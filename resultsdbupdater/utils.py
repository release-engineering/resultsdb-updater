import requests
import fedmsg
import logging
import json
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus


CONFIG = fedmsg.config.load_config()
RESULTSDB_API_URL = CONFIG.get('resultsdb-updater.resultsdb_api_url')
TRUSTED_CA = CONFIG.get('resultsdb-updater.resultsdb_api_ca')

LOGGER = logging.getLogger('CIConsumer')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    format=log_format, level=CONFIG.get('resultsdb-updater.log_level'))


def create_job(job_name, url, status):
    headers = {'content-type': 'application/json'}
    job_post_url = '{0}/{1}'.format(RESULTSDB_API_URL, 'jobs')
    post_req = requests.post(
        job_post_url,
        data=json.dumps({'name': job_name, 'ref_url': url, 'status': status}),
        headers=headers,
        verify=TRUSTED_CA)
    if post_req.status_code == 201:
        return post_req.json()
    else:
        try:
            message = post_req.json().get('message')
        except ValueError:
            message = post_req.text
        LOGGER.error('The job "{0}" failed with the following: {1}'
                     .format(job_name, message))
        return {}


def create_result(testcase_name, job_id, outcome, result_data):
    headers = {'content-type': 'application/json'}
    result_post_url = '{0}/{1}'.format(RESULTSDB_API_URL, 'results')
    post_req = requests.post(
        result_post_url,
        data=json.dumps({
            'testcase_name': testcase_name,
            'job_id': job_id,
            'outcome': outcome,
            'result_data': result_data}),
        headers=headers,
        verify=TRUSTED_CA)
    if post_req.status_code == 201:
        return True
    else:
        try:
            message = post_req.json().get('message')
        except ValueError:
            message = post_req.text
        LOGGER.error(
            'The result for job id "{0}" failed with the following: {1}'
            .format(job_id, message))
        return False


def set_job_status(job_id, status):
    headers = {'content-type': 'application/json'}
    job_put_url = '{0}/{1}/{2}'.format(RESULTSDB_API_URL, 'jobs', job_id)
    put_req = requests.put(
        job_put_url,
        data=json.dumps({'status': status}),
        headers=headers,
        verify=TRUSTED_CA)

    if put_req.status_code == 200:
        return True
    else:
        LOGGER.error((
            'The job with job id "{0}" failed while setting the status with '
            'the following: {1}').format(job_id, json.dumps(put_req.json())))
        return False


def post_to_resultsdb(msg):
    msg_id = msg['headers']['message-id']
    if msg['body']['msg'].get('team'):
        testcase_name = '{0}\{1}'.format(
            msg['body']['msg']['team'], msg['body']['msg']['job_names'])
    else:
        LOGGER.warn((
            'The message "{0}" did not contain a team. Using '
            '"unassinged\job_names" as the name for the Test Case')
                .format(msg_id))
        testcase_name = 'unassigned\{0}'.format(msg['body']['msg']['job_names'])

    job_name = msg['body']['msg']['job_names']
    job_url = msg['body']['msg']['job_link_back']
    job_tests = msg['body']['msg'].get('tests')

    if not job_tests:
        LOGGER.warn((
            'The message "{0}" did not contain any tests. Marking the job as '
            '"CRASHED"').format(msg_id))
        job_status = 'CRASHED'
    else:
        job_status = 'RUNNING'

    new_job = create_job(job_name, job_url, job_status)

    if not new_job:
        LOGGER.error(
            'The new job for message "{0}" couldn\'t be created'.format(msg_id))
        return

    job_id = new_job['id']
    # Only create results if tests were in the message
    if job_tests:
        for test in job_tests:
            if 'failed' in test and int(test['failed']) == 0:
                outcome = 'PASSED'
            else:
                outcome = 'FAILED'

            if not create_result(testcase_name, job_id, outcome,
                                 result_data=test):
                LOGGER.error(
                    'The new result for message "{0}" couldn\'t be created'
                    .format(msg_id))
                return

    # Only mark the job as completed if it is in the RUNNING state
    if job_status == 'RUNNING' and not set_job_status(job_id, 'COMPLETED'):
        LOGGER.error(
            'The job status for message "{0}" couldn\'t be set to "COMPLETED"'
            .format(msg_id))
        return
