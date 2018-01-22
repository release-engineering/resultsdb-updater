import logging
import json
import uuid
import re

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import fedmsg


CONFIG = fedmsg.config.load_config()
RESULTSDB_API_URL = CONFIG.get('resultsdb-updater.resultsdb_api_url')
TRUSTED_CA = CONFIG.get('resultsdb-updater.resultsdb_api_ca')

LOGGER = logging.getLogger('CIConsumer')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    format=log_format, level=CONFIG.get('resultsdb-updater.log_level'))


def retry_session():
    # This will give the total wait time in minutes:
    # >>> sum([min((0.3 * (2 ** (i - 1))), 120) / 60 for i in range(24)])
    # >>> 30.5575
    # This works by the using the minimum time in seconds of the backoff time
    # and the max back off time which defaults to 120 seconds. The backoff time
    # increases after every failed attempt.
    session = requests.Session()
    retry = Retry(
        total=24,
        read=5,
        connect=24,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        method_whitelist=('GET', 'POST'),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_error_from_request(request):
    try:
        return request.json().get('message')
    except ValueError:
        return request.text


def create_result(session, testcase, outcome, ref_url, data, groups=None,
                  note=None):
    post_req = session.post(
        '{0}/results'.format(RESULTSDB_API_URL),
        data=json.dumps({
            'testcase': testcase,
            'groups': groups or [],
            'outcome': outcome,
            'ref_url': ref_url,
            'note': note or '',
            'data': data}),
        headers={'content-type': 'application/json'},
        verify=TRUSTED_CA)
    if post_req.status_code == 201:
        return True
    else:
        message = get_error_from_request(post_req)
        LOGGER.error(
            'The result failed with the following: {0}'.format(message))
        return False


def get_first_group(session, description):
    get_req = session.get(
        '{0}/groups?description={1}'.format(RESULTSDB_API_URL, description),
        verify=TRUSTED_CA
    )
    if get_req.status_code == 200:
        if len(get_req.json()['data']) > 0:
            return get_req.json()['data'][0]
        else:
            return {}
    else:
        message = get_error_from_request(get_req)
        raise RuntimeError(
            'The query for groups failed with the following: {0}'.format(
                message))


def ci_metrics_post_to_resultsdb(msg):
    session = retry_session()
    msg_id = msg['headers']['message-id']
    team = msg['body']['msg'].get('team', 'unassigned')
    if team == 'unassigned':
        LOGGER.warn((
            'The message "{0}" did not contain a team. Using "unassigned" as '
            'the team namespace section of the Test Case').format(msg_id))

    if 'job_name' in msg['body']['msg']:
        test_name = msg['body']['msg']['job_name']  # new format
    else:
        # This should eventually be deprecated and removed.
        test_name = msg['body']['msg']['job_names']  # old format
        LOGGER.warn('Saw message "{0}" with job_names field.'.format(msg_id))

    testcase_url = msg['body']['msg']['jenkins_job_url']
    group_ref_url = msg['body']['msg']['jenkins_build_url']
    build_type = msg['body']['msg'].get('build_type', 'unknown')
    artifact = msg['body']['msg'].get('artifact', 'unknown')
    brew_task_id = msg['body']['msg'].get('brew_task_id', 'unknown')
    tests = msg['body']['msg']['tests']
    group_tests_ref_url = '{0}/console'.format(group_ref_url.rstrip('/'))
    component = msg['body']['msg'].get('component', 'unknown')
    # This comes as a string of comma separated names
    recipients = msg['body']['msg'].get('recipients', 'unknown').split(',')
    ci_tier = msg['body']['msg'].get('CI_tier', ['unknown'])
    test_type = 'unknown'

    if brew_task_id != 'unknown':
        test_type = 'koji_build'

    if build_type == 'scratch':
        test_type += '_scratch'

    groups = [{
        'uuid': str(uuid.uuid4()),
        'ref_url': group_ref_url
    }]
    overall_outcome = 'PASSED'

    for test in tests:
        if 'failed' in test and int(test['failed']) == 0:
            outcome = 'PASSED'
        else:
            outcome = 'FAILED'
            overall_outcome = 'FAILED'

        testcase = {
            'name': '{0}.{1}.{2}'.format(
                team, test_name, test.get('executor', 'unknown')),
            'ref_url': testcase_url
        }
        test['item'] = component
        test['type'] = test_type
        test['recipients'] = recipients
        test['CI_tier'] = ci_tier
        test['job_name'] = test_name
        test['artifact'] = artifact
        test['brew_task_id'] = brew_task_id

        if not create_result(session, testcase, outcome, group_tests_ref_url,
                             test, groups):
            LOGGER.error(
                'A new result for message "{0}" couldn\'t be created'
                .format(msg_id))
            return False

    # Create the overall test result
    testcase = {
        'name': '{0}.{1}'.format(team, test_name),
        'ref_url': testcase_url
    }
    result_data = {
        'item': component,
        'type': test_type,
        'recipients': recipients,
        'CI_tier': ci_tier,
        'job_name': test_name,
        'artifact': artifact,
        'brew_task_id': brew_task_id
    }

    if not create_result(session, testcase, overall_outcome,
                         group_tests_ref_url, result_data, groups):
        LOGGER.error(
            'An overall result for message "{0}" couldn\'t be created'
            .format(msg_id))
        return False

    return True


def cips_post_to_resultsdb(msg):
    session = retry_session()
    # define variables from cips.json
    msg_id = msg['headers']['message-id']
    ci_type = msg['headers']['ci_type']
    component = msg['headers']['component']
    brew_task_id = msg['headers']['brew_task_id']
    msg_body = msg['body']['msg']
    tests = msg_body['tests']

    arch = msg_body['environment']['arch']
    brew_tag = msg_body['environment']['brew_tag']
    build_type = msg_body['environment']['build_type']

    jenkins_job_url = msg_body['infrastructure']['jenkins_job_url']
    jenkins_build_url = msg_body['infrastructure']['jenkins_build_url']

    cips_report = msg_body['results']['cips_report']
    cips_status = msg_body['results']['cips_status']

    testcase_url = jenkins_job_url

    # variables to be passed to create_result
    groups = [{
        'uuid': str(uuid.uuid4()),
        'ref_url': jenkins_build_url
    }]
    outcome = cips_status
    ref_url = jenkins_build_url

    result_data = {
        'item': component,
        'ci_type': ci_type,
        'brew_task_id': brew_task_id,
        'brew_tag': brew_tag,
        'arch': arch,
        'component': component,
        'build_type': build_type,
        'cips_report': cips_report,
        'cips_status': cips_status,
        'testcase_url': testcase_url,
    }

    # Create individual test results for each test in the message
    for test_name, test_outcome in tests.items():
        testcase = {
            'name': 'rpm-factory.cips.{}'.format(test_name),
            'ref_url': testcase_url
        }
        if not create_result(
                session, testcase, test_outcome, ref_url, result_data, groups):
            LOGGER.error(
                'A new result for message "{0}" couldn\'t be created'
                .format(msg_id))
            return False

    # Create the overall test result
    testcase = {
        'name': 'rpm-factory.cips',
        'ref_url': testcase_url
    }
    if not create_result(session, testcase, outcome, ref_url, result_data,
                         groups):
        LOGGER.error(
            'An overall result for message "{0}" couldn\'t be created'
            .format(msg_id))
        return False

    return True


def resultsdb_post_to_resultsdb(msg):
    session = retry_session()
    error_msg = 'A new result for message "{0}" couldn\'t be created'
    msg_id = msg['headers']['message-id']
    msg_body = msg['body']['msg']
    group_ref_url = msg_body['ref_url']
    rpmdiff_url_regex_pattern = \
        r'^(?P<url_prefix>http.+\/run\/)(?P<run>\d+)(?:\/)?(?P<result>\d+)?$'

    if msg_body.get('testcase', {}).get('name', '').startswith('dist.rpmdiff'):
        rpmdiff_url_regex_match = re.match(
            rpmdiff_url_regex_pattern, msg_body['ref_url'])

        if rpmdiff_url_regex_match:
            group_ref_url = '{0}{1}'.format(
                rpmdiff_url_regex_match.groupdict()['url_prefix'],
                rpmdiff_url_regex_match.groupdict()['run'])
        else:
            raise ValueError(
                'The ref_url of "{0}" did not match the rpmdiff URL scheme'
                .format(msg_body['ref_url']))

    # Check if the message is in bulk format
    if msg_body.get('results'):
        groups = [{
            'uuid': str(uuid.uuid4()),
            'ref_url': group_ref_url
        }]

        for testcase, result in msg_body['results'].items():
            result_rv = create_result(
                session,
                testcase,
                result['outcome'],
                result.get('ref_url', ''),
                result.get('data', {}),
                groups,
                result.get('note', ''),
            )
            if not result_rv:
                LOGGER.error(error_msg.format(msg_id))
                return False

    else:
        groups = [{
            # Check to see if there is a group already for these sets of tests,
            # otherwise, generate a UUID
            'uuid': get_first_group(session, group_ref_url).get(
                'uuid', str(uuid.uuid4())),
            'ref_url': group_ref_url,
            # Set the description to the ref_url so that we can query for the
            # group by it later
            'description': group_ref_url
        }]

        result_rv = create_result(
            session,
            msg_body['testcase'],
            msg_body['outcome'],
            msg_body['ref_url'],
            msg_body['data'],
            groups,
            msg_body.get('note', '')
        )

        if not result_rv:
            LOGGER.error(error_msg.format(msg_id))
            return False

    return True
