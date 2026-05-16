import os
#from opensearchpy import OpenSearch
#from functools import lru_cache
#from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load database configuration from environment variables
'''
load_dotenv()

OPENSEARCH_HOST = os.getenv('OPENSEARCH_HOST', 'localhost')
OPENSEARCH_PORT = int(os.getenv('OPENSEARCH_PORT', 9200))
OPENSEARCH_USER = os.getenv('OPENSEARCH_USER', '')
OPENSEARCH_PASS = os.getenv('OPENSEARCH_PASS', '')
OPENSEARCH_USE_SSL = os.getenv('OPENSEARCH_USE_SSL', 'False').lower() == 'true'


@lru_cache()
def get_opensearch_client() -> OpenSearch:
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASS),
        use_ssl=OPENSEARCH_USE_SSL,
        verify_certs=OPENSEARCH_USE_SSL,
        ssl_show_warn=False,
    )
    return client
'''


# connect to sqlite database
DATABASE_URL = "sqlite:///db/file_metadata.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()






