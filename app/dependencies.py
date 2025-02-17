from elasticsearch import Elasticsearch
from functools import lru_cache
from .config import settings

@lru_cache()
def get_es_client() -> Elasticsearch:
    return Elasticsearch([
        {
            'scheme': 'http',  # Add this line
            'host': settings.ELASTICSEARCH_HOST,
            'port': settings.ELASTICSEARCH_PORT,
        }
    ])