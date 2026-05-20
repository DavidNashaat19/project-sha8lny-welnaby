from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class JobDocument(BaseModel):
    doc_id: int
    platform: str
    title: str
    description_snippet: str
    skills: List[str]
    budget_extracted: Optional[float]
    budget_currency: Optional[str]
    budget_type: Optional[str]
    url: str
    relevance_score: Optional[float] = None
    matched_tokens: Optional[List[str]] = None
    tfidf_breakdown: Optional[Dict[str, float]] = None
    inferred_skills: List[str] = []
    has_explicit_skills: bool = True

class SearchResponse(BaseModel):
    total: int
    page: int
    results: List[JobDocument]
    insight: Optional[str] = None
    query_time_ms: int

class AnalyticsResponse(BaseModel):
    top_skills: List[Dict[str, Any]]
    platform_dist: Dict[str, int]
    budget_stats: Dict[str, float]
    budget_histogram: List[Dict[str, Any]]
    skills_by_budget: List[Dict[str, Any]]
    cooccurrence_matrix: Dict[str, Dict[str, int]]
    currency_dist: Dict[str, int]
    token_count_dist: List[Dict[str, Any]]

class MatchRequest(BaseModel):
    skills: List[str]
    budget_expectation: Optional[float] = None
    platform: Optional[str] = "all"

class MatchResponse(BaseModel):
    match_score: float
    top_jobs: List[JobDocument]
    matched_skills: List[str]
    gap_skills: List[str]
    suggested_skills: List[str]

class VSMRequest(BaseModel):
    query: str

class VSMDocumentResult(BaseModel):
    doc_id: int
    cosine_similarity: float
    document_vector: Dict[str, float]
    title: str

class VSMResponse(BaseModel):
    query_vector: Dict[str, float]
    top_documents: List[VSMDocumentResult]
