import json
import uuid
import re

from .session import session

from . import config, exceptions


# Maximum length of a text value for result data.
MAX_RESULT_DATA_SIZE = 8192


def json_serialize_data_item(item):
    if isinstance(item, list):
        return [
            json.dumps(v) if isinstance(v, dict) else v
            for v in item
        ]

    if isinstance(item, dict):
        return json.dumps(item)

    return item


def json_serialize_data(data):
    """
    Serialize data correctly for ResultsDB.

    Results data should be only strings or lists of strings, otherwise the data
    are stored as string representations of Python objects in ResultsDB.
    """
    return {
        k: json_serialize_data_item(v)
        for k, v in data.items()
    }


def crop_data(log, data):
    """
    Crops large data values so they can be stored in ResultsDB.

    Even thought size for result data are not limited in database schema,
    Postgresql index has a size limited ("Values larger than 1/3 of a buffer
    page cannot be indexed").

    Raises InvalidMessageError if non-string value is too large.
    """
    for k, v in data.items():
        if isinstance(v, str):
            if len(v) > MAX_RESULT_DATA_SIZE:
                log.warning('Cropping large value for field %s', k)
                data[k] = v[:MAX_RESULT_DATA_SIZE - 3] + "..."
        elif isinstance(v, list):
            if any(len(str(item)) > MAX_RESULT_DATA_SIZE for item in v):
                raise exceptions.InvalidMessageError(
                    'Result value "{0}" contains items that are too large'.format(k))
        elif len(str(v)) > MAX_RESULT_DATA_SIZE:
            raise exceptions.InvalidMessageError(
                'Result value "{0}" is too large'.format(k))


def update_publisher_id(data, msg):
    """
    Sets data['publisher_id'] to message publisher ID (JMSXUserID) if it
    exists.
    """
    msg_publisher_id = msg.header('JMSXUserID')
    if msg_publisher_id:
        data['publisher_id'] = msg_publisher_id


def create_result(log, testcase, outcome, ref_url, data, groups=None, note=None):
    data = json_serialize_data(data)
    crop_data(log, data)

    payload = json.dumps({
        'testcase': testcase,
        'groups': groups or [],
        'outcome': outcome,
        'ref_url': ref_url,
        'note': note or '',
        'data': data
    })

    log.debug('Requesting new result: %s', payload)

    post_req = session.post(
        '{0}/results'.format(config.RESULTSDB_API_URL),
        data=payload,
        headers={
            'content-type': 'application/json',
        },
        auth=config.RESULTSDB_AUTH,
        timeout=config.TIMEOUT,
        verify=config.TRUSTED_CA)

    log.debug('New result requested (HTTP %s)', post_req.status_code)

    if post_req.status_code == 400:
        message = post_req.json().get('message')
        raise exceptions.CreateResultError(message, payload)

    post_req.raise_for_status()


def get_first_group(description):
    get_req = session.get(
        '{0}/groups?description={1}'.format(config.RESULTSDB_API_URL, description),
        timeout=config.TIMEOUT,
        verify=config.TRUSTED_CA,
    )
    get_req.raise_for_status()
    if len(get_req.json()['data']) > 0:
        return get_req.json()['data'][0]

    return {}


def handle_ci_metrics(msg):
    team = msg.get('team', default='unassigned')
    if team == 'unassigned':
        msg.log.warning(
            'Missing "team". Using "unassigned" as '
            'the team namespace section of the Test Case'
        )

    test_name = msg.get('job_name', default=None)  # new format
    if test_name is None:
        # This should eventually be deprecated and removed.
        test_name = msg.get('job_names')  # old format
        msg.log.warning('Using with "job_names" field.')

    testcase_url = msg.get('jenkins_job_url')
    group_ref_url = msg.get('jenkins_build_url')
    build_type = msg.get('build_type', default='unknown')
    artifact = msg.get('artifact', default='unknown')
    brew_task_id = msg.get('brew_task_id', default='unknown')
    tests = msg.get('tests')
    group_tests_ref_url = '{0}/console'.format(group_ref_url.rstrip('/'))
    component = msg.get('component', default='unknown')
    # This comes as a string of comma separated names
    recipients = msg.get('recipients', default='unknown').split(',')
    ci_tier = msg.get('CI_tier', default=['unknown'])
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
        create_result(msg.log, testcase, outcome, group_tests_ref_url, test, groups)

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
    create_result(msg.log, testcase, overall_outcome, group_tests_ref_url, result_data, groups)


