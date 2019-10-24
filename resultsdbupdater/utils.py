import logging
import json
import uuid
import re

from collections import namedtuple

import fedmsg
import requests

import semantic_version


CONFIG = fedmsg.config.load_config()
RESULTSDB_API_URL = CONFIG.get('resultsdb-updater.resultsdb_api_url')
TRUSTED_CA = CONFIG.get('resultsdb-updater.resultsdb_api_ca')
TIMEOUT = CONFIG.get('resultsdb-updater.requests_timeout', 15)

LOGGER = logging.getLogger('CIConsumer')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    format=log_format, level=CONFIG.get('resultsdb-updater.log_level'))

USER_AGENT = 'resultsdb_updater'


def update_publisher_id(data, msg):
    """
    Sets data['publisher_id'] to message publisher ID (JMSXUserID) if it
    exists.
    """
    msg_publisher_id = msg['headers'].get('JMSXUserID')
    if msg_publisher_id:
        data['publisher_id'] = msg_publisher_id


FedoraCiTestArray = namedtuple(
    'FedoraCiTestArray',
    [
        'category',
        'namespace',
        'type',
        'result',
        'xunit',
    ]
)


class CreateResultError(RuntimeError):
    def __init__(self, msg, payload):
        super(CreateResultError, self).__init__()
        self.msg = msg
        self.payload = payload

    def __str__(self):
        return 'Failed to create result: {0}; Payload: {1}'.format(self.msg, self.payload)


def get_contact(msg_body):
    if semantic_version.match('<0.2.1', msg_body['version']):
        return msg_body['ci']
    return msg_body['contact']


def get_http_auth(user, password, url):
    """Return an auth tuple to be used with requests

    Args:
        user (string) - username used for Basic auth
        password (string) - password for Basic auth
        url (string) - URL for which the credentials above will be used

    Returns:
        Tuple of (user, password), if both defined, or None

    Raises:
        RuntimeError, if only one of (user, password) is defined
        RuntimeError, if url is not HTTPS
    """
    auth = None

    if not user and not password:
        pass
    elif user and password:
        auth = (user, password)
    else:
        raise RuntimeError(
            'User or password not configured for ResultDB Basic authentication!')

    # https://tools.ietf.org/html/rfc7617#section-4
    if auth and not url.startswith('https://'):
        raise RuntimeError(
            'Basic authentication should not be used without HTTPS!')

    return auth


RESULTSDB_AUTH = get_http_auth(
    CONFIG.get('resultsdb-updater.resultsdb_user'),
    CONFIG.get('resultsdb-updater.resultsdb_pass'),
    RESULTSDB_API_URL)


def create_result(testcase, outcome, ref_url, data, groups=None, note=None):
    payload = json.dumps({
        'testcase': testcase,
        'groups': groups or [],
        'outcome': outcome,
        'ref_url': ref_url,
        'note': note or '',
        'data': data
    })
    post_req = requests.post(
        '{0}/results'.format(RESULTSDB_API_URL),
        data=payload,
        headers={
            'content-type': 'application/json',
            'User-Agent': USER_AGENT,
        },
        auth=RESULTSDB_AUTH,
        timeout=TIMEOUT,
        verify=TRUSTED_CA)

    if post_req.status_code == 400:
        message = post_req.json().get('message')
        raise CreateResultError(message, payload)

    post_req.raise_for_status()


def get_first_group(description):
    get_req = requests.get(
        '{0}/groups?description={1}'.format(RESULTSDB_API_URL, description),
        timeout=TIMEOUT,
        verify=TRUSTED_CA,
        headers={
            'User-Agent': USER_AGENT,
        },
    )
    get_req.raise_for_status()
    if len(get_req.json()['data']) > 0:
        return get_req.json()['data'][0]

    return {}


