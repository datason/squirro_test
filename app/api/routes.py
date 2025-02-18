from fastapi import APIRouter, Depends, HTTPException
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
    AuthenticationException,
    TransportError,
    NotFoundError
)
from openai.error import (
    APIError as OpenAIAPIError,
    AuthenticationError as OpenAIAuthError,
    RateLimitError,
    APIConnectionError
)
from typing import List
import sys
import openai
from ..config import settings
from ..dependencies import get_es_client
from .models import Document, DocumentResponse, SearchQuery, SearchResponse, SearchResult

router = APIRouter()
INDEX_NAME = "documents"

@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    document: Document,
    es_client: Elasticsearch = Depends(get_es_client)
):
    try:
        result = es_client.index(
            index=INDEX_NAME,  # Use the constant
            body={"text": document.text}
        )
        return DocumentResponse(
            document_id=result['_id'],
            text=document.text
        )
    except ESConnectionError as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Elasticsearch connection failed",
                "message": str(e),
                "type": "elasticsearch_connection_error"
            }
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Elasticsearch authentication failed",
                "message": str(e),
                "type": "elasticsearch_authentication_error"
            }
        )
    except TransportError as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Elasticsearch transport error",
                "message": str(e),
                "error_code": e.status_code,
                "type": "elasticsearch_transport_error"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Unexpected error during document creation",
                "message": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    es_client: Elasticsearch = Depends(get_es_client)
):
    try:
        result = es_client.get(index=INDEX_NAME, id=document_id)
        return DocumentResponse(
            document_id=result["_id"],
            text=result["_source"]["text"]
        )
    except NotFoundError:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "Document not found",
                "document_id": document_id,
                "index": INDEX_NAME,
                "type": "document_not_found"
            }
        )
    except ESConnectionError as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Elasticsearch connection failed",
                "message": str(e),
                "type": "elasticsearch_connection_error"
            }
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Elasticsearch authentication failed",
                "message": str(e),
                "type": "elasticsearch_authentication_error"
            }
        )
    except TransportError as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Elasticsearch transport error",
                "message": str(e),
                "error_code": e.status_code,
                "type": "elasticsearch_transport_error"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Unexpected error retrieving document",
                "message": str(e),
                "type": type(e).__name__
            }
        )

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    query: SearchQuery,
    es_client: Elasticsearch = Depends(get_es_client)
):
    try:
        search_query = {
            "query": {
                "match": {
                    "text": query.query
                }
            }
        }
        
        results = es_client.search(
            index=INDEX_NAME,
            body=search_query,
            size=query.max_results or settings.MAX_SEARCH_RESULTS
        )
        
        search_results = [
            SearchResult(
                document_id=hit["_id"],
                text=hit["_source"]["text"],
                score=hit["_score"]
            )
            for hit in results["hits"]["hits"]
        ]
        
        return SearchResponse(
            results=search_results,
            total=results["hits"]["total"]["value"]
        )
    except ESConnectionError as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Elasticsearch connection failed during search",
                "message": str(e),
                "type": "elasticsearch_connection_error"
            }
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Elasticsearch authentication failed during search",
                "message": str(e),
                "type": "elasticsearch_authentication_error"
            }
        )
    except TransportError as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Elasticsearch transport error during search",
                "message": str(e),
                "error_code": e.status_code,
                "type": "elasticsearch_transport_error"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Unexpected error during search",
                "message": str(e),
                "type": type(e).__name__
            }
        )

@router.post("/search/llm")
async def search_with_llm(
    query: SearchQuery,
    es_client: Elasticsearch = Depends(get_es_client)
):
    # First, get relevant documents
    search_results = await search_documents(query, es_client)
    
    if not search_results.results:
        return {"answer": "No relevant documents found"}
    
    # Prepare context from top results
    context = "\n\n".join([
        f"Document {i+1}:\n{result.text}"
        for i, result in enumerate(search_results.results[:3])
    ])
    
    try:
        # Create prompt for OpenAI
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer the question based on the provided context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query.query}"}
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))