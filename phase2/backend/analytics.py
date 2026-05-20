from collections import Counter, defaultdict
import pandas as pd
from typing import List, Dict, Any

def get_analytics(engine, platform_filter: str) -> Dict[str, Any]:
    import numpy as np
    docs = engine.documents
    if platform_filter != 'all':
        docs = [d for d in docs if d['platform'].lower() == platform_filter.lower()]
        
    if not docs:
        return {
            "top_skills": [],
            "platform_dist": {},
            "budget_stats": {},
            "budget_histogram": [],
            "skills_by_budget": [],
            "cooccurrence_matrix": {},
            "currency_dist": {},
            "token_count_dist": []
        }

    # Platform distribution
    platform_counts = Counter(d['platform'] for d in docs)
    
    # Skills distribution
    skill_counter = Counter()
    skill_platform_counter = {}
    for d in docs:
        for s in d['skills']:
            skill_counter[s] += 1
            if s not in skill_platform_counter:
                skill_platform_counter[s] = Counter()
            skill_platform_counter[s][d['platform']] += 1
            
    top_skills_raw = skill_counter.most_common(20)
    top_skills = []
    for s, c in top_skills_raw:
        top_skills.append({
            "skill": s,
            "count": c,
            "platforms": dict(skill_platform_counter[s])
        })

    # Budget stats
    budgets = [d['budget_extracted'] for d in docs if d['budget_extracted'] is not None]
    if budgets:
        budget_stats = {
            "mean": round(float(np.mean(budgets)), 2),
            "median": round(float(np.median(budgets)), 2),
            "max": round(float(np.max(budgets)), 2)
        }
    else:
        budget_stats = {"mean": 0, "median": 0, "max": 0}

    # Budget histogram
    budget_hist = []
    if budgets:
        counts, bins = np.histogram(budgets, bins=10)
        for i in range(len(counts)):
            budget_hist.append({
                "range": f"{int(bins[i])}-{int(bins[i+1])}",
                "count": int(counts[i])
            })

    # Skills by budget
    skill_budget_sums = defaultdict(list)
    for d in docs:
        if d['budget_extracted']:
            for s in d['skills']:
                skill_budget_sums[s].append(d['budget_extracted'])
                
    skills_by_budget = []
    for s, b_list in skill_budget_sums.items():
        if len(b_list) >= 2: # only skills with multiple occurrences
            skills_by_budget.append({
                "skill": s,
                "avg_budget": round(float(np.mean(b_list)), 2),
                "frequency": len(b_list)
            })
    skills_by_budget.sort(key=lambda x: x['frequency'], reverse=True)
    skills_by_budget = skills_by_budget[:20]

    # Co-occurrence
    top_15_skills = [s for s, c in skill_counter.most_common(15)]
    cooccurrence_matrix = {s1: {s2: 0 for s2 in top_15_skills} for s1 in top_15_skills}
    for d in docs:
        s_set = set(d['skills']).intersection(top_15_skills)
        for s1 in s_set:
            for s2 in s_set:
                if s1 != s2:
                    cooccurrence_matrix[s1][s2] += 1

    # Currency
    currency_counts = Counter(d['budget_currency'] for d in docs if d['budget_currency'])
    
    # Token count
    token_counts_list = [len(d['tokens']) for d in docs]
    token_hist = []
    if token_counts_list:
        t_counts, t_bins = np.histogram(token_counts_list, bins=10)
        for i in range(len(t_counts)):
            token_hist.append({
                "range": f"{int(t_bins[i])}-{int(t_bins[i+1])}",
                "count": int(t_counts[i])
            })

    return {
        "top_skills": top_skills,
        "platform_dist": dict(platform_counts),
        "budget_stats": budget_stats,
        "budget_histogram": budget_hist,
        "skills_by_budget": skills_by_budget,
        "cooccurrence_matrix": cooccurrence_matrix,
        "currency_dist": dict(currency_counts),
        "token_count_dist": token_hist
    }