def _test_result_outcome(topic, outcome):
    """
    Returns test result outcome value for ResultDB. The outcome depends
    on the topic and the outcome (in case of complete messages).

    Some systems generate outcomes that don't match spec.

    Test outcome is ERROR for messages with "*.error" topic.
    """
    if topic.endswith('.error'):
        return 'ERROR'
    elif topic.endswith('.queued'):
        return 'QUEUED'
    elif topic.endswith('.running'):
        return 'RUNNING'

    broken_mapping = {
        'pass': 'PASSED',
        'fail': 'FAILED',
        'failure': 'FAILED',
    }

    try:
        return broken_mapping.get(outcome.lower(), outcome.upper())
    except AttributeError:
        raise exceptions.InvalidMessageError(
            'Unexpected result status/outcome, expected a string, got: %r' % outcome)


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

    Raises MissingTopicError if an old topic format is encountered.

    The new topic format is:

        /topic/VirtualTopic.eng.ci.<namespace>.<artifact>.<event>.{queued,running,complete,error}

    Raises TopicMismatchError if topic doesn't match test namespace.

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
        raise exceptions.MissingTopicError(
            topic=topic,
            testcase_name=testcase_name)

    testcase_namespace = namespace_from_testcase_name(testcase_name)
    if testcase_namespace != topic_namespace:
        raise exceptions.TopicMismatchError(
            testcase_name=testcase_name,
            testcase_namespace=testcase_namespace,
            topic=topic,
            topic_namespace=topic_namespace)


