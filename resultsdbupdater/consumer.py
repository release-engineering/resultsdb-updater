import fedmsg.consumers

from utils import (
    LOGGER, ci_metrics_post_to_resultsdb, resultsdb_post_to_resultsdb,
    tps_post_to_resultsdb)


class CIConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = '/topic/CI'
    config_key = 'ciconsumer'

    def __init__(self, *args, **kw):
        super(CIConsumer, self).__init__(*args, **kw)

    def debug_log_msg(self, msg):
        LOGGER.debug('Processing message "{0}"'.format(
            msg['headers']['message-id']))
        LOGGER.debug(str(msg))

    def consume(self, msg):
        if 'headers' in msg:
            if 'CI_TYPE' in msg['headers']:
                if msg['headers']['CI_TYPE'] == 'ci-metricsdata':
                    self.debug_log_msg(msg)
                    return ci_metrics_post_to_resultsdb(msg)
                elif msg['headers']['CI_TYPE'] == 'resultsdb':
                    self.debug_log_msg(msg)
                    return resultsdb_post_to_resultsdb(msg)
            elif 'ci_type' in msg['headers']:
                if msg['headers']['ci_type'] == 'ci-tps':
                    self.debug_log_msg(msg)
                    return tps_post_to_resultsdb(msg)
