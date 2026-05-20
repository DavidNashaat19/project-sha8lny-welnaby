from typing import List, Dict, Any
from .ir_engine import VSMSearcher
from .preprocess import clean_text_full
from collections import Counter

def match_freelancer(engine, skills: List[str], budget_expectation: float = None, platform: str = "all") -> Dict[str, Any]:
    # Use VSM Searcher to find jobs matching user skills
    # Ensure lowercase matching
    # Use IR pipeline to normalize skills
    normalized_skills = []
    for s in skills:
        _, tokens = clean_text_full(s)
        if tokens:
            normalized_skills.append(tokens[0])
    
    skills = normalized_skills
    
    docs = engine.documents
    if platform != 'all':
        docs = [d for d in docs if d['platform'].lower() == platform.lower()]
        
    # We will build a temporary VSMSearcher for just the filtered docs, or use the global one and filter results.
    # It's faster to use global and filter results if there aren't many docs.
    # But wait, VSM vectors might include skills. Let's just use the global one and filter by platform/budget.
    results = engine.vsm_searcher.search(skills, top_k=100) # get more to filter
    
    filtered_results = []
    for r in results:
        doc = engine.vsm_searcher.documents[r['doc_id']]
        if platform != 'all' and doc['platform'].lower() != platform.lower():
            continue
            
        # We can also add budget logic here if needed, but the prompt just says find matches
        
        filtered_results.append({
            "job": doc,
            "score": r['cosine_similarity']
        })
        if len(filtered_results) >= 10:
            break
            
    # Calculate match score based on top results or just average of top 3
    match_score = 0.0
    if filtered_results:
        match_score = sum(r['score'] for r in filtered_results[:5]) / min(5, len(filtered_results))

    # Gap skills - skills present in top matched jobs but not in user profile
    # Only consider top 10 jobs
    top_jobs_skills = Counter()
    for r in filtered_results:
        for s in r['job']['skills']:
            top_jobs_skills[s.lower()] += 1
            
    matched_skills = [s for s in top_jobs_skills if s in skills]
    gap_skills_raw = [s for s in top_jobs_skills if s not in skills]
    
    # Sort gap skills by frequency in top jobs
    gap_skills_raw.sort(key=lambda s: top_jobs_skills[s], reverse=True)
    gap_skills = [s for s in gap_skills_raw if top_jobs_skills[s] > 1][:5]
    
    # Suggested skills: skills co-occurring with user's skills
    suggested_skills = [s for s in gap_skills_raw if top_jobs_skills[s] == 1][:5]

    top_jobs_formatted = []
    for r in filtered_results:
        job_doc = r['job'].copy()
        job_doc['relevance_score'] = r['score']
        # add matching format expected by the frontend
        top_jobs_formatted.append(job_doc)

    return {
        "match_score": round(match_score, 2),
        "top_jobs": top_jobs_formatted,
        "matched_skills": matched_skills,
        "gap_skills": gap_skills,
        "suggested_skills": suggested_skills
    }