def handle_ci_metrics(msg):
    msg_id = msg['headers']['message-id']
    team = msg['body']['msg'].get('team', 'unassigned')
    if team == 'unassigned':
        LOGGER.warning(
            'The message "{0}" did not contain a team. Using "unassigned" as '
            'the team namespace section of the Test Case'
            .format(msg_id)
        )

    if 'job_name' in msg['body']['msg']:
        test_name = msg['body']['msg']['job_name']  # new format
    else:
        # This should eventually be deprecated and removed.
        test_name = msg['body']['msg']['job_names']  # old format
        LOGGER.warning('Saw message "{0}" with job_names field.'.format(msg_id))

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

        update_publisher_id(data=test, msg=msg)
        create_result(testcase, outcome, group_tests_ref_url, test, groups)

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

    update_publisher_id(data=result_data, msg=msg)
    create_result(testcase, overall_outcome, group_tests_ref_url, result_data, groups)


def _test_result_outcome(topic, outcome):
    """
    Returns test result outcome value for ResultDB. The outcome depends
    on the topic and the outcome (in case of complete messages).

    Some systems generate outcomes that don't match spec.

    Test outcome is FAILED for messages with "*.error" topic.
    """
    if topic.endswith('.error'):
        return 'FAILED'
    elif topic.endswith('.queued'):
        return 'QUEUED'
    elif topic.endswith('.running'):
        return 'RUNNING'

    broken_mapping = {
        'pass': 'PASSED',
        'fail': 'FAILED',
        'failure': 'FAILED',
    }

    return broken_mapping.get(outcome.lower(), outcome.upper())


def _get_test_details(topic, message):
    """
    Returns test details according to the version of the spec.
    """
    result = None

    # version 0.1.x
    if semantic_version.match('<0.2.0', message['version']):
        category = message['category']
        namespace = message['namespace']
        test_type = message['type']
        xunit = message.get('xunit', None)
        result = message.get('status', None)

    # version >= 0.2.0
    else:
        test = message['test']
        category = test['category']
        namespace = test['namespace']
        test_type = test['type']

        # result is required for complete messages only
        if topic.endswith('.complete'):
            result = test['result']

        xunit = message.get('xunit', None)

    return FedoraCiTestArray(
        category=category,
        namespace=namespace,
        result=result,
        type=test_type,
        xunit=xunit
    )


def namespace_from_topic(topic):
    """
    Returns namespace from message topic.

    Returns None if the topic does not have the expected format.

    The expected topic format is:

        /topic/VirtualTopic.eng.ci.<namespace>.<artifact>.<event>.{queued,running,complete,error}
    """
    if not topic.startswith('/topic/VirtualTopic.eng.ci.'):
        return None

    topic_components = topic.split('.')
    if len(topic_components) != 7:
        return None

    return topic_components[3]


def namespace_from_testcase_name(testcase_name):
    """
    Returns namespace from test case name.

    Namespace is the component before the first dot.
    """
    return testcase_name.split('.', 1)[0]


def verify_topic_and_testcase_name(topic, testcase_name):
    """
    Verifies that the topic contains same namespace as the test case name.

    If an old topic format is encountered, this test is skipped and a warning
    is logged. This will be removed in the future after everyone uses the new
    topic format.

    The new topic format is:

        /topic/VirtualTopic.eng.ci.<namespace>.<artifact>.<event>.{queued,running,complete,error}

    Returns true only if topic format is different or the namespace does not
    match.

    Note: If the "namespace" field in the message contains ".", only the
    component before the first "." is expected to be in the topic.

    Example:

    - Message body:

        "msg": {
          "category": "functional",
          "namespace": "baseos-ci.redhat-module",
          "type": "tier1",
          ...
        }

    - Test case name:

        baseos-ci.redhat-module.tier1.functional

    - Example of expected topic:

        /topic/VirtualTopic.eng.ci.baseos-ci.redhat-module.test.complete
    """
    topic_namespace = namespace_from_topic(topic)
    if not topic_namespace:
        LOGGER.warning(
            'The message topic "%s" uses old scheme not containing '
            'namespace from test case name "%s"',
            topic, testcase_name)
        # Old topics are allowed for now.
        return True

    testcase_namespace = namespace_from_testcase_name(testcase_name)
    if testcase_namespace != topic_namespace:
        LOGGER.warning(
            'Test case "%s" namespace "%s" does not match '
            'message topic "%s" namespace "%s"',
            testcase_name, testcase_namespace, topic, topic_namespace)
        return False

    return True


