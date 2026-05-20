import json
import os
from typing import Dict, Any

from .ir_engine import InvertedIndex, TFIDFScorer, VSMSearcher, BooleanSearcher, PositionalSearcher
from .ner_extractor import ner_extractor
from .preprocess import clean_text_full


class SearchEngine:
    def __init__(self):
        self.documents = []
        self.inverted_index = InvertedIndex()
        self.tfidf_scorer = None
        self.vsm_searcher = None
        self.boolean_searcher = None
        self.positional_searcher = None
        self.is_loaded = False

    def load_data(self, json_path: str):
        """Load directly from freelance_data.json — no CSV dependency."""
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        projects = raw_data.get("projects", [])
        if not projects:
            raise ValueError(f"No projects found in {json_path}")

        self.documents = []
        for idx, proj in enumerate(projects):
            # ── Skills ──────────────────────────────────────────────────
            raw_skills = proj.get("skills") or []
            if isinstance(raw_skills, str):
                raw_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
            skills = list(dict.fromkeys(s.strip() for s in raw_skills if str(s).strip()))  # deduplicate, preserve order

            # ── Budget ──────────────────────────────────────────────────
            b_min = proj.get("budget_min")
            b_max = proj.get("budget_max")
            if b_min is not None and b_max is not None:
                try:
                    budget = (float(b_min) + float(b_max)) / 2.0
                except (TypeError, ValueError):
                    budget = None
            elif b_min is not None:
                try:
                    budget = float(b_min)
                except (TypeError, ValueError):
                    budget = None
            elif b_max is not None:
                try:
                    budget = float(b_max)
                except (TypeError, ValueError):
                    budget = None
            else:
                budget = None

            # ── Text corpus to tokenize ─────────────────────────────────
            title        = proj.get("title", "") or ""
            full_desc    = proj.get("full_description", "") or ""
            snippet      = proj.get("description_snippet", "") or ""
            skills_text  = " ".join(skills)
            category     = proj.get("category", "") or ""

            combined_text = f"{title} {skills_text} {category} {full_desc or snippet}"
            _, tokens = clean_text_full(combined_text)

            # ── Build document dict ─────────────────────────────────────
            doc = {
                "doc_id":             idx,
                "platform":           proj.get("platform", "Unknown"),
                "title":              title,
                "full_description":   full_desc,
                "description_snippet": (snippet or full_desc[:200] + "..." if full_desc else ""),
                "skills":             skills,
                "budget_min":         b_min,
                "budget_max":         b_max,
                "budget_extracted":   budget,
                "budget_currency":    proj.get("budget_currency") or None,
                "budget_type":        proj.get("budget_type") or None,
                "category":           category,
                "posted_date":        proj.get("posted_date") or None,
                "url":                proj.get("url", "#"),
                "tokens":             tokens,
                "inferred_skills":    [],
            }
            self.documents.append(doc)

        # Build indexes
        self.inverted_index.build(self.documents)
        self.tfidf_scorer     = TFIDFScorer(self.inverted_index, self.documents)
        self.vsm_searcher     = VSMSearcher(self.inverted_index, self.documents)
        self.boolean_searcher = BooleanSearcher(self.inverted_index)
        self.positional_searcher = PositionalSearcher(self.inverted_index)
        self.is_loaded = True


engine = SearchEngine()


def load_all_data():
    base_dir  = os.path.dirname(__file__)
    # Primary: use the root-level freelance_data.json (the one the user scraped)
    root_json = os.path.join(base_dir, "..", "..", "freelance_data.json")
    data_json = os.path.join(base_dir, "data", "freelance_data.json")

    if os.path.exists(root_json):
        json_path = os.path.normpath(root_json)
    elif os.path.exists(data_json):
        json_path = data_json
    else:
        raise FileNotFoundError(
            "Could not find freelance_data.json. "
            f"Checked:\n  {root_json}\n  {data_json}"
        )

    print(f"[DataLoader] Loading from: {json_path}")
    engine.load_data(json_path)

    # Run NER enrichment on loaded documents
    ner_extractor.enrich_documents(engine.documents)
