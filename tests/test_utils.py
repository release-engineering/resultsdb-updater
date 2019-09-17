import logging
import pytest
from resultsdbupdater import utils


@pytest.mark.parametrize(
    ('user', 'password', 'url', 'result', 'error'),
    [
        # Basic auth correctly configured
        ('user', 'password', 'https://example.com', ('user', 'password'), None),
        # Basic auth not configured
        (None, None, 'http://example.com', None, None),
        # URL is not HTTPS
        ('foo', 'bar', 'http://example.com', None, RuntimeError),
        # User not configured
        (None, 'bar', 'https://example.com', None, RuntimeError),
        # Password not configured
        ('red', None, 'https://example.com', None, RuntimeError),
    ])
def test_get_http_auth(user, password, url, result, error):
    if error:
        with pytest.raises(error):
            auth = utils.get_http_auth(user, password, url)
    else:
        auth = utils.get_http_auth(user, password, url)
        assert auth == result


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


@pytest.mark.parametrize(
    ('topic', 'testcase_name', 'expected_result', 'expected_log'),
    [
        (
            '/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete',
            'rhproduct.default.functional',
            True,
            [],
        ),
        (
            '/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete',
            'nont-rhproduct.default.functional',
            False,
            [
                'Test case "nont-rhproduct.default.functional" namespace "nont-rhproduct" '
                'does not match message topic '
                '"/topic/VirtualTopic.eng.ci.rhproduct.brew-build.test.complete" '
                'namespace "rhproduct"'
            ]
        ),
        (
            '/topic/VirtualTopic.eng.ci.brew-build.test.complete',
            'rhproduct.default.functional',
            True,
            [
                'The message topic "/topic/VirtualTopic.eng.ci.brew-build.test.complete" '
                'uses old scheme not containing namespace from '
                'test case name "rhproduct.default.functional"'
            ]
        ),
    ]
)
def test_verify_topic_and_testcase_name(
        topic, testcase_name, expected_result, expected_log, caplog):
    caplog.set_level(logging.WARNING)
    assert utils.verify_topic_and_testcase_name(topic, testcase_name) == expected_result
    assert expected_log == [rec.message for rec in caplog.records]
