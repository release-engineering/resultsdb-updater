from __future__ import unicode_literals
from os import path
import json

import pytest
import mock
import requests

import resultsdbupdater.utils

from resultsdbupdater import consumer as ciconsumer


class FakeHub(object):
    config = {}


json_dir = path.join(path.abspath(path.dirname(__file__)), 'fake_messages')
consumer = ciconsumer.CIConsumer(FakeHub())
uuid_patcher = mock.patch(
    'resultsdbupdater.utils.uuid.uuid4',
    return_value='1bb0a6a5-3287-4321-9dc5-72258a302a37')
uuid_patcher.start()


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the URLs called
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    assert mock_requests.post.call_args_list[1][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 2
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
        mock_requests.post.call_args_list[0][1]['data'])
    actual_data_two = json.loads(
        mock_requests.post.call_args_list[1][1]['data'])
    assert expected_data_one == actual_data_one, actual_data_one
    assert expected_data_two == actual_data_two, actual_data_two


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_overall_rpmdiff_msg(mock_requests):
    mock_requests.get.return_value.json.return_value = {
        'data': [{
            'description': 'https://domain.local/run/12345',
            'uuid': '529da400-fc74-4b28-af81-52f56816a2cb'
        }]
    }

    fake_msg_path = path.join(json_dir, 'rpmdiff_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Assert it checked to see if an existing group exists to add the new
    # result to
    mock_requests.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'https://domain.local/run/12345'),
        headers=mock.ANY,
        timeout=15,
        verify=None
    )
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_rpmdiff_msg(mock_requests):
    mock_requests.get.return_value.json.return_value = {'data': []}
    fake_msg_path = path.join(json_dir, 'rpmdiff_message_two.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Assert it checked to see if an existing group exists to add the new
    # result to, but this time nothing was returned
    mock_requests.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'https://domain.local/run/12345'),
        headers=mock.ANY,
        timeout=15,
        verify=None
    )
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_covscan_msg(mock_requests):
    mock_requests.get.return_value.json.return_value = {'data': []}
    fake_msg_path = path.join(json_dir, 'covscan_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Assert it checked to see if an existing group exists to add the new
    # result to, but this time nothing was returned
    mock_requests.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'http://domain.local/covscanhub/task/64208/log/added.html'),
        headers=mock.ANY,
        timeout=15,
        verify=None
    )
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_bulk_results_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'bulk_results_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

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
            mock_requests.post.call_args_list[i][1]['data'])
        testcase_name = post_call_data['testcase']
        assert post_call_data == all_expected_data[testcase_name]
        testcase_names.pop(testcase_names.index(testcase_name))
    msg = 'Not all the expected testcases were processed'
    assert len(testcase_names) == 0, msg


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_bogus_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'bogus.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    mock_requests.post.assert_not_called()


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_pipeline_failure_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'pipeline_failure_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'tigervnc-1.8.0-5.el9000+5',
            'type': 'brew-build_scratch',

            'component': 'tigervnc',
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
        'outcome': 'FAILED',
        'ref_url': 'https://domain.redhat.com/job/downstream-rhel9000-build-pipeline/34/',
        'testcase': {
            'name': 'contra.pipeline.functional',
            'ref_url': 'https://domain.redhat.com/job/downstream-rhel9000-build-pipeline/34/',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_platformci_success_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'platformci_success_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
            'ref_url': 'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com/'
                       'job/ci-openstack/8465/',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_osci_success_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'osci_success_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
            'ref_url': (
                'https://some-jenkins.osci.redhat.com/'
                'job/pipeline/21/'),
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_fedora_ci_no_version(mock_requests):
    """ Make sure message is not processed if version is missing. """
    fake_msg_path = path.join(json_dir, 'fedora-ci-message-no-version.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    mock_requests.post.assert_not_called()


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_compose_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'compose_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the URLs called
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    url = 'https://rtt-jenkins/job/compose-RHEL-X.0-rel-eng-tier2-acceptance/1/'
    expected_data = {
        'testcase': {
            'name': 'rtt.tier2.functional',
            'ref_url': url,
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
        mock_requests.post.call_args_list[0][1]['data'])
    assert expected_data == actual_data, actual_data


@mock.patch('resultsdbupdater.utils.requests')
def test_queued_outcome_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'platformci_queued_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
            'ref_url': 'https://some-jenkins.redhat.com/job/ci-brew-dispatcher/125157/'
        }
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_queued_running_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'platformci_running_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
            'ref_url': 'https://some-jenkins.redhat.com/job/ci-covscan/109087/'
        }
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_pelc_component_version_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'pelc_component_version.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'

    # Verify the URLs called
    url = 'https://rcm-tools-jenkins/3/'
    expected_data = {
        'testcase': {
            'name': 'pelc.scan.validation',
            'ref_url': url
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
        mock_requests.post.call_args_list[0][1]['data'])
    assert expected_data == actual_data, actual_data


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_redhat_module_success_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'redhat_module_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
            'ref_url': (
                'https://baseos-jenkins.rhev-ci-vms.eng.rdu2.redhat.com/job/'
                'ci-openstack-mbs/45/'),
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_container_image_msg(mock_requests):
    fake_msg_path = path.join(json_dir, 'container_image_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {
        "note": "",
        "ref_url": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/job/waiverdb-test"
                   "/job/waiverdb-test-stage-waiverdb-dev-integration-test/104/",
        "testcase": {
            "ref_url": "https://jenkins-waiverdb-test.cloud.paas.upshift.redhat.com/job/"
                       "waiverdb-test/job/waiverdb-test-stage-waiverdb-dev-integration-test/104/",
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
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
@pytest.mark.parametrize('consume_fn', (
    resultsdbupdater.utils.handle_ci_umb,
    resultsdbupdater.utils.handle_ci_metrics,
    resultsdbupdater.utils.handle_resultsdb_format,
))
def test_publisher_id(mock_requests, consume_fn):
    mock_requests.get.return_value.json.return_value = {'data': []}

    fake_msg_path = path.join(json_dir, 'jmsx_user_id.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consume_fn(fake_msg)
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'

    actual_data = json.loads(
        mock_requests.post.call_args_list[0][1]['data'])
    assert 'msg-example-ci' == actual_data['data'].get('publisher_id'), actual_data


def test_topic_namespace_match():
    fake_msg_path = path.join(json_dir, 'redhat_module_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    fake_msg['topic'] = '/topic/VirtualTopic.eng.ci.baseos-ci.redhat-module.test.complete'

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_called_once()


def test_topic_namespace_mismatch(caplog):
    fake_msg_path = path.join(json_dir, 'redhat_module_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    fake_msg['topic'] = '/topic/VirtualTopic.eng.ci.bad-ci.redhat-module.test.complete'

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_not_called()
        assert any(
            'namespace "baseos-ci" does not match message topic' in rec.message
            for rec in caplog.records)


def test_topic_namespace_missing(caplog):
    fake_msg_path = path.join(json_dir, 'redhat_module_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    with mock.patch('resultsdbupdater.utils.create_result') as mock_create_result:
        consumer.consume(fake_msg)
        mock_create_result.assert_called_once()
        assert any(
            'uses old scheme not containing namespace' in rec.message
            for rec in caplog.records)


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_post_failed(mock_requests):
    mock_requests.post.return_value.raise_for_status.side_effect = \
        requests.exceptions.HTTPError()
    fake_msg_path = path.join(json_dir, 'message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    with pytest.raises(requests.exceptions.HTTPError):
        consumer.consume(fake_msg)


@mock.patch('resultsdbupdater.utils.requests')
def test_full_consume_post_timeout(mock_requests):
    mock_requests.post.side_effect = requests.exceptions.Timeout()
    fake_msg_path = path.join(json_dir, 'message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    with pytest.raises(requests.exceptions.Timeout):
        consumer.consume(fake_msg)


def test_consume_no_exception_on_bad_message(caplog):
    consumer.consume({})
    assert 'Failed to process message' in caplog.text


@mock.patch('resultsdbupdater.utils.requests')
def test_fedora_ci_message_brew_build_test_complete_version_2(mock_requests):
    fake_msg_path = path.join(json_dir, 'fedora-ci-message-brew-build.test.complete-2.0.0.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    consumer.consume(fake_msg)

    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
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
            'ref_url': 'https://jenkins/job/pipeline/170/',
        },
        'note': ''
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.requests')
def test_validate_throws_only_runtime_warning(mock_requests, caplog):
    with pytest.raises(RuntimeWarning):
        consumer.validate({'body': None})
    assert 'Failed to validate message: {' in caplog.text
