from pydantic import BaseModel
from typing import List, Optional

class Document(BaseModel):
    text: str

class DocumentResponse(BaseModel):
    document_id: str
    text: str

class SearchResult(BaseModel):
    document_id: str
    text: str
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int

class SearchQuery(BaseModel):
    query: str
    max_results: Optional[int] = 10