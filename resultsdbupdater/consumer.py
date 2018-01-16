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

    def debug_log_msg(self, msg):
        LOGGER.debug('Processing message "{0}"'.format(
            msg['headers']['message-id']))
        LOGGER.debug(str(msg))

    def consume(self, msg):
        resultsdb_style_topics = [
            '/topic/VirtualTopic.eng.platformci.covscan.result',
            '/topic/VirtualTopic.eng.platformci.rpmdiff.analysis.result',
            '/topic/VirtualTopic.eng.platformci.rpmdiff.comparison.result'
        ]
        if msg['topic'] == '/topic/VirtualTopic.eng.platformci.tier1.result':
            self.debug_log_msg(msg)
            return ci_metrics_post_to_resultsdb(msg)
        elif msg['topic'] == '/topic/VirtualTopic.eng.cips':
            self.debug_log_msg(msg)
            return cips_post_to_resultsdb(msg)
        elif msg['topic'] in resultsdb_style_topics:
            self.debug_log_msg(msg)
            return resultsdb_post_to_resultsdb(msg)
        elif msg['topic'] == '/topic/VirtualTopic.qe.ci.jenkins':
            # Some of the messages here can be empty strings, so only process
            # them if they are dicts to avoid tracebacks
            if isinstance(msg['body']['msg'], dict):
                result_keys = msg['body']['msg'].get('results', {}).keys()
                # From our understanding, we are only interested in the AMI
                # test results in this topic
                if result_keys and result_keys[0].startswith('dva.ami'):
                    self.debug_log_msg(msg)
                    return resultsdb_post_to_resultsdb(msg)
        else:
            LOGGER.warn("Received unhandled message topic %r" % msg['topic'])
