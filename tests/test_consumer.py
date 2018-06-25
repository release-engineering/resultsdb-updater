from __future__ import unicode_literals
from os import path
import json

import pytest
import mock

from resultsdbupdater import consumer as ciconsumer


class FakeHub(object):
    config = {}


json_dir = path.join(path.abspath(path.dirname(__file__)), 'fake_messages')
consumer = ciconsumer.CIConsumer(FakeHub())
uuid_patcher = mock.patch(
    'resultsdbupdater.utils.uuid.uuid4',
    return_value='1bb0a6a5-3287-4321-9dc5-72258a302a37')
uuid_patcher.start()


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_msg(mock_get_session):
    mock_rv = mock.Mock()
    mock_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
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


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_overall_rpmdiff_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_get_rv = mock.Mock()
    mock_get_rv.status_code = 200
    mock_get_rv.json.return_value = {
        'data': [{
            'description': 'https://domain.local/run/12345',
            'uuid': '529da400-fc74-4b28-af81-52f56816a2cb'
        }]
    }
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_requests.get.return_value = mock_get_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'rpmdiff_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Assert it checked to see if an existing group exists to add the new
    # result to
    mock_requests.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'https://domain.local/run/12345'),
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


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_rpmdiff_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_get_rv = mock.Mock()
    mock_get_rv.status_code = 200
    mock_get_rv.json.return_value = {'data': []}
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_requests.get.return_value = mock_get_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'rpmdiff_message_two.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Assert it checked to see if an existing group exists to add the new
    # result to, but this time nothing was returned
    mock_requests.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'https://domain.local/run/12345'),
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


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_cips_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'cips_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {}

    all_expected_data = {
        'data': {
            'item': 'setup-2.8.71-7.el7_4',
            'type': 'brew-build',

            'component': 'setup',
            'brew_task_id': 15477983,
            'category': 'sanity',
            'scratch': True,
            'issuer': 'jenkins/domain.redhat.com',
            'rebuild': (
                'https://domain.redhat.com/job/ci-package-sanity-development'
                '/label=ose-slave-tps,provision_arch=x86_64/1835//'
                'rebuild/parametrized'),
            'log': (
                'https://domain.redhat.com/job/ci-package-sanity-development'
                '/label=ose-slave-tps,provision_arch=x86_64/1835//console'),
            'system_os': 'rhel-7.4-server-x86_64-updated',
            'system_provider': 'openstack',
            'ci_name': 'RPM Factory',
            'ci_url': 'https://domain.redhat.com',
            'ci_environment': 'production',
            'ci_team': 'rpm-factory',
            'ci_irc': '#rpm-factory',
            'ci_email': 'nobody@redhat.com'
        },
        'groups': [
            {
                'url': (
                    'https://domain.redhat.com/job/ci-package-sanity-development'
                    '/label=ose-slave-tps,provision_arch=x86_64/1835/'),
                'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
            },
        ],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': (
            'https://domain.redhat.com/job/ci-package-sanity-development'
            '/label=ose-slave-tps,provision_arch=x86_64/1835/'),
        'testcase': {
            'name': 'rpm-factory.unknown.sanity',
            'ref_url': 'https://domain.redhat.com',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_covscan_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_get_rv = mock.Mock()
    mock_get_rv.status_code = 200
    mock_get_rv.json.return_value = {'data': []}
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_requests.get.return_value = mock_get_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'covscan_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Assert it checked to see if an existing group exists to add the new
    # result to, but this time nothing was returned
    mock_requests.get.assert_called_once_with(
        ('https://resultsdb.domain.local/api/v2.0/groups?description='
         'http://domain.local/covscanhub/task/64208/log/added.html'),
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


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_bulk_results_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'bulk_results_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
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


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_bogus_msg(mock_get_session):
    fake_msg_path = path.join(json_dir, 'bogus.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is False
    mock_get_session.assert_not_called()


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_pipeline_failure_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'pipeline_failure_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'tigervnc-1.8.0-5.el9000+5',
            'type': 'brew-build',

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
            'ci_environment': None,
            'ci_team': 'contra',
            'ci_irc': '#contra',
            'ci_email': 'continuous-infra@redhat.com',
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
            'ref_url': 'https://domain.redhat.com/',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_platformci_success_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'platformci_success_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'setup-2.8.71-7.el7_4',
            'type': 'brew-build',
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
            'ci_environment': None,
            'ci_team': 'BaseOS QE',
            'ci_irc': '#baseosci',
            'ci_email': 'baseos-ci@redhat.com',
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
            'ref_url': 'https://baseos-jenkins.rhev-ci-vms.datacenter.redhat.com',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_osci_success_msg(mock_get_session):
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'osci_success_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'passwd-0.80-1.el8+5',
            'type': 'brew-build',
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
            'ci_environment': None,
            'ci_team': 'contra',
            'ci_irc': '#contra',
            'ci_email': 'continuous-infra@redhat.com',
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
            'ref_url': 'https://some-jenkins.osci.redhat.com/',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@pytest.mark.parametrize('namespace,expected', [
    (None, 'unknown.tier0.functional'),
    ('cheese', 'cheese.tier0.functional')
])
@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_osci_example_2(mock_get_session, namespace, expected):
    """ Testing a second OSCI message that didn't do what we expected. """
    mock_post_rv = mock.Mock()
    mock_post_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_post_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'osci_example_2.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)
    if namespace is None and fake_msg['body']['msg']['namespace']:
        del fake_msg['body']['msg']['namespace']
    else:
        fake_msg['body']['msg']['namespace'] = namespace

    assert consumer.consume(fake_msg) is True
    # Verify the post URL
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    all_expected_data = {
        'data': {
            'item': 'libfoo-2.7-9.el8+6',
            'type': 'brew-build',
            'component': 'libfoo',
            'brew_task_id': '16000903',
            'category': 'functional',
            'scratch': True,
            'issuer': None,
            'rebuild': (
                'https://some-jenkins.osci.redhat.com/'
                'job/pipeline/15/rebuild/parameterized'),
            'log': (
                'https://some-jenkins.osci.redhat.com/'
                'job/pipeline/15/console'),
            'system_os': 'TODO',
            'system_provider': 'TODO',
            'ci_name': 'Continuous Infra',
            'ci_url': 'https://some-jenkins.osci.redhat.com/',
            'ci_environment': None,
            'ci_team': 'contra',
            'ci_irc': '#contra',
            'ci_email': 'continuous-infra@redhat.com',
        },
        'groups': [{
            'url': (
                'https://some-jenkins.osci.redhat.com/blue/organizations/'
                'some-jenkins/pipeline/detail/pipeline/15/pipeline/'),
            'uuid': '1bb0a6a5-3287-4321-9dc5-72258a302a37'
        }],
        'note': '',
        'outcome': 'PASSED',
        'ref_url': (
            'https://some-jenkins.osci.redhat.com/blue/organizations/'
            'some-jenkins/pipeline/detail/pipeline/15/pipeline/'),
        'testcase': {
            'name': expected,
            'ref_url': 'https://some-jenkins.osci.redhat.com/',
        },
    }

    assert all_expected_data == \
        json.loads(mock_requests.post.call_args_list[0][1]['data'])


@mock.patch('resultsdbupdater.utils.retry_session')
def test_full_consume_compose_msg(mock_get_session):
    mock_rv = mock.Mock()
    mock_rv.status_code = 201
    mock_requests = mock.Mock()
    mock_requests.post.return_value = mock_rv
    mock_get_session.return_value = mock_requests
    fake_msg_path = path.join(json_dir, 'compose_message.json')
    with open(fake_msg_path) as fake_msg_file:
        fake_msg = json.load(fake_msg_file)

    assert consumer.consume(fake_msg) is True
    # Verify the URLs called
    assert mock_requests.post.call_args_list[0][0][0] == \
        'https://resultsdb.domain.local/api/v2.0/results'
    # Verify the post data
    assert mock_requests.post.call_count == 1
    url = "https://rtt-jenkins/job/compose-RHEL-X.0-rel-eng-tier2-acceptance/1/"
    expected_data = {
        "testcase": {
            "name": "unknown.tier2.functional",
            "ref_url": "https://rtt-jenkins"
        },
        "groups": [
            {
                "uuid": "1bb0a6a5-3287-4321-9dc5-72258a302a37",
                "url": url
            }
        ],
        "outcome": "passed",
        "ref_url": url,
        "note": "",
        "data": {
            "productmd.compose.id": "RHEL-X.0-20180101.1",
            "type": "compose",
            "category": "functional",
            "log": url + "console",
            "system_provider": "beaker",
            "system_architecture": "x86_64",
            "ci_name": "RTT CI",
            "ci_team": "RTT",
            "ci_url": "https://rtt-jenkins",
            "ci_irc": "#rtt",
            "ci_email": "release-test-team<AT>redhat.com"
        }
    }

    actual_data = json.loads(
        mock_requests.post.call_args_list[0][1]['data'])
    assert expected_data == actual_data, actual_data
