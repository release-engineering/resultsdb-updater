import logging

config = {
    'ciconsumer': True,
    'zmq_enabled': False,
    'endpoints': {},
    'validate_signatures': False,
    'stomp_heartbeat': 1000,
    # Modify the values below
    'stomp_uri': 'server:61613',
    'stomp_user': 'user',
    'stomp_pass': 'password',
    'resultsdb-updater.log_level': logging.INFO,
    'resultsdb-updater.resultsdb_api_url': 'http://resultsdb.domain.local/api/v1.0',
    'resultsdb-updater.resultsdb_api_ca': None
}
