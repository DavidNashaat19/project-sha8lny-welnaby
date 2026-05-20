import pandas as pd
import json
import os
from typing import Dict, Any

from .ir_engine import InvertedIndex, TFIDFScorer, VSMSearcher, BooleanSearcher, PositionalSearcher
from .ner_extractor import ner_extractor

class SearchEngine:
    def __init__(self):
        self.documents = []
        self.inverted_index = InvertedIndex()
        self.tfidf_scorer = None
        self.vsm_searcher = None
        self.boolean_searcher = None
        self.positional_searcher = None
        self.is_loaded = False

    def load_data(self, csv_path: str, json_path: str):
        # Read the cleaned data
        df = pd.read_csv(csv_path)
        
        # We also need URLs from the JSON, or we can just reconstruct them if available
        # The prompt says URL is in json, but let's read the JSON to get URLs by matching titles
        urls = {}
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            for proj in raw_data.get('projects', []):
                # match by some approximate logic or assuming order is similar?
                # actually, looking at the data, the JSON has the exact same projects.
                # Since the cleaning might drop rows or keep order, we can map by title snippet.
                pass
        
        self.documents = []
        for idx, row in df.iterrows():
            if pd.isna(row['tokens']):
                tokens = []
            else:
                tokens = [t.strip() for t in str(row['tokens']).split('|') if t.strip()]
            
            if pd.isna(row['skills_clean']):
                skills = []
            else:
                skills = [s.strip() for s in str(row['skills_clean']).split('|') if s.strip()]

            budget = row['budget_extracted']
            budget = float(budget) if pd.notna(budget) else None

            # Attempt to find URL from JSON based on matching
            # For simplicity, we just look up by platform and title snippet
            # Let's map directly if possible, or use a default
            doc = {
                "doc_id": idx,
                "platform": row['platform'],
                "title": row['title_raw'] if pd.notna(row['title_raw']) else (row['title_clean'] if pd.notna(row['title_clean']) else "Unknown Title"),
                "description_snippet": row['full_description'][:150] + "..." if pd.notna(row.get('full_description')) else "",
                "skills": skills,
                "budget_extracted": budget,
                "budget_currency": row['budget_currency'] if pd.notna(row['budget_currency']) else None,
                "budget_type": row['budget_type'] if pd.notna(row['budget_type']) else None,
                "url": "#", # We'll populate this later properly if needed
                "tokens": tokens
            }
            self.documents.append(doc)

        # Build indexes
        self.inverted_index.build(self.documents)
        self.tfidf_scorer = TFIDFScorer(self.inverted_index, self.documents)
        self.vsm_searcher = VSMSearcher(self.inverted_index, self.documents)
        self.boolean_searcher = BooleanSearcher(self.inverted_index)
        self.positional_searcher = PositionalSearcher(self.inverted_index)
        self.is_loaded = True

engine = SearchEngine()

def load_all_data():
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, 'data', 'data_after_cleaning.csv')
    json_path = os.path.join(base_dir, 'data', 'freelance_data.json')
    engine.load_data(csv_path, json_path)
    
    # Try mapping URLs from JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        proj_list = raw_data.get('projects', [])
        # We can try to zip them if lengths match, or match by title
        # For simplicity, if len matches, just zip
        if len(proj_list) == len(engine.documents):
            for i, p in enumerate(proj_list):
                engine.documents[i]['url'] = p.get('url', '#')
                engine.documents[i]['title'] = p.get('title', engine.documents[i]['title']) # Use raw title instead of cleaned if available
        else:
            # Fallback title matching
            title_url_map = {str(p.get('title', '')).strip(): p.get('url', '#') for p in proj_list}
            for d in engine.documents:
                raw_t = str(d['title']).strip()
                d['url'] = title_url_map.get(raw_t, '#')
    
    # Run NER enrichment
    ner_extractor.enrich_documents(engine.documents)
