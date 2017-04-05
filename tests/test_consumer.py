import unittest
from resultsdbupdater import consumer as ciconsumer
from resultsdbupdater import utils
from os import path
import json
import mock
import vcr

CASSETTES_DIR = path.join(path.abspath(path.dirname(__file__)), 'cassettes')


class FakeHub(object):
    config = {}


class TestConsumer(unittest.TestCase):
    def setUp(self):
        self.cassettes_dir = path.join(path.abspath(path.dirname(__file__)),
                                       'cassettes')
        self.json_dir = path.join(path.abspath(path.dirname(__file__)),
                                  'fake_messages')
        self.consumer = ciconsumer.CIConsumer(FakeHub())

    def tearDown(self):
        pass

    def test_basic_consume(self):
        fake_msg_path = path.join(self.json_dir, 'message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)
        with mock.patch('resultsdbupdater.consumer.ci_metrics_post_to_resultsdb') as ci_metrics_post_to_resultsdb:
            self.consumer.consume(fake_msg)
            ci_metrics_post_to_resultsdb.assert_called_once_with(fake_msg)

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_success.yaml'))
    def test_full_consume_msg(self):
        fake_msg_path = path.join(self.json_dir, 'message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), True)

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_overall_rpmdiff_success.yaml'))
    def test_full_consume_overall_rpmdiff_msg(self):
        fake_msg_path = path.join(self.json_dir, 'rpmdiff_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), True)

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_rpmdiff_success.yaml'))
    def test_full_consume_rpmdiff_msg(self):
        fake_msg_path = path.join(self.json_dir, 'rpmdiff_message_two.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), True)

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_covscan_success.yaml'))
    def test_full_consume_covscan_msg(self):
        fake_msg_path = path.join(self.json_dir, 'covscan_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), True)

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_bulk_results_success.yaml'))
    def test_full_consume_bulk_results_msg(self):
        fake_msg_path = path.join(self.json_dir, 'bulk_results_message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), True)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'create_result_success.yaml'))
    def test_create_result(self):
        data = {
            'executor': 'beaker',
            'arch': 'aarch64',
            'executed': '20',
            'failed': '1',
            'job_names': "fake-jenkins-job"
        }
        fake_ref_url = 'http://domain.local/job/package/136/console'
        self.assertEqual(
            utils.create_result(
                {'name': 'testcase'}, 'PASSED', fake_ref_url, data),
            True
        )
