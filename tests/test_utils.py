import mock
import pytest
import requests
import requests_mock

from resultsdbupdater import exceptions, utils


@pytest.mark.parametrize(
    ('testcase_name', 'namespace'),
    [
        ('rhproduct.default.functional', 'rhproduct'),
        ('', ''),
    ]
)
def test_namespace_from_testcase_name(testcase_name, namespace):
    assert utils.namespace_from_testcase_name(testcase_name) == namespace


@pytest.mark.parametrize(
    ('topic', 'namespace'),
    [
        ('/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete', 'rhproduct'),
        ('/topic/VirtualTopic.eng.ci.brew-build.test.complete', None),
    ]
)
def test_namespace_from_topic(topic, namespace):
    assert utils.namespace_from_topic(topic) == namespace


def test_verify_topic_and_testcase_name():
    topic = '/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete'
    testcase = 'rhproduct.default.functional'
    utils.verify_topic_and_testcase_name(topic, testcase)


def test_verify_topic_and_testcase_name_mismatch():
    topic = '/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete'
    testcase = 'nont-rhproduct.default.functional'
    error = (
        'Test case "nont-rhproduct.default.functional" namespace "nont-rhproduct" '
        'does not match message topic '
        '"/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete" '
        'namespace "rhproduct"'
    )
    with pytest.raises(exceptions.TopicMismatchError, match=error):
        utils.verify_topic_and_testcase_name(topic, testcase)


def test_verify_topic_and_testcase_name_with_topic_missing():
    topic = '/topic/VirtualTopic.eng.ci.brew-build.test.complete'
    testcase = 'rhproduct.default.functional'
    error = (
        'The message topic "/topic/VirtualTopic.eng.ci.brew-build.test.complete" '
        'uses old scheme not containing namespace from '
        'test case name "rhproduct.default.functional"'
    )
    with pytest.raises(exceptions.MissingTopicError, match=error):
        utils.verify_topic_and_testcase_name(topic, testcase)


def test_verify_topic_and_testcase_name_with_non_eng_topic():
    topic = '/topic/VirtualTopic.qe.ci.jenkins.x.y.z'
    testcase = 'rhproduct.default.functional'
    with pytest.raises(exceptions.MissingTopicError):
        utils.verify_topic_and_testcase_name(topic, testcase)


def test_value_too_large():
    """
    Large values cannot be stored in ResultsDB in a DB index.

    Storing values too big for DB index also caused the POST request to get
    stuck for some reason.

    JIRA: FACTORY-5780
    """
    data = {'reason': 'x' * 8193}
    log = mock.Mock()
    utils.crop_data(log, data)
    assert len(data['reason']) == 8192
    assert data['reason'].endswith('x...')
    log.warning.assert_called_with('Cropping large value for field %s', 'reason')


@pytest.mark.parametrize(
    ('status_code', 'exception', 'message'),
    [
        (400, exceptions.CreateResultError, 'An error occurred'),
        (500, requests.exceptions.HTTPError, ''),
    ]
)
def test_create_results_failure(status_code, exception, message):
    url = '{0}/results'.format(utils.config.RESULTSDB_API_URL)
    with requests_mock.Mocker() as mocked_requests:
        mocked_requests.post(url, json={'message': message}, status_code=status_code)
        log = mock.Mock()
        with pytest.raises(exception, match=message):
            utils.create_result(log, 'testcase', 'PASSED', 'http://example.com', {})
