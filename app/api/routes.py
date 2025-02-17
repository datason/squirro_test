from fastapi import APIRouter, Depends, HTTPException
from elasticsearch import Elasticsearch
from typing import List
import openai
from ..config import settings
from ..dependencies import get_es_client
from .models import Document, DocumentResponse, SearchQuery, SearchResponse, SearchResult

router = APIRouter()

@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    document: Document,
    es_client: Elasticsearch = Depends(get_es_client)
):
    try:
        result = es_client.index(
            index="documents",
            body={"text": document.text}
        )
        # The ID is in result['_id']
        return DocumentResponse(
            document_id=result['_id'],  # This is where we get the document_id
            text=document.text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    es_client: Elasticsearch = Depends(get_es_client)
):
    try:
        result = es_client.get(index="documents", id=document_id)
        return DocumentResponse(
            document_id=result["_id"],
            text=result["_source"]["text"]
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Document not found")

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
            index="documents",
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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