def handle_ci_umb(msg):
    #
    # Handle messages in Fedora CI messages format
    #
    # https://pagure.io/fedora-ci/messages
    #

    # check if required version is provided in the message
    if msg.get('version', default=None) is None:
        msg.log.warning((
            'Missing required version information, using default version %s'
        ), msg.version)

    if isinstance(msg.version, str) and msg.version and not msg.version.startswith('0.'):
        raise exceptions.InvalidMessageError(
            'Unsupported version: %s (supported are only versions less than 1.0.0)' % msg.version)

    item_type = msg.get('artifact', 'type')
    test_run_url = msg.get('run', 'url')

    outcome = _test_result_outcome(msg.topic, msg.result.result)

    # variables to be passed to create_result
    groups = [{
        'uuid': str(uuid.uuid4()),
        'url': test_run_url
    }]

    if item_type == 'productmd-compose':
        architecture = msg.system('architecture')
        variant = msg.system('variant', default=None)
        # Field compose_id in artifacts is deprecated.
        compose_id = msg.get('artifact', 'id', default=None) or msg.get('artifact', 'compose_id')
        item = '{0}/{1}/{2}'.format(compose_id, variant or 'unknown', architecture)
        result_data = {
            key: value for key, value in (
                ('item', item),

                ('log', msg.get('run', 'log')),

                ('type', item_type),
                ('productmd.compose.id', compose_id),

                ('system_provider', msg.system('provider')),
                ('system_architecture', architecture),
                ('system_variant', variant),

                ('category', msg.result.category),
            ) if value is not None
        }

    elif item_type == 'product-build':
        product = msg.get('artifact', 'name')
        version = msg.get('artifact', 'version')
        release = msg.get('artifact', 'release')
        item = '{0}-{1}-{2}'.format(product, version, release)
        result_data = {
            key: value for key, value in (
                ('item', item),
                ('product', product),
                ('version', version),
                ('release', release),
                ('log', msg.get('run', 'log')),
                ('type', item_type),
                ('system_architecture', msg.system('architecture')),
                ('category', msg.result.category),
            ) if value is not None
        }

    elif item_type == 'component-version':
        component = msg.get('artifact', 'component')
        version = msg.get('artifact', 'version')
        item = '{0}-{1}'.format(component, version)
        result_data = {
            key: value for key, value in (
                ('item', item),

                ('log', msg.get('run', 'log')),

                ('type', item_type),
                ('component', component),
                ('version', version),

                ('category', msg.result.category),
            ) if value is not None
        }

    elif item_type == 'container-image':
        repo = msg.get('artifact', 'repository')
        digest = msg.get('artifact', 'digest')
        item = '{0}@{1}'.format(repo, digest)
        result_data = {
            key: value for key, value in (
                ('item', item),

                ('log', msg.get('run', 'log')),
                ('rebuild', msg.get('run', 'rebuild', default=None)),
                ('xunit', msg.result.xunit),

                ('type', item_type),
                ('repository', msg.get('artifact', 'repository', default=None)),
                ('digest', msg.get('artifact', 'digest', default=None)),
                ('format', msg.get('artifact', 'format', default=None)),
                ('pull_ref', msg.get('artifact', 'pull_ref', default=None)),
                ('scratch', msg.get('artifact', 'scratch', default=None)),
                ('nvr', msg.get('artifact', 'nvr', default=None)),
                ('issuer', msg.get('artifact', 'issuer', default=None)),

                ('system_os', msg.system('os', default=None)),
                ('system_provider', msg.system('provider', default=None)),
                ('system_architecture', msg.system('architecture', default=None)),

                ('category', msg.result.category),
            ) if value is not None
        }

    elif item_type == 'redhat-container-image':
        result_data = {
            'item': msg.get('artifact', 'id'),
            'type': item_type,
            'brew_task_id': msg.get('artifact', 'task_id', default=None),
            'brew_build_id': msg.get('artifact', 'build_id', default=None),
            'category': msg.result.category,
            'full_names': msg.get('artifact', 'full_names'),
            'registry_url': msg.get('artifact', 'registry_url', default=None),
            'tag': msg.get('artifact', 'tag', default=None),
            'issuer': msg.get('artifact', 'issuer'),
            'component': msg.get('artifact', 'component'),
            'name': msg.get('artifact', 'name'),
            'namespace': msg.get('artifact', 'namespace'),
            'scratch': msg.get('artifact', 'scratch'),
            'nvr': msg.get('artifact', 'nvr'),
            'source': msg.get('artifact', 'source'),
            'rebuild': msg.get('run', 'rebuild', default=None),
            'log': msg.get('run', 'log'),
        }

    elif item_type == 'redhat-module':
        # The pagure.io/messages spec defines the NSVC delimited with ':' and the stream name can
        # contain '-', which MBS changes to '_' when importing to koji.
        # See https://github.com/release-engineering/resultsdb-updater/pull/73
        nsvc_regex = re.compile('^(.*):(.*):(.*):(.*)')
        nsvc = msg.get('artifact', 'nsvc')
        try:
            name, stream, version, context = re.match(nsvc_regex, nsvc).groups()
            stream = stream.replace('-', '_')
        except AttributeError:
            raise exceptions.InvalidMessageError('Invalid nsvc "%s" encountered' % nsvc)

        nsvc = '{}-{}-{}.{}'.format(name, stream, version, context)

        result_data = {
            'item': nsvc,
            'type': item_type,
            'mbs_id': msg.get('artifact', 'id', default=None),
            'category': msg.result.category,
            'context': msg.get('artifact', 'context'),
            'name': msg.get('artifact', 'name'),
            'nsvc': nsvc,
            'stream': msg.get('artifact', 'stream'),
            'version': msg.get('artifact', 'version'),
            'issuer': msg.get('artifact', 'issuer', default=None),
            'rebuild': msg.get('run', 'rebuild', default=None),
            'log': msg.get('run', 'log'),
            'system_os': msg.system('os', default=None),
            'system_provider': msg.system('provider', default=None),
        }

    elif item_type == 'redhat-advisory':
        item = msg.get('artifact', 'id')
        result_data = {
            'item': item,
            'type': item_type,
            'category': msg.result.category,
            'numeric_id': msg.get('artifact', 'numeric_id', default=None),

            'pipeline_id': msg.get('pipeline', 'id'),
            'pipeline_name': msg.get('pipeline', 'name'),
            'pipeline_build': msg.get('pipeline', 'build', default=None),
            'pipeline_stage': msg.get('pipeline', 'stage', 'name', default=None),

            'log': msg.get('run', 'log'),
            'log_raw': msg.get('run', 'log_raw', default=None),
            'log_stream': msg.get('run', 'log_stream', default=None),

            'system_os': msg.system('os', default=None),
            'system_provider': msg.system('provider', default=None),
        }

    elif item_type == 'brew-build':
        item = msg.get('artifact', 'nvr')
        component = msg.get('artifact', 'component')
        scratch = msg.get('artifact', 'scratch', default='')
        brew_task_id = msg.get('artifact', 'id', default=None)

        # scratch is supposed to be a bool but some messages in the wild
        # use a string instead
        if not isinstance(scratch, bool):
            try:
                scratch = scratch.lower() == 'true'
            except AttributeError:
                scratch = False

        # we need to differentiate between scratch and non-scratch builds
        if scratch:
            item_type += '_scratch'

        result_data = {
            'item': item,
            'type': item_type,
            'brew_task_id': brew_task_id,
            'category': msg.result.category,
            'component': component,
            'scratch': scratch,
            'issuer': msg.get('artifact', 'issuer', default=None),
            'rebuild': msg.get('run', 'rebuild', default=None),
            'log': msg.get('run', 'log'),
            'system_os': msg.system('os', default=None),
            'system_provider': msg.system('provider', default=None),
        }

    elif item_type == 'brew-build-group':
        item = msg.get('artifact', 'id')
        repository = msg.get('artifact', 'repository')
        builds = msg.get('artifact', 'builds')

        result_data = {
            'item': item,
            'type': item_type,
            'category': msg.result.category,
            'repository': repository,
            'builds': builds,
            'rebuild': msg.get('run', 'rebuild', default=None),
            'log': msg.get('run', 'log'),
            'system_os': msg.system('os', default=None),
            'system_provider': msg.system('provider', default=None),
        }

    elif item_type == 'product-scenario':
        product_scenario = msg.get('artifact', 'id')
        products = msg.get('artifact', 'products')
        products_data = [json.dumps(product) for product in products]
        item = [product.get('nvr', product['id']) for product in products]
        item.insert(0, product_scenario)
        result_data = {
            'item': item,
            'type': item_type,
            'rebuild': msg.get('run', 'rebuild', default=None),
            'log': msg.get('run', 'log'),
            'system_os': msg.system('os', default=None),
            'system_provider': msg.system('provider', default=None),
            'products': products_data,
        }

    else:
        raise exceptions.InvalidMessageError('Unknown artifact type "%s"' % item_type)

    result_data.update(msg.contact_dict)
    result_data['recipients'] = msg.recipients

    update_publisher_id(data=result_data, msg=msg)

    if msg.result.scenario is not None:
        result_data['scenario'] = msg.result.scenario

    # construct resultsdb testcase dict
    testcase = {
        'name': msg.result.testcase,
        'ref_url': msg.get('run', 'url'),
    }

    try:
        verify_topic_and_testcase_name(msg.topic, testcase['name'])
    except exceptions.MissingTopicError as e:
        # Old topics are allowed for now.
        msg.log.warning(e)

    if outcome == 'ERROR':
        result_data['error_reason'] = msg.error_reason[:256]

        issue_url = msg.get('error', 'issue_url', default=None)
        if issue_url:
            result_data['issue_url'] = issue_url

    create_result(msg.log, testcase, outcome, test_run_url, result_data, groups, msg.result.note)


