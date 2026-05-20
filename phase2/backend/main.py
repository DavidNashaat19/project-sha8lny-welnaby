import time
from fastapi import FastAPI, Query, Body, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import io
import PyPDF2
from .ner_extractor import ner_extractor


from .models import (
    SearchResponse, JobDocument, AnalyticsResponse, 
    MatchRequest, MatchResponse, VSMRequest, VSMResponse, VSMDocumentResult
)
from .data_loader import engine, load_all_data
from .analytics import get_analytics
from .match import match_freelancer
from .preprocess import tokenize_and_filter, clean_text_full
from .semantic_engine import semantic_engine
from .market_insight import market_insight_engine
import asyncio

app = FastAPI(title="Sha8lny Welnaby Phase 2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Loading data and building indexes...")
    load_all_data()
    print(f"Loaded {engine.inverted_index.total_docs} documents.")
    
    print("Building semantic index... (first run ~30s)")
    await asyncio.to_thread(semantic_engine.load)
    await asyncio.to_thread(semantic_engine.build_index, engine.documents)
    print("OK All systems ready")

@app.get("/api/search", response_model=SearchResponse)
async def search_jobs(
    q: str = "",
    mode: str = "tfidf",
    platform: List[str] = Query(None),
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    currency: List[str] = Query(None),
    budget_type: Optional[str] = None,
    skills: List[str] = Query(None),
    page: int = 1,
    per_page: int = 20
):
    start_time = time.time()
    
    # Process query
    _, query_terms = clean_text_full(q) if q else ("", [])
    
    result_docs = []
    
    if not q:
        # return all docs if no query
        result_docs = [{"doc_id": d['doc_id'], "score": 1.0} for d in engine.documents]
    elif mode == "boolean":
        doc_ids = engine.boolean_searcher.evaluate(q, preprocess_func=clean_text_full)
        result_docs = [{"doc_id": did, "score": 1.0} for did in doc_ids]
    elif mode == "phrase":
        doc_ids = engine.positional_searcher.phrase_search(query_terms)
        result_docs = [{"doc_id": did, "score": 1.0} for did in doc_ids]
    elif mode == "vsm":
        vsm_results = engine.vsm_searcher.search(query_terms, top_k=engine.inverted_index.total_docs)
        result_docs = [{"doc_id": r['doc_id'], "score": r['cosine_similarity']} for r in vsm_results]
    elif mode == "semantic":
        sem_hits = semantic_engine.search(q, top_k=200)
        result_docs = [{"doc_id": h["doc_id"], "score": h["score"]} for h in sem_hits]
    elif mode == "hybrid":
        # Lexical scores
        lex_doc_scores = {}
        for term in query_terms:
            for doc_id in engine.inverted_index.lookup(term):
                if doc_id not in lex_doc_scores:
                    lex_doc_scores[doc_id] = engine.tfidf_scorer.score(query_terms, doc_id)
        
        # Semantic scores
        sem_hits = semantic_engine.search(q, top_k=200)
        sem_doc_scores = {h["doc_id"]: h["score"] for h in sem_hits}
        
        # Combine using Reciprocal Rank Fusion or weighted average
        # We'll use weighted average of normalized scores
        all_ids = set(lex_doc_scores.keys()) | set(sem_doc_scores.keys())
        max_lex = max(lex_doc_scores.values()) if lex_doc_scores else 1.0
        
        result_docs = []
        for did in all_ids:
            l_score = (lex_doc_scores.get(did, 0) / max_lex) if lex_doc_scores else 0
            s_score = sem_doc_scores.get(did, 0)
            combined = (0.6 * l_score) + (0.4 * s_score)
            if combined > 0.1:
                result_docs.append({"doc_id": did, "score": combined})
        result_docs.sort(key=lambda x: x['score'], reverse=True)
    else: # tfidf (default)
        doc_scores = {}
        for term in query_terms:
            for doc_id in engine.inverted_index.lookup(term):
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = engine.tfidf_scorer.score(query_terms, doc_id)
        
        result_docs = [{"doc_id": k, "score": v} for k, v in doc_scores.items() if v > 0]
        result_docs.sort(key=lambda x: x['score'], reverse=True)


    # Filter
    filtered_results = []
    for rd in result_docs:
        doc = engine.documents[rd['doc_id']]
        
        # Platform filter
        if platform and "all" not in [p.lower() for p in platform]:
            if doc['platform'] not in platform:
                continue
                
        # Budget filter
        if budget_min is not None and (doc['budget_extracted'] is None or doc['budget_extracted'] < budget_min):
            continue
        if budget_max is not None and (doc['budget_extracted'] is None or doc['budget_extracted'] > budget_max):
            continue
            
        # Currency filter
        if currency and doc['budget_currency'] not in currency:
            continue
            
        # Budget type
        if budget_type and budget_type != 'all' and doc['budget_type'] != budget_type:
            continue
            
        # Skills filter
        if skills:
            doc_skills = [s.lower() for s in doc['skills']]
            if not all(s.lower() in doc_skills for s in skills):
                continue
                
        # Calculate TF-IDF breakdown if tfidf mode
        tfidf_breakdown = {}
        matched_tokens = []
        if mode == "tfidf" and q:
            for t in query_terms:
                if doc['doc_id'] in engine.inverted_index.lookup(t):
                    matched_tokens.append(t)
                    # Use explanation logic
                    exp = engine.tfidf_scorer.explain(t, doc['doc_id'])
                    tfidf_breakdown[t] = exp['tfidf']
                    
        doc_copy = doc.copy()
        doc_copy['relevance_score'] = rd['score']
        doc_copy['has_explicit_skills'] = bool(doc.get('skills'))
        doc_copy['inferred_skills'] = doc.get('inferred_skills', [])
        
        if matched_tokens:
            doc_copy['matched_tokens'] = matched_tokens
            doc_copy['tfidf_breakdown'] = tfidf_breakdown
            
        filtered_results.append(doc_copy)

    # Normalize scores relative to top filtered result if in TF-IDF mode
    if mode == "tfidf" and filtered_results:
        # Avoid inflating very weak matches (BM25 baseline)
        baseline = 1.5 * len(query_terms) if query_terms else 1.0
        max_raw = max(d['relevance_score'] for d in filtered_results)
        norm_factor = max(max_raw, baseline)
        for d in filtered_results:
            d['relevance_score'] = d['relevance_score'] / norm_factor


    # Run insight generation IN PARALLEL
    insight_task = market_insight_engine.generate(q, filtered_results[:10])
    
    # Pagination
    total = len(filtered_results)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_dicts = filtered_results[start_idx:end_idx]
    
    # Wait for insight
    insight = await insight_task
    
    # Convert to models
    paginated = [JobDocument(**d) for d in paginated_dicts]
    
    query_time_ms = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        total=total,
        page=page,
        results=paginated,
        insight=insight,
        query_time_ms=query_time_ms
    )

