# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from elasticsearch import Elasticsearch
import os
from typing import Generator
import time
from app.main import app
from app.dependencies import get_es_client

# Use environment variable or default to 'elasticsearch' (Docker service name)
TEST_ES_HOST = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
TEST_ES_PORT = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
TEST_INDEX = "documents"

def wait_for_elasticsearch():
    """Wait for Elasticsearch to be ready"""
    max_retries = 30
    retry_interval = 2

    es = Elasticsearch([{
        'scheme': 'http',
        'host': TEST_ES_HOST,
        'port': TEST_ES_PORT
    }])

    for i in range(max_retries):
        try:
            if es.ping():
                return es
        except Exception as e:
            print(f"Waiting for Elasticsearch... attempt {i+1}/{max_retries}")
            time.sleep(retry_interval)
    
    raise Exception("Elasticsearch is not available")

@pytest.fixture(scope="session")
def es_client() -> Generator[Elasticsearch, None, None]:
    """
    Create a test Elasticsearch client and clean up test indices after tests.
    """
    client = wait_for_elasticsearch()
    
    # Delete test index if it exists
    if client.indices.exists(index=TEST_INDEX):
        client.indices.delete(index=TEST_INDEX)
    
    # Create test index
    client.indices.create(
        index=TEST_INDEX,
        body={
            "mappings": {
                "properties": {
                    "text": {"type": "text"}
                }
            }
        }
    )
    
    yield client
    
    # Cleanup after tests
    if client.indices.exists(index=TEST_INDEX):
        client.indices.delete(index=TEST_INDEX)

@pytest.fixture
def test_client(es_client: Elasticsearch) -> TestClient:
    """
    Create a test client with modified dependencies.
    """
    def get_test_es_client():
        return es_client
        
    # Override the get_es_client dependency
    app.dependency_overrides[get_es_client] = get_test_es_client
    
    # Make sure we're using the test index
    from app.main import startup_event
    async def test_startup():
        client = get_test_es_client()
        if not client.indices.exists(index=TEST_INDEX):
            client.indices.create(
                index=TEST_INDEX,
                body={
                    "mappings": {
                        "properties": {
                            "_id": {"type": "keyword"},
                            "text": {"type": "text"}
                        }
                    }
                }
            )
    
    app.dependency_overrides["startup_event"] = test_startup
    return TestClient(app)

@pytest.fixture
def sample_documents() -> list:
    """
    Provide sample documents for testing.
    """
    return [
        {
            "text": "Python is excellent for data science and machine learning projects."
        },
        {
            "text": "JavaScript is the primary language for web development."
        },
        {
            "text": "Python web frameworks like Django and Flask make backend development easier."
        }
    ]

@pytest.fixture
def populated_es(es_client: Elasticsearch, sample_documents: list) -> Generator[Elasticsearch, None, None]:
    """
    Populate Elasticsearch with sample documents for testing.
    """
    # Clear any existing documents
    if es_client.indices.exists(index=TEST_INDEX):
        es_client.indices.delete(index=TEST_INDEX)
        
    es_client.indices.create(
        index=TEST_INDEX,
        body={
            "mappings": {
                "properties": {
                    "text": {"type": "text"}
                }
            }
        }
    )
    
    # Add test documents
    for doc in sample_documents:
        es_client.index(index=TEST_INDEX, body=doc, refresh=True)
    
    yield es_client