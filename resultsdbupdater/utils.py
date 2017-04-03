import requests
import fedmsg
import logging
import json
import uuid
import re
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus


CONFIG = fedmsg.config.load_config()
RESULTSDB_API_URL = CONFIG.get('resultsdb-updater.resultsdb_api_url')
TRUSTED_CA = CONFIG.get('resultsdb-updater.resultsdb_api_ca')

LOGGER = logging.getLogger('CIConsumer')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    format=log_format, level=CONFIG.get('resultsdb-updater.log_level'))


def get_error_from_request(request):
    try:
        return request.json().get('message')
    except ValueError:
        return request.text


def create_result(testcase, outcome, ref_url, data, groups=None):
    if not groups:
        groups = []
    post_req = requests.post(
        '{0}/results'.format(RESULTSDB_API_URL),
        data=json.dumps({
            'testcase': testcase,
            'groups': groups,
            'outcome': outcome,
            'ref_url': ref_url,
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


def get_first_group(description):
    get_req = requests.get(
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
    msg_id = msg['headers']['message-id']
    team = msg['body']['msg'].get('team', 'unassigned')
    if team == 'unassigned':
        LOGGER.warn((
            'The message "{0}" did not contain a team. Using "unassigned" as '
            'the team namespace section of the Test Case').format(msg_id))

    testcase_url = msg['body']['msg']['jenkins_job_url']
    test_name = msg['body']['msg']['job_names']
    group_ref_url = msg['body']['msg']['jenkins_build_url']
    tests = msg['body']['msg']['tests']
    group_tests_ref_url = '{0}/console'.format(group_ref_url.rstrip('/'))
    component = msg['body']['msg'].get('component', 'unknown')
    recipients = msg['body']['msg'].get('recipients', ['unknown'])
    ci_tier = msg['body']['msg'].get('CI_tier', ['unknown'])

    if msg['body']['msg'].get('brew_task_id'):
        test_type = 'koji_build'
    else:
        test_type = 'unknown'

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
        test['job_names'] = test_name

        if not create_result(testcase, outcome, group_tests_ref_url,
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
        'job_names': test_name
    }

    if not create_result(testcase, overall_outcome, group_tests_ref_url,
                         result_data, groups):
        LOGGER.error(
            'An overall result for message "{0}" couldn\'t be created'
            .format(msg_id))
        return False

    return True


def resultsdb_post_to_resultsdb(msg):
    msg_id = msg['headers']['message-id']
    group_ref_url = msg['body']['msg']['ref_url']
    rpmdiff_url_regex_pattern = \
        r'^(?P<url_prefix>http.+\/run\/)(?P<run>\d+)(?:\/)?(?P<result>\d+)?$'
    if msg['headers']['testcase'].startswith('dist.rpmdiff'):
        rpmdiff_url_regex_match = re.match(
            rpmdiff_url_regex_pattern, msg['body']['msg']['ref_url'])

        if rpmdiff_url_regex_match:
            group_ref_url = '{0}{1}'.format(
                rpmdiff_url_regex_match.groupdict()['url_prefix'],
                rpmdiff_url_regex_match.groupdict()['run'])
        else:
            raise ValueError(
                'The ref_url of "{0}" did not match the rpmdiff URL scheme'
                .format(msg['body']['msg']['ref_url']))

    groups = [{
        # Check to see if there is a group already for these sets of tests,
        # otherwise, generate a UUID
        'uuid': get_first_group(group_ref_url).get('uuid', str(uuid.uuid4())),
        'ref_url': group_ref_url,
        # Set the description to the ref_url so that we can query for the group
        # by it later
        'description': group_ref_url
    }]

    result_rv = create_result(
        msg['body']['msg']['testcase'],
        msg['body']['msg']['outcome'],
        msg['body']['msg']['ref_url'],
        msg['body']['msg']['data'],
        groups
    )

    if not result_rv:
        LOGGER.error(
            'A new result for message "{0}" couldn\'t be created'
            .format(msg_id))
        return False

    return True