@app.get("/api/analytics", response_model=AnalyticsResponse)
def get_analytics_api(platform: str = "all"):
    return get_analytics(engine, platform)

@app.post("/api/match", response_model=MatchResponse)
def match_profile(req: MatchRequest):
    return match_freelancer(engine, req.skills, req.budget_expectation, req.platform)

@app.post("/api/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
            
        extracted_skills = await ner_extractor.extract_ai(text)
        return {"skills": extracted_skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing PDF: {str(e)}")


@app.get("/api/ir/index")
def get_index(term: str):
    term = term.lower()
    df = len(engine.inverted_index.lookup(term))
    idf = engine.tfidf_scorer.idf(term) if engine.tfidf_scorer else 0.0
    
    postings = []
    for doc_id, positions in engine.inverted_index.lookup(term).items():
        postings.append({
            "doc_id": doc_id,
            "tf": len(positions),
            "positions": positions
        })
        
    return {
        "term": term,
        "df": df,
        "idf": round(idf, 3),
        "postings": postings
    }

@app.get("/api/ir/tfidf")
def get_tfidf_explain(term: str, doc_id: int):
    term = term.lower()
    return engine.tfidf_scorer.explain(term, doc_id)

@app.post("/api/ir/vsm", response_model=VSMResponse)
def vsm_explain(req: VSMRequest):
    query_terms = tokenize_and_filter(req.query)
    q_vec = engine.vsm_searcher.query_vector(query_terms)
    results = engine.vsm_searcher.search(query_terms, top_k=5)
    
    top_docs = []
    for r in results:
        top_docs.append(VSMDocumentResult(
            doc_id=r['doc_id'],
            cosine_similarity=round(r['cosine_similarity'], 4),
            document_vector={k: round(v, 4) for k, v in r['document_vector'].items() if v > 0},
            title=r['title']
        ))
        
    return VSMResponse(
        query_vector={k: round(v, 4) for k, v in q_vec.items()},
        top_documents=top_docs
    )

