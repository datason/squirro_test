from fastapi import FastAPI
from .api.routes import router
from elasticsearch import Elasticsearch
from .dependencies import get_es_client


INDEX_NAME = 'documents'

app = FastAPI(title="Document Search Service")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    es_client = get_es_client()
    # Create index if it doesn't exist
    if not es_client.indices.exists(index="documents"):
        es_client.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "text": {"type": "text"}
                    }
                }
            }
        )

app.include_router(router, prefix="/api/v1")