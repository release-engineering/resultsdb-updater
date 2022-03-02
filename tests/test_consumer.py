from __future__ import unicode_literals
from os import path
import json

import pytest
import mock
import requests

import resultsdbupdater.utils
from resultsdbupdater.message import create_message

from resultsdbupdater import consumer as ciconsumer


class FakeHub(object):
    config = {}


json_dir = path.join(path.abspath(path.dirname(__file__)), 'fake_messages')
consumer = ciconsumer.CIConsumer(FakeHub())
uuid_patcher = mock.patch(
    'resultsdbupdater.utils.uuid.uuid4',
    return_value='1bb0a6a5-3287-4321-9dc5-72258a302a37')
uuid_patcher.start()


@pytest.fixture
def mock_session():
    with mock.patch('resultsdbupdater.utils.session') as mocked:
        yield mocked


def get_fake_msg(name):
    fake_msg_path = path.join(json_dir, name + '.json')
    with open(fake_msg_path) as fake_msg_file:
        return json.load(fake_msg_file)


def test_full_consume_msg(mock_session):
    fake_msg = get_fake_msg('message')

    consumer.consume(fake_msg)
    assert mock_session.post.call_count == 2
    # Verify the URLs called
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    assert mock_session.post.call_args_list[1][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    expected_data_one = {
        'data': {
            'CI_tier': 1,
            'artifact': 'unknown',
            'brew_task_id': 14655525,
            'executed': 6,
            'executor': 'CI_OSP',
            'failed': 2,
            'item': 'libreswan-3.23-0.1.rc1.el6_9',
            'job_name': 'ci-libreswan-brew-rhel-6.9-z-candidate-2-runtest',
            'recipients': ['tbrady', 'rgronkowski'],
            'type': 'koji_build'
        },
        'groups': [{
            'ref_url': 'https://domain.local/job/ci-openstack/5154/',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'FAILED',
        'ref_url': 'https://domain.local/job/ci-openstack/5154/console',
        'testcase': {
            'name': ('baseos.ci-libreswan-brew-rhel-6.9-z-candidate-2-'
                     'runtest.CI_OSP'),
            'ref_url': 'https://domain.local/job/ci-openstack/'
        }
    }
    expected_data_two = {
        'data': {
            'CI_tier': 1,
            'artifact': 'unknown',
            'brew_task_id': 14655525,
            'item': 'libreswan-3.23-0.1.rc1.el6_9',
            'job_name': 'ci-libreswan-brew-rhel-6.9-z-candidate-2-runtest',
            'recipients': ['tbrady', 'rgronkowski'],
            'type': 'koji_build'
        },
        'groups': [{
            'ref_url': 'https://domain.local/job/ci-openstack/5154/',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'FAILED',
        'ref_url': 'https://domain.local/job/ci-openstack/5154/console',
        'testcase': {
            'name': ('baseos.ci-libreswan-brew-rhel-6.9-z-candidate-2-'
                     'runtest'),
            'ref_url': 'https://domain.local/job/ci-openstack/'
        }
    }
    actual_data_one = json.loads(
        mock_session.post.call_args_list[0][1]['data'])
    actual_data_two = json.loads(
        mock_session.post.call_args_list[1][1]['data'])
    assert expected_data_one == actual_data_one, actual_data_one
    assert expected_data_two == actual_data_two, actual_data_two


def test_full_consume_overall_rpmdiff_msg(mock_session):
    mock_session.get.return_value.json.return_value = {
        'data': [{
            'description': 'https://domain.local/run/12345',
            'uuid': '529da400-fc74-4b28-af81-52f56816a2cb'
        }]
    }

    fake_msg = get_fake_msg('rpmdiff_message')

    consumer.consume(fake_msg)
    # Assert it checked to see if an existing group exists to add the new
    # result to
    mock_session.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'https://domain.local/run/12345'),
        timeout=15,
        verify=None
    )
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    expected_data = {
        'data': {
            'item': 'setup-2.8.71-5.el7_1',
            'newnvr': 'setup-2.8.71-5.el7_1',
            'oldnvr': 'setup-2.8.71-5.el7',
            'scratch': True,
            'taskid': 12644803,
            'type': 'koji_build'
        },
        'groups': [{
            'description': 'https://domain.local/run/12345',
            'ref_url': 'https://domain.local/run/12345',
            'uuid': '529da400-fc74-4b28-af81-52f56816a2cb'
        }],
        'note': '',
        'outcome': 'NEEDS_INSPECTION',
        'ref_url': 'https://domain.local/run/12345',
        'testcase': {
            'name': 'dist.rpmdiff.analysis',
            'ref_url': 'https://domain.local/rpmdiff-in-ci'
        }
    }
    assert expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_full_consume_rpmdiff_msg(mock_session):
    mock_session.get.return_value.json.return_value = {'data': []}
    fake_msg = get_fake_msg('rpmdiff_message_two')

    consumer.consume(fake_msg)
    # Assert it checked to see if an existing group exists to add the new
    # result to, but this time nothing was returned
    mock_session.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'https://domain.local/run/12345'),
        timeout=15,
        verify=None
    )
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    expected_data = {
        'data': {
            'item': 'lapack-3.4.2-8.el7 lapack-3.4.2-7.el7',
            'newnvr': 'lapack-3.4.2-8.el7',
            'oldnvr': 'lapack-3.4.2-7.el7',
            'scratch': False,
            'taskid': 12665429,
            'type': 'koji_build_pair'
        },
        'groups': [{'description': 'https://domain.local/run/12345',
                    'ref_url': 'https://domain.local/run/12345',
                    'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'}],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': 'https://domain.local/run/12345/13',
        'testcase': {
            'name': 'dist.rpmdiff.comparison.abi_symbols',
            'ref_url': ('https://domain.local/display/HTD/rpmdiff-abi-'
                        'symbols')
        }
    }
    assert expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_full_consume_rpmdiff_msg_with_bad_ref_url(mock_session, caplog):
    fake_msg = get_fake_msg('rpmdiff_message')
    fake_msg['body']['msg']['ref_url'] = 'https://example.com/bad/123'
    consumer.consume(fake_msg)
    mock_session.post.assert_not_called()
    assert (
        'Invalid message rejected: The ref_url "https://example.com/bad/123"'
        ' did not match the rpmdiff URL scheme'
    ) in caplog.text


def test_full_consume_covscan_msg(mock_session):
    mock_session.get.return_value.json.return_value = {'data': []}
    fake_msg = get_fake_msg('covscan_message')

    consumer.consume(fake_msg)
    # Assert it checked to see if an existing group exists to add the new
    # result to, but this time nothing was returned
    mock_session.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'http://domain.local/covscanhub/task/64208/log/added.html'),
        timeout=15,
        verify=None
    )
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    expected_data = {
        'data': {
            'item': 'ipa-4.5.4-5.el7 ipa-4.5.4-4.el7',
            'newnvr': 'ipa-4.5.4-5.el7',
            'oldnvr': 'ipa-4.5.4-4.el7',
            'scratch': True,
            'taskid': 14655680,
            'type': 'koji_build_pair'
        },
        'groups': [{
            'description': ('http://domain.local/covscanhub/task/64208/log'
                            '/added.html'),
            'ref_url': ('http://domain.local/covscanhub/task/64208/log/'
                        'added.html'),
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': ('http://domain.local/covscanhub/task/64208/log/'
                    'added.html'),
        'testcase': {
            'name': 'dist.covscan',
            'ref_url': 'https://domain.local/covscan-in-ci'
        }
    }
    assert expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_full_consume_bulk_results_msg(mock_session):
    fake_msg = get_fake_msg('bulk_results_message')

    consumer.consume(fake_msg)
    all_expected_data = {
        'dva.ami.memory': {
            'data': {'item': 'ami-b63769a1'},
            'groups': [{
                'ref_url': 'http://domain.local/path/to/test',
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }],
            'note': '',
            'outcome': 'PASSED',
            'ref_url': 'http://domain.local/path/to/test/memory',
            'testcase': 'dva.ami.memory'
        },
        'dva.ami.no_avc_denials': {
            'data': {'item': 'ami-b63769a1'},
            'groups': [{
                'ref_url': 'http://domain.local/path/to/test',
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }],
            'note': '',
            'outcome': 'PASSED',
            'ref_url': ('http://domain.local/path/to/test/'
                        'no_avc_denials_test'),
            'testcase': 'dva.ami.no_avc_denials'
        },
        'dva.ami': {
            'data': {'item': 'ami-b63769a1'},
            'groups': [{
                'ref_url': 'http://domain.local/path/to/test',
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }],
            'note': '',
            'outcome': 'PASSED',
            'ref_url': 'http://domain.local/path/to/test',
            'testcase': 'dva.ami'
        }
    }
    # We can't guarantee the order of when the results are created, so this
    # is a workaround
    testcase_names = list(all_expected_data.keys())
    for i in range(len(all_expected_data)):
        post_call_data = json.loads(
            mock_session.post.call_args_list[i][1]['data'])
        testcase_name = post_call_data['testcase']
        assert post_call_data == all_expected_data[testcase_name]
        testcase_names.pop(testcase_names.index(testcase_name))
    msg = 'Not all the expected testcases were processed'
    assert len(testcase_names) == 0, msg


def test_full_consume_bogus_msg(mock_session):
    fake_msg = get_fake_msg('bogus')
    consumer.consume(fake_msg)
    mock_session.post.assert_not_called()


def test_full_consume_pipeline_failure_msg(mock_session):
    fake_msg = get_fake_msg('pipeline_failure_message')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'tigervnc-1.8.0-5.el9000+5',
            'type': 'brew-build_scratch',

            'component': 'tigervnc',
            'error_reason': 'unknown execution error',
            'brew_task_id': '15665813',
            'category': 'functional',
            'scratch': True,
            'issuer': None,
            'rebuild': (
                'https://domain.redhat.com/job/downstream-rhel9000-build-pipeline/'
                '34/rebuild/parameterized'),
            'log': (
                'https://domain.redhat.com/job/downstream-rhel9000-build-pipeline/'
                '34/console'),
            'system_os': 'TODO',
            'system_provider': 'TODO',
            'ci_name': 'Continuous Infra',
            'ci_url': 'https://domain.redhat.com/',
            'ci_team': 'contra',
            'ci_irc': '#contra',
            'ci_email': 'continuous-infra@redhat.com',
            'recipients': []
        },
        'groups': [{
            'url': 'https://domain.redhat.com/job/downstream-rhel9000-build-pipeline/34/',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'ERROR',
        'ref_url': 'https://domain.redhat.com/job/downstream-rhel9000-build-pipeline/34/',
        'testcase': {
            'name': 'contra.pipeline.functional',
        },
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_full_consume_brew_build_v2_failure_msg(mock_session):
    fake_msg = get_fake_msg('brew-build.test.error.v2')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'setup-2.8.71-7.el7_4',
            'type': 'brew-build_scratch',

            'component': 'setup',
            'error_reason': 'CI pipeline aborted',
            'issue_url': 'http://sentry.somewhere.com/baseos/production/issues/1149/',
            'brew_task_id': 14546276,
            'category': 'functional',
            'scratch': True,
            'issuer': 'alice',
            'rebuild': 'https://somewhere.com/job/ci-openstack/4794/rebuild/parametrized',
            'log': 'https://somewhere.com/job/ci-openstack/4794/console',
            'system_os': None,
            'system_provider': None,
            'ci_name': 'BaseOS CI',
            'ci_url': 'https://somewhere.com',
            'ci_team': 'BaseOS',
            'ci_irc': '#baseosci',
            'ci_email': 'baseos-ci@somewhere.com',
            'recipients': ['alice', 'bob']
        },
        'groups': [{
            'url': 'https://somewhere.com/job/ci-openstack/4794',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': 'Operation team was notified about the issue, follow the Sentry issue link',
        'outcome': 'ERROR',
        'ref_url': 'https://somewhere.com/job/ci-openstack/4794',
        'testcase': {
            'name': 'baseos-qe.baseos-ci.tier1.functional',
            'ref_url': 'https://my-ci-system/docs/contribute-retrigger-reproduce',
        },
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_brew_build_scratch_null(mock_session):
    fake_msg = get_fake_msg('brew-build.test.error.v2')
    fake_msg['body']['msg']['artifact']['scratch'] = None

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1

    actual_data = json.loads(mock_session.post.call_args_list[0][1]['data'])
    assert actual_data['data']['scratch'] is False


@pytest.mark.parametrize('spec_version', (None, '0.1.0', ''))
def test_full_consume_platformci_success_msg(mock_session, spec_version):
    fake_msg = get_fake_msg('platformci_success_message')

    if spec_version is None:
        del fake_msg['body']['msg']['version']
    else:
        fake_msg['body']['msg']['version'] = spec_version

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'setup-2.8.71-7.el7_4',
            'type': 'brew-build_scratch',
            'component': 'setup',
            'brew_task_id': '15667760',
            'category': 'functional',
            'scratch': True,
            'issuer': 'ovasik',
            'rebuild': (
                'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com/'
                'job/ci-openstack/8465/rebuild/parameterized'),
            'log': (
                'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com/'
                'job/ci-openstack/8465/console'),
            'system_os': None,
            'system_provider': None,
            'ci_name': 'BaseOS CI',
            'ci_url': 'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com',
            'ci_team': 'BaseOS QE',
            'ci_irc': '#baseosci',
            'ci_email': 'baseos-ci@redhat.com',
            'recipients': ['jscotka', 'ovasik']
        },
        'groups': [{
            'url': (
                'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com/'
                'job/ci-openstack/8465/'),
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': (
            'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com/'
            'job/ci-openstack/8465/'),
        'testcase': {
            'name': 'baseos.tier1.functional',
        },
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_full_consume_osci_success_msg(mock_session):
    fake_msg = get_fake_msg('osci_success_message')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'passwd-0.80-1.el8+5',
            'type': 'brew-build_scratch',
            'component': 'passwd',
            'brew_task_id': '15801580',
            'category': 'functional',
            'scratch': True,
            'issuer': None,
            'rebuild': (
                'https://some-jenkins.osci.redhat.com/'
                'job/pipeline/21/rebuild/parameterized'),
            'log': (
                'https://some-jenkins.osci.redhat.com/'
                'job/pipeline/21/console'),
            'system_os': 'TODO',
            'system_provider': 'TODO',
            'ci_name': 'Continuous Infra',
            'ci_url': 'https://some-jenkins.osci.redhat.com/',
            'ci_team': 'contra',
            'ci_irc': '#contra',
            'ci_email': 'continuous-infra@redhat.com',
            'recipients': []
        },
        'groups': [{
            'url': (
                'https://some-jenkins.osci.redhat.com/'
                'job/pipeline/21/'),
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'FAILED',
        'ref_url': (
            'https://some-jenkins.osci.redhat.com/'
            'job/pipeline/21/'),
        'testcase': {
            'name': 'osci.pipeline.functional',
        },
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_fedora_ci_no_test(mock_session, caplog):
    """ Make sure message is not processed if test is missing. """
    fake_msg = get_fake_msg('fedora-ci-message-no-test')
    consumer.consume(fake_msg)
    mock_session.post.assert_not_called()
    assert 'Invalid message rejected: Missing field "test.result"' in caplog.text


def test_full_consume_compose_msg(mock_session):
    fake_msg = get_fake_msg('compose_message')
    consumer.consume(fake_msg)
    # Verify the URLs called
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    url = 'https://rtt-jenkins/job/compose-RHEL-X.0-rel-eng-tier2-acceptance/1/'
    expected_data = {
        'testcase': {
            'name': 'rtt.tier2.functional',
            'ref_url': 'https://example.com/test-case-documentation',
        },
        'groups': [
            {
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37',
                'url': url
            }
        ],
        'outcome': 'PASSED',
        'ref_url': url,
        'note': '',
        'data': {
            'item': 'RHEL-X.0-20180101.1/unknown/x86_64',
            'productmd.compose.id': 'RHEL-X.0-20180101.1',
            'type': 'productmd-compose',
            'category': 'functional',
            'log': url + 'console',
            'system_provider': 'beaker',
            'system_architecture': 'x86_64',
            'ci_name': 'RTT CI',
            'ci_team': 'RTT',
            'ci_url': 'https://rtt-jenkins',
            'ci_irc': '#rtt',
            'ci_email': 'release-test-team<AT>redhat.com',
            'recipients': []
        }
    }

    actual_data = json.loads(
        mock_session.post.call_args_list[0][1]['data'])
    assert expected_data == actual_data, actual_data


def test_full_consume_compose_msg_v2(mock_session):
    fake_msg = get_fake_msg('compose_message_v2')
    consumer.consume(fake_msg)
    # Verify the URLs called
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    url = 'https://rtt-jenkins/job/compose-RHEL-X.0-rel-eng-tier2-acceptance/1/'
    expected_data = {
        'testcase': {
            'name': 'rtt.installability.validation',
            'ref_url': 'https://example.com/test-case-documentation',
        },
        'groups': [{
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37',
            'url': url
        }],
        'outcome': 'PASSED',
        'ref_url': 'https://rtt-jenkins/job/compose-RHEL-X.0-rel-eng-tier2-acceptance/1/',
        'note': '',
        'data': {
            'item': 'RHEL-X.0-20200512.1/BaseOS/x86_64',
            'productmd.compose.id': 'RHEL-X.0-20200512.1',
            'type': 'productmd-compose',
            'category': 'validation',
            'log': url + 'console',
            'system_provider': 'beaker',
            'system_variant': 'BaseOS',
            'system_architecture': 'x86_64',
            'scenario': 'BaseOS x86_64',
            'ci_name': 'RTT CI',
            'ci_team': 'RTT',
            'ci_url': 'https://rtt-jenkins',
            'ci_irc': 'not available',
            'ci_email': 'release-test-team@example.com',
            'publisher_id': 'msg-client-rtt',
            'recipients': []
        }
    }

    actual_data = json.loads(
        mock_session.post.call_args_list[0][1]['data'])
    assert expected_data == actual_data, actual_data


def test_product_build(mock_session):
    fake_msg = get_fake_msg('product_build')
    consumer.consume(fake_msg)
    # Verify the URLs called
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    url = 'https://jenkins-cnv14.192.168.42.176.nip.io/job/send-product-build-message-resultdb/3/'
    expected_data = {
        'data': {
            'category': 'validation',
            'ci_email': 'cpaas-ops@redhat.com',
            'ci_irc': 'not available',
            'ci_name': 'CPaaS',
            'ci_team': 'CPaaS',
            'ci_url': 'https://jenkins-cnv14.192.168.42.176.nip.io/',
            'item': 'CNV-1.4.0-20191023.57',
            'log': url + 'console',
            'product': 'CNV',
            'recipients': [],
            'release': '20191023.57',
            'system_architecture': 'x86_64',
            'type': 'product-build',
            'version': '1.4.0'
        },
        'groups': [
            {
                'url': url,
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            }
        ],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': url,
        'testcase': {
            'name': 'cnv.product-build.smoke-test.validation',
        }
    }
    assert expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_queued_outcome_msg(mock_session):
    fake_msg = get_fake_msg('platformci_queued_message')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'openstack-neutron-lbaas-13.0.1-0.20180913154426.eb47e20.el7ost',
            'type': 'brew-build',
            'component': 'openstack-neutron-lbaas',
            'brew_task_id': '18310713',
            'category': 'static-analysis',
            'scratch': False,
            'issuer': None,
            'rebuild': (
                'https://some-jenkins.redhat.com/job/ci-brew-dispatcher/'
                '125157/rebuild/parameterized'),
            'log': (
                'https://some-jenkins.redhat.com/job/ci-brew-dispatcher/'
                '125157/console'),
            'system_os': None,
            'system_provider': None,
            'ci_name': 'PlatformCI',
            'ci_url': 'https://some-jenkins.redhat.com',
            'ci_team': 'Platform QE',
            'ci_irc': '#baseosci',
            'ci_email': 'platform-ci@redhat.com',
            'recipients': []
        },
        'groups': [{'url': 'https://some-jenkins.redhat.com/job/ci-brew-dispatcher/125157/',
                   'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'}],
        'note': '',
        'outcome': 'QUEUED',
        'ref_url': 'https://some-jenkins.redhat.com/job/ci-brew-dispatcher/125157/',
        'testcase': {
            'name': 'baseos-ci.brew-build.covscan.static-analysis',
        }
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_queued_running_msg(mock_session):
    fake_msg = get_fake_msg('platformci_running_message')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'setup-2.8.71-7.el7_4',
            'type': 'brew-build_scratch',
            'component': 'setup',
            'brew_task_id': '18325602',
            'category': 'static-analysis',
            'scratch': True,
            'issuer': None,
            'rebuild': (
                'https://some-jenkins.redhat.com/job/ci-covscan/'
                '109087/rebuild/parameterized'),
            'log': (
                'https://some-jenkins.redhat.com/job/ci-covscan/'
                '109087/console'),
            'system_os': None,
            'system_provider': None,
            'ci_name': 'Platform CI',
            'ci_url': 'https://some-jenkins.redhat.com',
            'ci_team': 'Platform QE',
            'ci_irc': '#baseosci',
            'ci_email': 'platform-ci@redhat.com',
            'recipients': []
        },
        'groups': [{'url': 'https://some-jenkins.redhat.com/job/ci-covscan/109087/',
                   'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'}],
        'note': '',
        'outcome': 'RUNNING',
        'ref_url': 'https://some-jenkins.redhat.com/job/ci-covscan/109087/',
        'testcase': {
            'name': 'baseos-ci.brew-build.covscan.static-analysis',
        }
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_pelc_component_version_msg(mock_session):
    fake_msg = get_fake_msg('pelc_component_version')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'

    # Verify the URLs called
    url = 'https://rcm-tools-jenkins/3/'
    expected_data = {
        'testcase': {
            'name': 'pelc.scan.validation',
        },
        'groups': [
            {
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37',
                'url': url
            }
        ],
        'outcome': 'PASSED',
        'ref_url': url,
        'note': '',
        'data': {
            'item': '389-ds-base-1.4.0.10',
            'component': '389-ds-base',
            'version': '1.4.0.10',
            'type': 'component-version',
            'category': 'validation',
            'log': url + 'console',
            'ci_name': 'PELC',
            'ci_team': 'PnT DevOps',
            'ci_url': 'https://rcm-tools-jenkins',
            'ci_irc': '#pnt-devops',
            'ci_email': 'rbean<AT>redhat.com',
            'recipients': []
        }
    }

    actual_data = json.loads(
        mock_session.post.call_args_list[0][1]['data'])
    assert expected_data == actual_data, actual_data


def test_full_consume_redhat_module_success_msg(mock_session):
    fake_msg = get_fake_msg('redhat_module_message')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'go-toolset-rhel8_8-820181119195405.b754926a',
            'type': 'redhat-module',
            'context': 'b754926a',
            'name': 'go-toolset',
            'nsvc': 'go-toolset-rhel8_8-820181119195405.b754926a',
            'stream': 'rhel8',
            'version': '820181119195405',
            'mbs_id': '2240',
            'category': 'functional',
            'issuer': 'deparker',
            'rebuild': (
                'https://baseos-jenkins.rhev-ci-vms.eng.rdu2.redhat.com'
                '/job/ci-openstack-mbs/45/rebuild/parameterized'
            ),
            'log': (
                'https://baseos-jenkins.rhev-ci-vms.eng.rdu2.redhat.com'
                '/job/ci-openstack-mbs/45/console'
            ),
            'ci_name': 'BaseOS CI',
            'ci_url': 'https://baseos-jenkins.rhev-ci-vms.eng.rdu2.redhat.com',
            'ci_team': 'BaseOS QE',
            'ci_irc': '#baseosci',
            'ci_email': 'baseos-ci@redhat.com',
            'system_os': None,
            'system_provider': None,
            'recipients': [
                'deparker',
                'emachado',
                'mcermak',
                'mprchlik',
                'qe-baseos-tools-commits',
            ]
        },
        'groups': [{
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37',
            'url': (
                'https://baseos-jenkins.rhev-ci-vms.eng.rdu2.redhat.com'
                '/job/ci-openstack-mbs/45/'
            )
        }],
        'note': '',
        'outcome': 'FAILED',
        'ref_url': (
            'https://baseos-jenkins.rhev-ci-vms.eng.rdu2.redhat.com/job/ci-openstack-mbs/45/'),
        'testcase': {
            'name': 'baseos-ci.redhat-module.tier1.functional',
        },
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_full_consume_redhat_module_with_bad_nsvc(mock_session, caplog):
    fake_msg = get_fake_msg('redhat_module_message')
    fake_msg['body']['msg']['artifact']['nsvc'] = 'BAD_FORMAT'
    consumer.consume(fake_msg)
    mock_session.post.assert_not_called()
    assert 'Invalid message rejected: Invalid nsvc "BAD_FORMAT" encountered' in caplog.text


def test_full_consume_redhat_module_with_unknown_artifact_type(mock_session, caplog):
    fake_msg = get_fake_msg('redhat_module_message')
    fake_msg['body']['msg']['artifact']['type'] = 'mysterious-artifact'
    consumer.consume(fake_msg)
    mock_session.post.assert_not_called()
    assert 'Invalid message rejected: Unknown artifact type "mysterious-artifact"' in caplog.text


def test_redhat_container_image_msg(mock_session):
    fake_msg = get_fake_msg('redhat-container-image.test.complete')
    consumer.consume(fake_msg)

    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'sha256:67dad89757a55bfdfabec8abd0e22f8c7c12a1856514726470228063ed865934',
            'type': 'redhat-container-image',
            'brew_task_id': 835014,
            'brew_build_id': None,
            'category': 'functional',
            'full_names': [
                'example.com:8888/openshift/'
                'ose-machine-config-operator-container:v4.3.0-201911080317'],
            'registry_url': 'example.com:8888',
            'tag': 'v4.3.0-201911080317',
            'issuer': 'user',
            'component': 'ose-machine-config-operator',
            'name': 'ose-machine-config-operator-container',
            'namespace': 'openshift',
            'rebuild': 'https://somewhere.com/job/ci-job/4794/rebuild/parametrized',
            'log': 'https://somewhere.com/job/ci-job/4794/console',
            'ci_name': 'C3I Jenkins',
            'ci_url': 'https://example.com',
            'ci_team': 'DevOps',
            'ci_irc': '#some-channel',
            'ci_email': 'someone@example.com',
            'recipients': ['alice', 'bob'],
            'scratch': False,
            'nvr': 'ose-machine-config-operator-container-v4.3.0-201911080317',
            'source': (
                'git://dist-git.com/containers/ose-machine-config-operator'
                '#422f238e6011b411c93198ad00299a4002979843'
            )
        },
        'groups': [{
            'url': 'https://somewhere.com/job/ci-job/4794',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37',
        }],
        'note': 'Some notes.',
        'outcome': 'FAILED',
        'ref_url': 'https://somewhere.com/job/ci-job/4794',
        'testcase': {
            'name': 'factory2.c3i-ci.tier1.functional',
        },
    }
    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_redhat_advisory_complete_msg(mock_session):
    fake_msg = get_fake_msg('redhat-advisory.test.complete')
    consumer.consume(fake_msg)

    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'category': 'validation',
            'ci_email': 'fcctt-team@redhat.com',
            'ci_irc': '#fcctt-team-is-the-best',
            'ci_name': 'Fictional Content Compressibility Test Team Jenkins (FCCTT)',
            'ci_team': 'Fictional Content Compressibility Testing Team',
            'ci_url': 'https://example.redhat.com',
            'item': 'RHBA-2017:01234-03',
            'log': 'https://example.redhat.com/tests/583271/file/stdout.txt',
            'log_raw': 'https://somewhere.com/583271/log_raw',
            'log_stream': 'https://somewhere.com/583271/log_stream',
            'numeric_id': None,
            'pipeline_build': None,
            'pipeline_id': 'ac11dcddf99a',
            'pipeline_name': 'ci-job',
            'pipeline_stage': 'testing',
            'recipients': [],
            'system_os': None,
            'system_provider': None,
            'type': 'redhat-advisory'
        },
        'groups': [{
            'url': 'https://example.redhat.com/tests/583271',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': 'https://example.redhat.com/tests/583271',
        'testcase': {
            'name': 'fcctt.compression.validation',
        },
    }
    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_redhat_advisory_error_msg(mock_session):
    fake_msg = get_fake_msg('redhat-advisory.test.error')
    consumer.consume(fake_msg)

    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'category': 'validation',
            'ci_email': 'fcctt-team@redhat.com',
            'ci_irc': '#fcctt-team-is-the-best',
            'ci_name': 'Fictional Content Compressibility Test Team Jenkins (FCCTT)',
            'ci_team': 'Fictional Content Compressibility Testing Team',
            'ci_url': 'https://example.redhat.com',
            'error_reason': 'content is not adequately compressible',
            'item': 'RHBA-2017:01234-03',
            'log': 'https://example.redhat.com/tests/583271/file/stdout.txt',
            'log_raw': None,
            'log_stream': None,
            'numeric_id': None,
            'pipeline_build': None,
            'pipeline_id': 'ac11dcddf99a',
            'pipeline_name': 'ci-job',
            'pipeline_stage': None,
            'recipients': [],
            'system_os': None,
            'system_provider': None,
            'type': 'redhat-advisory'
        },
        'groups': [{
            'url': 'https://example.redhat.com/tests/583271',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'ERROR',
        'ref_url': 'https://example.redhat.com/tests/583271',
        'testcase': {
            'name': 'fcctt.compression.validation',
        },
    }
    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_container_image_msg(mock_session):
    fake_msg = get_fake_msg('container_image_message')
    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        "note": "",
        "ref_url": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/job/waiverdb-test"
                   "/job/waiverdb-test-stage-waiverdb-dev-integration-test/104/",
        "testcase": {
            "name": "waiverdb-test.tier1.integration"
        },
        "groups": [
            {
                "url": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/job"
                       "/waiverdb-test/job/waiverdb-test-stage-waiverdb-dev-integration-test/104/",
                "uuid": "1bb0a6a5-3287-4321-9dc5-72258a302a37"
            }
        ],
        "outcome": "PASSED",
        "data": {
            "category": "integration",
            "system_os": "docker-registry.engineering.redhat.com"
                         "/factory2/waiverdb-jenkins-slave:latest",
            "log": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/job"
                   "/waiverdb-test/job/waiverdb-test-stage-waiverdb-dev-integration-test"
                   "/104//console",
            "repository": "factory2/waiverdb",
            "issuer": "c3i-jenkins",
            "scratch": True,
            "ci_email": "pnt-factory2-devel@redhat.com",
            "recipients": [

            ],
            "ci_name": "C3I Jenkins",
            "ci_irc": "#pnt-devops-dev",
            "item": "factory2/waiverdb@sha256:693377241d5bc55af239fdc51"
                    "83bcc97d7c5c097bebe84097c4388063a3950cc",
            "system_provider": "openshift",
            "ci_url": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/",
            "xunit": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/"
                     "job/waiverdb-test/job/waiverdb-test"
                     "-stage-waiverdb-dev-integration-test/104/"
                     "/artifacts/junit-functional-tests.xml",
            "system_architecture": "x86_64",
            "ci_team": "DevOps",
            "type": "container-image",
            "rebuild": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/job"
                       "/waiverdb-test/job/waiverdb"
                       "-test-stage-waiverdb-dev-integration-test/104//rebuild/parametrized",
            "digest": "sha256:693377241d5bc55af239fdc5183bcc97d7c5c097bebe84097c4388063a3950cc",
            "nvr": "waiverdb:test"
        }
    }
    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


