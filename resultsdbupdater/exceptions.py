class InvalidMessageError(RuntimeError):
    pass


class MissingMessageField(InvalidMessageError):
    def __init__(self, *field):
        super(MissingMessageField, self).__init__()
        self.field = field

    def __str__(self):
        field_name = '.'.join(str(field) for field in self.field)
        return 'Missing field "{0}"'.format(field_name)


class MissingTopicError(InvalidMessageError):
    def __init__(self, **kwargs):
        super(MissingTopicError, self).__init__()
        self.kwargs = kwargs

    def __str__(self):
        return (
            'The message topic "{topic}" uses old scheme not containing '
            'namespace from test case name "{testcase_name}"'
        ).format(**self.kwargs)


class TopicMismatchError(InvalidMessageError):
    def __init__(self, **kwargs):
        super(TopicMismatchError, self).__init__()
        self.kwargs = kwargs

    def __str__(self):
        return (
            'Test case "{testcase_name}" namespace "{testcase_namespace}" does not match '
            'message topic "{topic}" namespace "{topic_namespace}"'
        ).format(**self.kwargs)


class PrivateTestCaseMismatchError(InvalidMessageError):
    def __init__(self, **kwargs):
        super(PrivateTestCaseMismatchError, self).__init__()
        self.kwargs = kwargs

    def __str__(self):
        return (
            'Test case "{testcase_name}" is private (matches "{testcase_glob}") but '
            'message JMSXUserID "{msg_publisher_id}" does not match "{publisher_id}"'
        ).format(**self.kwargs)


class CreateResultError(RuntimeError):
    def __init__(self, msg, payload):
        super(CreateResultError, self).__init__()
        self.msg = msg
        self.payload = payload

    def __str__(self):
        return 'Failed to create result: {0}; Payload: {1}'.format(self.msg, self.payload)
