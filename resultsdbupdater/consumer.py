import fedmsg.consumers

from utils import LOGGER, post_to_resultsdb


class CIConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = '/topic/CI'
    config_key = 'ciconsumer'

    def __init__(self, *args, **kw):
        super(CIConsumer, self).__init__(*args, **kw)

    def consume(self, msg):
        if 'headers' in msg and 'CI_TYPE' in msg['headers'] and \
                msg['headers']['CI_TYPE'] == 'ci-metricsdata':
            LOGGER.debug('Processing message "{0}"'.format(
                msg['headers']['message-id']))
            post_to_resultsdb(msg)
