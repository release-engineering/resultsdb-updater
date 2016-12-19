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

    @vcr.use_cassette(
        path.join(CASSETTES_DIR, 'consume_msg_success.yaml'))
    def test_full_consume_msg(self):
        fake_msg_path = path.join(self.json_dir, 'message.json')
        with open(fake_msg_path) as fake_msg_file:
            fake_msg = json.load(fake_msg_file)

        self.assertEqual(self.consumer.consume(fake_msg), None)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'create_job_success.yaml'))
    def test_create_job(self):
        response = {
            'end_time': None,
            'href': 'https://resultsdb.domain.local/api/v1.0/jobs/2',
            'id': 2,
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
            utils.create_job('some_job', url, 'RUNNING'), response)

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
                'some_testcase', 2, 'PASSED',
                'http://domain.local/job/package/136/console', result),
            True
        )

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'set_job_status_success.yaml'))
    def test_set_job_status(self):
        self.assertEqual(utils.set_job_status(2, 'COMPLETED'), True)

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'create_testcase_success.yaml'))
    def test_create_testcase(self):
        self.assertEqual(
            utils.create_testcase('team.the_best_testcase_of_my_life',
                                  'https://http.cat/404'),
            True
        )

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'get_testcase_success.yaml'))
    def test_get_testcase(self):
        results = {
            'url': 'https://http.cat/404',
            'href': 'https://resultsdb.domain.local/api/v1.0/testcases/team.the_best_testcase_of_my_life',
            'name': 'team.the_best_testcase_of_my_life'
        }
        self.assertEqual(
            utils.get_testcase('team.the_best_testcase_of_my_life'),
            results
        )

    @vcr.use_cassette(path.join(CASSETTES_DIR, 'put_testcase_success.yaml'))
    def test_set_testcase(self):
        self.assertEqual(
            utils.set_testcase('team.the_best_testcase_of_my_life',
                               'https://http.cat/401'),
            True
        )
