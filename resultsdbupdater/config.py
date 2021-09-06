import logging

import fedmsg

CONFIG = fedmsg.config.load_config()

RESULTSDB_API_URL = CONFIG.get('resultsdb-updater.resultsdb_api_url')
TRUSTED_CA = CONFIG.get('resultsdb-updater.resultsdb_api_ca')
TIMEOUT = CONFIG.get('resultsdb-updater.requests_timeout', 15)

LOGGER = logging.getLogger('CIConsumer')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    format=log_format, level=CONFIG.get('resultsdb-updater.log_level'))

USER_AGENT = 'resultsdb_updater'


def get_http_auth(user, password, url):
    """Return an auth tuple to be used with requests

    Args:
        user (string) - username used for Basic auth
        password (string) - password for Basic auth
        url (string) - URL for which the credentials above will be used

    Returns:
        Tuple of (user, password), if both defined, or None

    Raises:
        RuntimeError, if only one of (user, password) is defined
        RuntimeError, if url is not HTTPS
    """
    auth = None

    if not user and not password:
        pass
    elif user and password:
        auth = (user, password)
    else:
        raise RuntimeError(
            'User or password not configured for ResultDB Basic authentication!')

    # https://tools.ietf.org/html/rfc7617#section-4
    if auth and not url.startswith('https://'):
        raise RuntimeError(
            'Basic authentication should not be used without HTTPS!')

    return auth


RESULTSDB_AUTH = get_http_auth(
    CONFIG.get('resultsdb-updater.resultsdb_user'),
    CONFIG.get('resultsdb-updater.resultsdb_pass'),
    RESULTSDB_API_URL)

# Private test case (glob pattern) always require to match JMSXUserID in
# messages.
PRIVATE_TESTCASE_PUBLISHER_MAP = CONFIG.get(
    'resultsdb-updater.private_testcase_publisher_map', ())
