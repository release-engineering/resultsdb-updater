import fedmsg.consumers
import fedmsg.config

from utils import (
    LOGGER, ci_metrics_post_to_resultsdb, resultsdb_post_to_resultsdb,
    cips_post_to_resultsdb)

CONFIG = fedmsg.config.load_config()
TOPICS = CONFIG.get('resultsdb-updater.topics', [])


class CIConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = TOPICS
    config_key = 'ciconsumer'

    def __init__(self, *args, **kw):
        super(CIConsumer, self).__init__(*args, **kw)

    def log_msg(self, msg):
        LOGGER.info('Processing message: "{0}"'.format(
            msg['headers']['message-id']))
        LOGGER.debug(str(msg))

    def consume(self, msg):
        if msg['topic'] == '/topic/VirtualTopic.eng.platformci.tier1.result':
            self.log_msg(msg)
            return ci_metrics_post_to_resultsdb(msg)
        elif msg['topic'] == '/topic/VirtualTopic.eng.cips.complete':
            self.log_msg(msg)
            return cips_post_to_resultsdb(msg)
        else:
            # Some of the messages here can be empty strings, so only process
            # them if they are dicts to avoid tracebacks
            if isinstance(msg['body']['msg'], dict):
                single_result_keys = set([
                    'data', 'outcome', 'ref_url', 'testcase'])
                bulk_results_keys = set(['results', 'ref_url'])
                actual_keys = set(msg['body']['msg'].keys())
                if actual_keys.issuperset(single_result_keys) or \
                        actual_keys.issuperset(bulk_results_keys):
                    self.log_msg(msg)
                    return resultsdb_post_to_resultsdb(msg)
            if msg['topic'] != '/topic/VirtualTopic.qe.ci.jenkins':
                # Mute unhandled message warnings when the message came from
                # VirtualTopic.qe.ci.jenkins since there will be many
                LOGGER.warn("Received unhandled message %r" % msg)
            return False