def handle_ci_umb(msg):
    #
    # Handle messages in Fedora CI messages format
    #
    # https://pagure.io/fedora-ci/messages
    #

    msg_body = msg['body']['msg']

    # check if required version is provided in the message
    if 'version' not in msg_body:
        LOGGER.error((
            'The message "{0}" does not contain required version information'
            .format(msg_body),
            ', cannot continue'
        ))
        return

    topic = msg['topic']

    item_type = msg_body['artifact']['type']
    test_run_url = msg_body['run']['url']

    test = _get_test_details(topic, msg_body)

    outcome = _test_result_outcome(topic, test.result)

    # variables to be passed to create_result
    groups = [{
        'uuid': str(uuid.uuid4()),
        'url': test_run_url
    }]

    system = msg_body.get('system', {})

    # Oddly, sometimes people pass us a sytem dict but other times a
    # list of one system dict.  Try to handle those two situation here.
    if isinstance(system, list):
        system = system[0] if system else {}

    contact = get_contact(msg_body)

    if item_type == 'productmd-compose':
        architecture = system['architecture']
        variant = system.get('variant')
        # Field compose_id in artifacts is deprecated.
        compose_id = msg_body['artifact'].get('id') or msg_body['artifact']['compose_id']
        item = '{0}/{1}/{2}'.format(compose_id, variant or 'unknown', architecture)
        result_data = {
            key: value for key, value in (
                ('item', item),

                ('ci_name', contact['name']),
                ('ci_team', contact['team']),
                ('ci_url', contact.get('url', 'not available')),
                ('ci_irc', contact.get('irc', 'not available')),
                ('ci_email', contact['email']),

                ('log', msg_body['run']['log']),

                ('type', item_type),
                ('productmd.compose.id', compose_id),

                ('system_provider', system['provider']),
                ('system_architecture', architecture),
                ('system_variant', variant),

                ('category', test.category),
            ) if value is not None
        }

    elif item_type == 'component-version':
        component = msg_body['artifact']['component']
        version = msg_body['artifact']['version']
        item = '{0}-{1}'.format(component, version)
        result_data = {
            key: value for key, value in (
                ('item', item),

                ('ci_name', contact['name']),
                ('ci_team', contact['team']),
                ('ci_url', contact.get('url', 'not available')),
                ('ci_irc', contact.get('irc', 'not available')),
                ('ci_email', contact['email']),

                ('log', msg_body['run']['log']),

                ('type', item_type),
                ('component', component),
                ('version', version),

                ('category', test.category),
            ) if value is not None
        }

    elif item_type == 'container-image':
        repo = msg_body['artifact']['repository']
        digest = msg_body['artifact']['digest']
        item = '{0}@{1}'.format(repo, digest)
        result_data = {
            key: value for key, value in (
                ('item', item),

                ('ci_name', contact['name']),
                ('ci_team', contact['team']),
                ('ci_url', contact.get('url', 'not available')),
                ('ci_irc', contact.get('irc', 'not available')),
                ('ci_email', contact['email']),

                ('log', msg_body['run']['log']),
                ('rebuild', msg_body['run'].get('rebuild')),
                ('xunit', test.xunit),

                ('type', item_type),
                ('repository', msg_body['artifact'].get('repository')),
                ('digest', msg_body['artifact'].get('digest')),
                ('format', msg_body['artifact'].get('format')),
                ('pull_ref', msg_body['artifact'].get('pull_ref')),
                ('scratch', msg_body['artifact'].get('scratch')),
                ('nvr', msg_body['artifact'].get('nvr')),
                ('issuer', msg_body['artifact'].get('issuer')),

                ('system_os', system.get('os')),
                ('system_provider', system.get('provider')),
                ('system_architecture', system.get('architecture')),

                ('category', test.category),
            ) if value is not None
        }

    elif item_type == 'redhat-module':
        # The pagure.io/messages spec defines the NSVC delimited with ':' and the stream name can
        # contain '-', which MBS changes to '_' when importing to koji.
        # See https://github.com/release-engineering/resultsdb-updater/pull/73
        nsvc_regex = re.compile('^(.*):(.*):(.*):(.*)')
        try:
            name, stream, version, context = re.match(
                nsvc_regex, msg_body['artifact']['nsvc']).groups()
            stream = stream.replace('-', '_')
        except AttributeError:
            LOGGER.error("Invalid nsvc '{}' encountered, ignoring result".format(
                msg_body['artifact']['nsvc']))
            return

        nsvc = '{}-{}-{}.{}'.format(name, stream, version, context)

        result_data = {
            'item': nsvc,
            'type': item_type,
            'mbs_id': msg_body['artifact'].get('id'),
            'category': test.category,
            'context': msg_body['artifact']['context'],
            'name': msg_body['artifact']['name'],
            'nsvc': nsvc,
            'stream': msg_body['artifact']['stream'],
            'version': msg_body['artifact']['version'],
            'issuer': msg_body['artifact'].get('issuer'),
            'rebuild': msg_body['run'].get('rebuild'),
            'log': msg_body['run']['log'],
            'system_os': system.get('os'),
            'system_provider': system.get('provider'),
            'ci_name': contact.get('name'),
            'ci_url': contact.get('url', 'not available'),
            'ci_team': contact.get('team'),
            'ci_irc': contact.get('irc', 'not available'),
            'ci_email': contact.get('email'),
        }
    # used as a default
    elif item_type == 'brew-build':
        item = msg_body['artifact']['nvr']
        component = msg_body['artifact']['component']
        scratch = msg_body['artifact'].get('scratch', '')
        brew_task_id = msg_body['artifact'].get('id')

        # scratch is supposed to be a bool but some messages in the wild
        # use a string instead
        if not isinstance(scratch, bool):
            scratch = scratch.lower() == 'true'

        # we need to differentiate between scratch and non-scratch builds
        if scratch:
            item_type += '_scratch'

        result_data = {
            'item': item,
            'type': item_type,
            'brew_task_id': brew_task_id,
            'category': test.category,
            'component': component,
            'scratch': scratch,
            'issuer': msg_body['artifact'].get('issuer'),
            'rebuild': msg_body['run'].get('rebuild'),
            'log': msg_body['run']['log'],  # required
            'system_os': system.get('os'),
            'system_provider': system.get('provider'),
            'ci_name': contact.get('name'),
            'ci_url': contact.get('url', 'not available'),
            'ci_team': contact.get('team'),
            'ci_irc': contact.get('irc', 'not available'),
            'ci_email': contact.get('email'),
        }

    # an unknown artifact type
    else:
        LOGGER.error("Artifact type '{}' handling not implemented".format(item_type))
        return

    # add optional recipients field, according to the version
    if semantic_version.match('<0.2.0', msg_body['version']):
        result_data['recipients'] = msg_body.get('recipients', [])

    else:
        notification = msg_body.get('notification', None)

        if notification:
            result_data['recipients'] = notification.get('recipients', [])

    update_publisher_id(data=result_data, msg=msg)

    # construct resultsdb testcase dict
    testcase = {
        'name': '.'.join([test.namespace, test.type, test.category]),
        'ref_url': msg_body['run']['url'],
    }

    if not verify_topic_and_testcase_name(msg['topic'], testcase['name']):
        return

    create_result(testcase, outcome, test_run_url, result_data, groups)


def handle_resultsdb_format(msg):
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
            result_data = result.get('data', {})
            update_publisher_id(data=result_data, msg=msg)
            create_result(
                testcase,
                result['outcome'],
                result.get('ref_url', ''),
                result_data,
                groups,
                result.get('note', ''),
            )

    else:
        groups = [{
            # Check to see if there is a group already for these sets of tests,
            # otherwise, generate a UUID
            'uuid': get_first_group(group_ref_url).get(
                'uuid', str(uuid.uuid4())),
            'ref_url': group_ref_url,
            # Set the description to the ref_url so that we can query for the
            # group by it later
            'description': group_ref_url
        }]

        result_data = msg_body['data']
        update_publisher_id(data=result_data, msg=msg)

        create_result(
            msg_body['testcase'],
            msg_body['outcome'],
            msg_body['ref_url'],
            result_data,
            groups,
            msg_body.get('note', '')
        )