@pytest.mark.parametrize('consume_fn', (
    resultsdbupdater.utils.handle_ci_umb,
    resultsdbupdater.utils.handle_ci_metrics,
    resultsdbupdater.utils.handle_resultsdb_format,
))
def test_publisher_id(mock_session, consume_fn):
    mock_session.get.return_value.json.return_value = {'data': []}

    fake_msg = get_fake_msg('jmsx_user_id')
    consume_fn(create_message(fake_msg))
    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'

    actual_data = json.loads(
        mock_session.post.call_args_list[0][1]['data'])
    assert 'msg-example-ci' == actual_data['data'].get('publisher_id'), actual_data


def test_topic_namespace_match():
    fake_msg = get_fake_msg('redhat_module_message')
    fake_msg['topic'] = '/topic/VirtualTopic.eng.ci.baseos-ci.redhat-module.test.complete'

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_called_once()


def test_topic_namespace_mismatch(caplog):
    fake_msg = get_fake_msg('redhat_module_message')
    fake_msg['topic'] = '/topic/VirtualTopic.eng.ci.bad-ci.redhat-module.test.complete'

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_not_called()
        assert any(
            'namespace "baseos-ci" does not match message topic' in rec.message
            for rec in caplog.records)


def test_topic_namespace_missing(caplog):
    fake_msg = get_fake_msg('redhat_module_message')

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_called_once()
        assert any(
            'uses old scheme not containing namespace' in rec.message
            for rec in caplog.records)


