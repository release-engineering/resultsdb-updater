import fedmsg.consumers
import fedmsg.config

from . import config, exceptions, utils

from .message import create_message

CONFIG = fedmsg.config.load_config()
TOPICS = CONFIG.get('resultsdb-updater.topics', [])


class CIConsumer(fedmsg.consumers.FedmsgConsumer):
    topic = TOPICS
    config_key = 'ciconsumer'

    def __init__(self, *args, **kw):
        super(CIConsumer, self).__init__(*args, **kw)

    def validate(self, message):
        """
        Wraps fedmsg.consumers.FedmsgConsumer.validate() to avoid propagating
        unexpected exceptions which would cause fedmsg-hub to get stuck (stops
        processing messages but doesn't quit).
        """
        try:
            return super(CIConsumer, self).validate(message)
        except RuntimeWarning:
            raise
        except Exception:
            config.LOGGER.exception('Failed to validate message: %s', message)
            raise RuntimeWarning('Unexpected exception during message validation')

    def _consume_helper(self, msg):
        # Some of the messages here can be empty strings, so only process
        # them if they are dicts to avoid tracebacks
        if not isinstance(msg.body, dict):
            msg.log.debug("Dropping non-dict message.")
            return

        # First, look by topic to see if the message is one of the old formats
        # we want to handle for legacy reasons.
        if msg.topic == '/topic/VirtualTopic.eng.platformci.tier1.result':
            utils.handle_ci_metrics(msg)
            return

        # The following stanzas consider if the actual message body
        # matches one of a few patterns we support.  Start by
        # extracting the keys borne in the message.
        actual_keys = set(msg.body.keys())

        # Next, detect if the message bears the primary format we support.
        # The "FACTORY 2.0 CI UMB messages"
        # See: https://pagure.io/fedora-ci/messages
        ci_umb_keys = set(['run', 'artifact'])
        contact_umb_keys = set(['ci', 'contact'])
        if actual_keys.issuperset(ci_umb_keys) and not actual_keys.isdisjoint(contact_umb_keys):
            utils.handle_ci_umb(msg)
            return

        # Next, detect if the message bears the secondary format we support:
        # The "resultsdb" format.
        # https://mojo.redhat.com/docs/DOC-1131637
        single_keys = set(['data', 'outcome', 'ref_url', 'testcase'])
        bulk_keys = set(['results', 'ref_url'])
        if actual_keys.issuperset(single_keys) or actual_keys.issuperset(bulk_keys):
            utils.handle_resultsdb_format(msg)
            return

        if msg.topic != '/topic/VirtualTopic.qe.ci.jenkins':
            # Mute unhandled message warnings when the message came from
            # VirtualTopic.qe.ci.jenkins since there will be many
            msg.log.warning('Received unhandled message %r', msg)

    def consume(self, msg_data):
        try:
            msg = create_message(msg_data)
            msg.log.info('Message received')
            msg.log.debug('%s', msg)

            self._consume_helper(msg)
        except exceptions.CreateResultError as e:
            msg.log.error('Failed to process message: %s', e)
        except exceptions.InvalidMessageError as e:
            msg.log.warning('Invalid message rejected: %s', e)
        except Exception:
            # Disallow propagating any other exception, otherwise NACK is sent
            # and the message is scheduled to be received later. But it seems
            # these messages can be only received by other consumer (or after
            # restart) otherwise the messages can block the queue completely.
            msg.log.exception('Unexpected exception')
