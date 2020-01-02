import semantic_version

from . import config
from . import exceptions

REQUIRED_FIELD = object()


def get_body(msg):
    return msg.get('body', {}).get('msg')


def get_version(msg):
    return get_body(msg).get('version', '0.1.0')


class Result(object):
    """
    Provides test result data from message.
    """

    def __init__(self, msg):
        """
        Args:
            msg (Message) - Parent message
        """
        self.msg = msg

    def get(self, *args, **kwargs):
        return self.msg.get(*args, **kwargs)

    @property
    def version(self):
        return get_version(self.msg)

    @property
    def testcase(self):
        return '.'.join((self.namespace, self.type, self.category))

    @property
    def category(self):
        return self.get('category')

    @property
    def namespace(self):
        return self.get('namespace')

    @property
    def type(self):
        return self.get('type')

    @property
    def xunit(self):
        return self.get('xunit', default=None)

    @property
    def result(self):
        return self.get('status', default=None)


class ResultV2(Result):
    def get(self, *args, **kwargs):
        return self.msg.get('test', *args, **kwargs)

    @property
    def xunit(self):
        return self.get('xunit', default=None)

    @property
    def result(self):
        # result is required for complete messages only
        if self.msg.topic.endswith('.complete'):
            return self.get('result')
        return None


class PrefixLogger(object):
    """
    Wrapper around a logger, adds custom prefix to messages.
    """

    def __init__(self, prefix, log):
        self.prefix = prefix
        self.log = log

    def info(self, msg, *args):
        self.log.info(self._prefixed(msg), *args)

    def warning(self, msg, *args):
        self.log.warning(self._prefixed(msg), *args)

    def error(self, msg, *args):
        self.log.error(self._prefixed(msg), *args)

    def exception(self, msg, *args):
        self.log.exception(self._prefixed(msg), *args)

    def debug(self, msg, *args):
        self.log.debug(self._prefixed(msg), *args)

    def _prefixed(self, msg):
        return '[{0}]: {1}'.format(self.prefix, msg)


class Message(object):
    """
    Provides message data.
    """

    def __init__(self, msg_data):
        """
        Args:
            msg (dict) - Message data
        """
        self.msg_data = msg_data
        self.log = PrefixLogger(self.msg_id, config.LOGGER)

    def __repr__(self):
        return repr(self.msg_data)

    @property
    def body(self):
        return get_body(self.msg_data)

    @property
    def msg_id(self):
        try:
            return self.header('message-id')
        except Exception:
            return 'ID:UNKNOWN'

    @property
    def topic(self):
        return self.msg_data.get('topic')

    @property
    def version(self):
        return get_version(self.msg_data)

    def header(self, name):
        return self.msg_data.get('headers', {}).get(name)

    def _get(self, *args, **kwargs):
        value = kwargs.get('value')
        default = kwargs.get('default')

        for arg in args:
            if not isinstance(value, dict):
                return default
            value = value.get(arg, default)

        return value

    def get(self, *args, **kwargs):
        default = kwargs.get('default', REQUIRED_FIELD)

        value = self._get(*args, value=self.body, default=default)

        if value is REQUIRED_FIELD:
            raise exceptions.MissingMessageField(*args)

        return value

    def contact(self, field, default=REQUIRED_FIELD):
        return self.get('ci', field, default=default)

    def system(self, field, default=REQUIRED_FIELD):
        system = self.get('system', default={})

        # Oddly, sometimes people pass us a sytem dict but other times a
        # list of one system dict.  Try to handle those two situation here.
        if isinstance(system, list):
            system = system[0] if system else {}

        value = self._get(field, value=system, default=default)

        if value is REQUIRED_FIELD:
            raise exceptions.MissingMessageField('system', field)

        return value

    @property
    def result(self):
        return Result(self)

    @property
    def contact_dict(self):
        return {
            'ci_name': self.contact('name'),
            'ci_team': self.contact('team'),
            'ci_url': self.contact('url', default='not available'),
            'ci_irc': self.contact('irc', default='not available'),
            'ci_email': self.contact('email'),
        }

    @property
    def recipients(self):
        return self.get('recipients', default=[])

    @property
    def error_reason(self):
        return self.get('reason')


class MessageV2(Message):
    @property
    def result(self):
        return ResultV2(self)

    @property
    def recipients(self):
        return self.get('notification', 'recipients', default=[])

    @property
    def error_reason(self):
        return self.get('error', 'reason')


class MessageV2_1(MessageV2):
    def contact(self, field, default=REQUIRED_FIELD):
        return self.get('contact', field, default=default)


def create_message(msg_data):
    try:
        version = get_version(msg_data)

        if semantic_version.match('<0.2.0', version):
            return Message(msg_data)

        if semantic_version.match('<0.2.1', version):
            return MessageV2(msg_data)

        return MessageV2_1(msg_data)
    except Exception:
        msg = Message(msg_data)
        msg.log.exception('Failed to parse message version')
        return msg
