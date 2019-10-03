import fedmsg.consumers
import fedmsg.config

from . import utils

CONFIG = fedmsg.config.load_config()
TOPICS = CONFIG.get('resultsdb-updater.topics', [])


class CIConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = TOPICS
    config_key = 'ciconsumer'

    def __init__(self, *args, **kw):
        super(CIConsumer, self).__init__(*args, **kw)

    def log_msg(self, msg):
        utils.LOGGER.info('Processing message: "{0}"'.format(
            msg['headers']['message-id']))
        utils.LOGGER.debug(str(msg))

    def consume(self, msg):
        # Some of the messages here can be empty strings, so only process
        # them if they are dicts to avoid tracebacks
        if not isinstance(msg['body']['msg'], dict):
            utils.LOGGER.debug("Dropping non-dict message.")
            return

        # First, look by topic to see if the message is one of the old formats
        # we want to handle for legacy reasons.
        if msg['topic'] == '/topic/VirtualTopic.eng.platformci.tier1.result':
            self.log_msg(msg)
            utils.handle_ci_metrics(msg)
            return

        # The following stanzas consider if the actual message body
        # matches one of a few patterns we support.  Start by
        # extracting the keys borne in the message.
        actual_keys = set(msg['body']['msg'].keys())

        # Next, detect if the message bears the primary format we support.
        # The "FACTORY 2.0 CI UMB messages"
        # https://docs.google.com/document/d/16L5odC-B4L6iwb9dp8Ry0Xk5Sc49h9KvTHrG86fdfQM/edit
        ci_umb_keys = set(['ci', 'run', 'artifact'])
        if actual_keys.issuperset(ci_umb_keys):
            self.log_msg(msg)
            utils.handle_ci_umb(msg)
            return

        # Next, detect if the message bears the secondary format we support:
        # The "resultsdb" format.
        # https://mojo.redhat.com/docs/DOC-1131637
        single_keys = set(['data', 'outcome', 'ref_url', 'testcase'])
        bulk_keys = set(['results', 'ref_url'])
        if actual_keys.issuperset(single_keys) or actual_keys.issuperset(bulk_keys):
            self.log_msg(msg)
            utils.handle_resultsdb_format(msg)
            return

        if msg['topic'] != '/topic/VirtualTopic.qe.ci.jenkins':
            # Mute unhandled message warnings when the message came from
            # VirtualTopic.qe.ci.jenkins since there will be many
            utils.LOGGER.warning('Received unhandled message %r' % msg)
