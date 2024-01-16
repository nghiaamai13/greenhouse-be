import pathlib
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
from .config import settings

import json

BASE_DIR = pathlib.Path(__file__).parent
CONNECT_BUNDLE = BASE_DIR / "unencrypted" / "astradb_connect.zip"


def get_cassandra_session():
    cloud_config= {
        'secure_connect_bundle': CONNECT_BUNDLE
    }

    CLIENT_ID = settings.astradb_client_id
    CLIENT_SECRET = settings.astradb_client_secret

    auth_provider = PlainTextAuthProvider(CLIENT_ID, CLIENT_SECRET)
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    session = cluster.connect()
    connection.register_connection(str(session), session=session)
    connection.set_default_connection(str(session))

    return session
