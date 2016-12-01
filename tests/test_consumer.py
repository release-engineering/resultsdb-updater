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
        with mock.patch('resultsdbupdater.consumer.post_to_resultsdb') as post_to_resultsdb:
            self.consumer.consume(fake_msg)
            post_to_resultsdb.assert_called_once_with(fake_msg)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'consume_msg_one_success.yaml'))
    def test_full_consume_msg_one(self):
        fake_msg_path = path.join(self.json_dir, 'message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), None)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'consume_msg_two_success.yaml'))
    def test_full_consume_msg_two(self):
        fake_msg_path = path.join(self.json_dir, 'message2.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), None)

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_three_success.yaml'))
    def test_full_consume_msg_three(self):
        fake_msg_path = path.join(self.json_dir, 'message3.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), None)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'create_job_success.yaml'))
    def test_create_job(self):
        response = {
            'end_time': None,
            'href': 'http://resultsdb.domain.local/api/v1.0/jobs/10',
            'id': 10,
            'name': 'some_job',
            'ref_url': 'http://someurl.domain.local/path/to/test',
            'results': [],
            'results_count': 0,
            'start_time': None,
            'status': 'RUNNING',
            'uuid': None
        }

        url = 'http://someurl.domain.local/path/to/test'
        self.assertEqual(
            utils.create_job('some_job', url, 'COMPLETED'), response)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'create_result_success.yaml'))
    def test_create_result(self):
        result = {
            'executor': 'beaker',
            'arch': 'aarch64',
            'executed': '20',
            'failed': '1'
        }

        self.assertEqual(
            utils.create_result(
                'some_testcase', 10, 'PASSED', result_data=result), True)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'set_job_status_success.yaml'))
    def test_set_job_status(self):
        self.assertEqual(utils.set_job_status(10, 'COMPLETED'), True)
