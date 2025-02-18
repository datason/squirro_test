from elasticsearch import Elasticsearch
from functools import lru_cache
from .config import settings
import logging

logger = logging.getLogger(__name__)

@lru_cache()
def get_es_client() -> Elasticsearch:
    es_host = settings.ELASTICSEARCH_HOST
    es_port = settings.ELASTICSEARCH_PORT
    
    logger.info(f"Creating Elasticsearch client with host={es_host}, port={es_port}")
    
    client = Elasticsearch([
        {
            'scheme': 'http',
            'host': es_host,
            'port': es_port,
            'timeout': 30,  # Add timeout
            'retry_on_timeout': True,  # Add retry on timeout
            'max_retries': 3  # Add max retries
        }
    ])
    
    # Verify connection
    try:
        if client.ping():
            logger.info("Successfully connected to Elasticsearch")
        else:
            logger.error("Could not connect to Elasticsearch")
    except Exception as e:
        logger.error(f"Error connecting to Elasticsearch: {str(e)}")
        raise
    
    return client