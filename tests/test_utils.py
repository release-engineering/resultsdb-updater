import pytest
from resultsdbupdater import utils


@pytest.mark.parametrize(
    ('user', 'password', 'url', 'result', 'error'),
    [
        # Basic auth correctly configured
        ('user', 'password', 'https://example.com', ('user', 'password'), None),
        # Basic auth not configured
        (None, None, 'http://example.com', None, None),
        # URL is not HTTPS
        ('foo', 'bar', 'http://example.com', None, RuntimeError),
        # User not configured
        (None, 'bar', 'https://example.com', None, RuntimeError),
        # Password not configured
        ('red', None, 'https://example.com', None, RuntimeError),
    ])
def test_get_http_auth(user, password, url, result, error):
    if error:
        with pytest.raises(error):
            auth = utils.get_http_auth(user, password, url)
    else:
        auth = utils.get_http_auth(user, password, url)
        assert auth == result