def test_full_consume_post_failed(mock_session):
    mock_session.post.return_value.raise_for_status.side_effect = \
        requests.exceptions.HTTPError()
    fake_msg = get_fake_msg('message')

    with pytest.raises(requests.exceptions.HTTPError):
        consumer._consume_helper(create_message(fake_msg))


def test_full_consume_post_timeout(mock_session):
    mock_session.post.side_effect = requests.exceptions.Timeout()
    fake_msg = get_fake_msg('message')

    with pytest.raises(requests.exceptions.Timeout):
        consumer._consume_helper(create_message(fake_msg))


def test_consume_no_exception_on_bad_message(caplog):
    consumer.consume({})
    assert 'Failed to parse message version' in caplog.text


def test_fedora_ci_message_brew_build_test_complete_version_2(mock_session):
    fake_msg = get_fake_msg('fedora-ci-message-brew-build.test.complete-2.0.0')
    consumer.consume(fake_msg)

    # Verify the post URL
    assert mock_session.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_session.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'binutils-2.30-43.el8',
            'type': 'brew-build',
            'component': 'binutils',
            'brew_task_id': 18400235,
            'category': 'functional',
            'scratch': False,
            'issuer': 'batman',
            'rebuild': (
                'https://jenkins/'
                'job/pipeline/170/rebuild/parameterized'),
            'log': (
                'https://jenkins/'
                'job/pipeline/170/console'),
            'system_os': 'RHEL-8.0.0',
            'system_provider': 'downshaft',
            'ci_name': 'TEAM',
            'ci_url': 'not available',
            'ci_team': 'team',
            'ci_irc': '#team',
            'ci_email': 'team-list@redhat.com',
            'recipients': ['ovasik', 'mvadkert']
        },
        'groups': [{
            'url': (
                'https://jenkins/'
                'job/pipeline/170/'),
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'outcome': 'PASSED',
        'ref_url': (
            'https://jenkins/'
            'job/pipeline/170/'),
        'testcase': {
            'name': 'team.build.tier0.functional',
        },
        'note': ''
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_fedora_ci_message_brew_build_group_test_complete(mock_session):
    fake_msg = get_fake_msg('brew-build-group.test.complete')
    consumer.consume(fake_msg)
    assert mock_session.post.call_count == 1
    builds = fake_msg['body']['msg']['artifact']['builds']
    builds = [json.dumps(item) for item in builds]
    all_expected_data = {
        'data': {
            'item': 'sha256:acbfb0c61199e5a05f07ee4ec2cdf7fb93376513b82cb5ad444e4d94e4258785',
            'type': 'brew-build-group',
            'repository': 'https://some.url/repo',
            'category': 'functional',
            'builds': builds,
            'rebuild': 'https://somewhere.com/job/ci-openstack/4794/rebuild/parametrized',
            'log': 'https://somewhere.com/job/ci-openstack/4794/console',
            'system_os': 'Fedora-Cloud-Base-28',
            'system_provider': 'openstack',
            'ci_name': 'BaseOS CI',
            'ci_url': 'https://somewhere.com',
            'ci_team': 'BaseOS',
            'ci_irc': '#baseosci',
            'ci_email': 'baseos-ci@somewhere.com',
            'recipients': ['claire', 'daniel'],
        },
        'groups': [{
            'url': 'https://somewhere.com/job/ci-openstack/4794',
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'outcome': 'FAILED',
        'ref_url': 'https://somewhere.com/job/ci-openstack/4794',
        'testcase': {
            'name': 'baseos-qe.baseos-ci.tier1.functional',
        },
        'note': 'Some notes.'
    }

    assert all_expected_data == \
        json.loads(mock_session.post.call_args_list[0][1]['data'])


def test_consuming_invalid_messages(mock_session, caplog):
    with pytest.raises(RuntimeWarning):
        consumer.validate({})
    assert 'Failed to validate message: {' in caplog.text

    consumer.validate({'body': None})
    consumer.consume({'body': None})
    consumer.consume({})


def test_results_create_failed(mock_session, caplog):
    fake_msg = get_fake_msg('osci_success_message')

    mock_session.post.return_value.json.return_value = {'message': 'Dummy failure message'}
    mock_session.post.return_value.status_code = 400

    consumer.consume(fake_msg)
    assert mock_session.post.call_count == 1
    assert 'Failed to create result: Dummy failure message; Payload: {' in caplog.text


def test_consumer_no_throw(mock_session, caplog):
    """
    Consumer must not throw an exception (it would cause NACK and potentially
    blocked queue).
    """
    fake_msg = get_fake_msg('osci_success_message')

    mock_session.post.side_effect = RuntimeError

    consumer.consume(fake_msg)
    assert 'Unexpected exception' in caplog.text
    assert 'RuntimeError' in caplog.text


def test_unexpected_status(mock_session, caplog):
    fake_msg = get_fake_msg('container_image_message')
    del fake_msg['body']['msg']['status']
    consumer.consume(fake_msg)
    mock_session.post.assert_not_called()
    assert 'Unexpected result status/outcome, expected a string, got: None' in caplog.text


def test_product_scenario_msg(mock_session):
    fake_msg = get_fake_msg('product-scenario.test.complete')
    consumer.consume(fake_msg)

    expected_data = [
        {
            "testcase": {
                "name": "interop.product-scenario.interoperability",
            },
            "groups": [
                {
                    "uuid": "1bb0a6a5-3287-4321-9dc5-72258a302a37",
                    "url": "https://somewhere.com/job/testjob/1"
                }
            ],
            "outcome": "PASSED",
            "ref_url": "https://somewhere.com/job/testjob/1",
            "note": "",
            "data": {
                "item": ["1234", "product1-1.0.0-1", "product2-1.0.0-1"],
                "type": "product-scenario",
                "rebuild": None,
                "log": "https://somewhere.com/job/testjob/1/console",
                "system_os": "RHEL-8.1.0-20190523.0-x86_64",
                "system_provider": "openstack",
                "ci_name": "CSI-QE",
                "ci_team": "CSI-QE",
                "ci_url": "csi-qe@somewhere.com",
                "ci_irc": "not available",
                "ci_email": "https://somewhere.com/user-documentation",
                "recipients": [],

                "products": [
                    mock.ANY,
                    mock.ANY,
                ],
            }
        }
    ]

    actual_data = [
        json.loads(args[1]['data'])
        for args in mock_session.post.call_args_list
    ]

    assert expected_data == actual_data

    expected_products = fake_msg["body"]["msg"]["artifact"]["products"]
    actual_products = [
        json.loads(product)
        for product in actual_data[0]["data"]["products"]
    ]
    assert expected_products == actual_products


def test_unsupported_version(caplog):
    """
    Versions 1.0.0 and greater are ignored here and consumed by a new service.
    """
    fake_msg = get_fake_msg('brew-build.test.error.v2')
    fake_msg['body']['msg']['version'] = '1.0.0'

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_not_called()
        assert any(
            'Unsupported version: 1.0.0' in rec.message
            for rec in caplog.records)
