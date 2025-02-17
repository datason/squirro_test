import pytest
import os
from fastapi.testclient import TestClient
from elasticsearch import Elasticsearch

def test_create_document(test_client: TestClient):
    """Test document creation endpoint"""
    response = test_client.post(
        "/api/v1/documents",
        json={"text": "Test document content"}
    )
    
    assert response.status_code == 200
    print(response.json())
    assert "document_id" in response.json()
    assert response.json()["text"] == "Test document content"

def test_get_document(test_client: TestClient, populated_es: Elasticsearch):
    """Test document retrieval endpoint"""
    # First create a document
    create_response = test_client.post(
        "/api/v1/documents",
        json={"text": "Test document for retrieval"}
    )
    
    document_id = create_response.json()["document_id"]
    
    # Then retrieve it
    response = test_client.get(f"/api/v1/documents/{document_id}")
    
    assert response.status_code == 200
    assert response.json()["document_id"] == document_id
    assert response.json()["text"] == "Test document for retrieval"

def test_get_nonexistent_document(test_client: TestClient):
    """Test retrieval of non-existent document"""
    response = test_client.get("/api/v1/documents/nonexistent_id")
    assert response.status_code == 404

def test_search_documents(test_client: TestClient, populated_es: Elasticsearch):
    """Test document search endpoint"""
    response = test_client.post(
        "/api/v1/search",
        json={
            "query": "Python data science",
            "max_results": 5
        }
    )
    
    assert response.status_code == 200
    assert "results" in response.json()
    assert "total" in response.json()
    assert len(response.json()["results"]) > 0
    
    # Check if results are relevant to the query
    found_relevant = False
    for result in response.json()["results"]:
        if "Python" in result["text"] and "data science" in result["text"]:
            found_relevant = True
            break
    
    assert found_relevant

def test_search_no_results(test_client: TestClient, populated_es: Elasticsearch):
    """Test search with no matching results"""
    response = test_client.post(
        "/api/v1/search",
        json={
            "query": "nonexistent content xyz123",
            "max_results": 5
        }
    )
    
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert len(response.json()["results"]) == 0

@pytest.mark.skipif(not bool(os.getenv("OPENAI_API_KEY")), 
                    reason="OpenAI API key not provided")
def test_llm_search(test_client: TestClient, populated_es: Elasticsearch):
    """Test LLM-powered search endpoint"""
    response = test_client.post(
        "/api/v1/search/llm",
        json={
            "query": "What can Python be used for?"
        }
    )
    
    assert response.status_code == 200
    assert "answer" in response.json()
    assert len(response.json()["answer"]) > 0

def test_search_with_invalid_query(test_client: TestClient):
    """Test search with invalid query format"""
    response = test_client.post(
        "/api/v1/search",
        json={
            "invalid_field": "test"
        }
    )
    
    assert response.status_code == 422  # Validation error

def test_create_invalid_document(test_client: TestClient):
    """Test document creation with invalid format"""
    response = test_client.post(
        "/api/v1/documents",
        json={
            "invalid_field": "test"
        }
    )
    
    assert response.status_code == 422  # Validation error

def test_search_with_large_max_results(test_client: TestClient, populated_es: Elasticsearch):
    """Test search with large max_results value"""
    response = test_client.post(
        "/api/v1/search",
        json={
            "query": "Python",
            "max_results": 1000  # Large number
        }
    )
    
    assert response.status_code == 200
    assert len(response.json()["results"]) <= 1000