def handle_resultsdb_format(msg):
    group_ref_url = msg.get('ref_url')
    rpmdiff_url_regex_pattern = \
        r'^(?P<url_prefix>http.+\/run\/)(?P<run>\d+)(?:\/)?(?P<result>\d+)?$'

    if msg.get('testcase', 'name', default='').startswith('dist.rpmdiff'):
        rpmdiff_url_regex_match = re.match(rpmdiff_url_regex_pattern, group_ref_url)

        if rpmdiff_url_regex_match:
            group_ref_url = '{0}{1}'.format(
                rpmdiff_url_regex_match.groupdict()['url_prefix'],
                rpmdiff_url_regex_match.groupdict()['run'])
        else:
            raise exceptions.InvalidMessageError(
                'The ref_url "{0}" did not match the rpmdiff URL scheme'
                .format(group_ref_url))

    # Check if the message is in bulk format
    results = msg.get('results', default=None)
    if results:
        groups = [{
            'uuid': str(uuid.uuid4()),
            'ref_url': group_ref_url
        }]

        for testcase, result in results.items():
            result_data = result.get('data', {})
            update_publisher_id(data=result_data, msg=msg)
            create_result(
                msg.log,
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

        result_data = msg.get('data')
        update_publisher_id(data=result_data, msg=msg)

        create_result(
            msg.log,
            msg.get('testcase'),
            msg.get('outcome'),
            msg.get('ref_url'),
            result_data,
            groups,
            msg.get('note', default='')
        )
