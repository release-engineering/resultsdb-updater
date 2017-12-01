import logging

config = {
    'ciconsumer': True,
    'zmq_enabled': False,
    'endpoints': {},
    'validate_signatures': False,
    'stomp_heartbeat': 1000,
    # Modify the values below
    'stomp_uri': 'server:61613',
    # User auth
    # 'stomp_user': 'user',
    # 'stomp_pass': 'password',
    # Cert auth
    'stomp_ssl_crt': '/path/to/cert',
    'stomp_ssl_key': '/path/to/key',
    'resultsdb-updater.log_level': logging.INFO,
    'resultsdb-updater.resultsdb_api_url': 'https://resultsdb.domain.local/api/v2.0',
    'resultsdb-updater.resultsdb_api_ca': None,
    'resultsdb-updater.topics': []
}
