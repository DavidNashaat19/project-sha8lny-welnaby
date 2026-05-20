import re
import httpx
import os
import json
import pandas as pd
from dotenv import load_dotenv
from .preprocess import remove_noise, lowercase_english

load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


# A comprehensive set of popular technical skills to ensure the regex extractor finds them in CVs
POPULAR_TECHNICAL_SKILLS = [
    # Languages
    "python", "javascript", "typescript", "php", "java", "kotlin", "swift", "c++", "c#", "dart", "go", "rust", "ruby", "c", "r", "matlab",
    # Frontend
    "react", "vue", "angular", "next.js", "nuxt", "svelte", "tailwind", "bootstrap", "html", "css", "sass", "jquery", "frontend", "front-end", "web development",
    # Backend
    "nodejs", "node.js", "django", "fastapi", "flask", "laravel", "express", "spring", "rails", "asp.net", "backend", "back-end",
    # Mobile
    "flutter", "react native", "android", "ios", "expo", "xcode", "mobile app",
    # Design
    "figma", "photoshop", "illustrator", "xd", "sketch", "canva", "indesign", "after effects", "premiere pro", "davinci resolve", "ui/ux", "graphic design", "logo design",
    # Data & AI
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras", "tableau", "power bi", "excel", "sql", "mongodb", "postgresql", "firebase", "mysql", "oracle", "sqlite", "data analysis", "machine learning", "deep learning", "artificial intelligence", "ai",
    # DevOps
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "github", "linux", "ci/cd", "devops",
    # CAD & 3D
    "autocad", "revit", "solidworks", "blender", "cinema 4d", "3ds max", "sketchup", "unity", "unreal", "3d rendering", "3d design",
    # CMS
    "wordpress", "shopify", "woocommerce", "webflow", "squarespace", "joomla",
    # Marketing
    "seo", "google ads", "facebook ads", "meta ads", "mailchimp", "hubspot", "crm", "digital marketing", "social media", "lead generation"
]


def load_dataset_skills() -> list[str]:
    """
    Dynamically load all unique skills present in the dataset (JSON or CSV)
    and merge them with a rich technical vocabulary.
    """
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, 'data', 'freelance_data.json')
    skills_set = set(POPULAR_TECHNICAL_SKILLS)
    
    # 1. Try loading from JSON
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                projects = data.get("projects") if isinstance(data, dict) else data
                if isinstance(projects, list):
                    for item in projects:
                        skills = item.get("skills") or []
                        for s in skills:
                            if s and str(s).strip():
                                skills_set.add(str(s).strip().lower())
        except Exception as e:
            print(f"[NER Dynamic] Warning loading JSON: {e}")
            
    # 2. Try loading from CSV if JSON failed or is empty
    csv_path = os.path.join(base_dir, 'data', 'data_after_cleaning.csv')
    if os.path.exists(csv_path):
        try:
            import ast
            df = pd.read_csv(csv_path)
            if 'skills_clean' in df.columns:
                for val in df['skills_clean'].dropna():
                    try:
                        lst = ast.literal_eval(val)
                        if isinstance(lst, list):
                            for s in lst:
                                if s and str(s).strip():
                                    skills_set.add(str(s).strip().lower())
                    except Exception:
                        pass
        except Exception as e:
            print(f"[NER Dynamic] Warning loading CSV: {e}")

    print(f"[NER Dynamic] Loaded {len(skills_set)} unique matching skills (merged with popular technical vocab).")
    return list(skills_set)


# Load vocabulary and build robust regex pattern
DATASET_SKILLS = load_dataset_skills()

# Sort by length in descending order to match multi-word skills first (e.g. "react native" before "react")
SORTED_SKILLS = sorted(DATASET_SKILLS, key=len, reverse=True)


def get_pattern_for_skill(skill: str) -> str:
    """Generate exact regex pattern for a skill, handling word boundaries for special chars."""
    escaped = re.escape(skill)
    # Check if first/last characters are standard alphanumeric or Arabic word characters
    starts_with_word = bool(re.match(r"^[\w\u0600-\u06FF]", skill, re.UNICODE))
    ends_with_word = bool(re.match(r"[\w\u0600-\u06FF]$", skill, re.UNICODE))
    
    start_boundary = r"\b" if starts_with_word else ""
    end_boundary = r"\b" if ends_with_word else ""
    return f"{start_boundary}{escaped}{end_boundary}"


ALL_PATTERN = re.compile(
    "|".join(get_pattern_for_skill(s) for s in SORTED_SKILLS),
    re.IGNORECASE | re.UNICODE
)


class NERExtractor:
    def extract(self, text: str) -> list[str]:
        """Return deduplicated list of detected technical skills using high-performance regex matching."""
        if not text:
            return []
        
        # Simple, non-destructive lowercasing keeps punctuation like C++ and C# intact
        cleaned = text.lower()
        
        found = {}
        for match in ALL_PATTERN.finditer(cleaned):
            entity = match.group().lower().strip()
            if entity not in found:
                found[entity] = True
        return list(found.keys())

    async def extract_ai(self, text: str) -> list[str]:
        """
        Extract skills using LLM for much higher accuracy.
        Falls back to the robust, dynamic regex extract() if API fails or no key.
        """
        if not GROQ_API_KEY or not text:
            return self.extract(text)

        # Truncate text to avoid token limits (first 4000 chars usually enough for resume)
        sample = text[:4000]
        
        prompt = f"""You are an expert technical recruiter and resume parser.
Extract EVERY technical skill, programming language, framework, library, tool, database, and platform mentioned in the text below.
Include specific technologies (e.g., 'React.js', 'PostgreSQL', 'Docker') and methodologies (e.g., 'Agile', 'Scrum').

OUTPUT FORMAT:
Return ONLY a JSON object with a single key "skills" containing a list of strings.
Example: {{"skills": ["python", "django", "aws", "kubernetes"]}}

Text to parse:
{sample}"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a professional technical entity extractor."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.0, # Maximum precision
                        "response_format": {"type": "json_object"}
                    }
                )

                data = resp.json()
                if "choices" not in data:
                    print(f"[NER AI] Error: 'choices' key missing in response. Status: {resp.status_code}. Response: {data}")
                    return self.extract(text)

                content = data["choices"][0]["message"]["content"]
                # Try parsing as JSON list
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "skills" in parsed:
                    return [str(s).lower() for s in parsed["skills"]]
                elif isinstance(parsed, list):
                    return [str(s).lower() for s in parsed]
                
                # Fallback to regex if JSON parsing is weird
                return self.extract(text)
        except Exception as e:
            print(f"[NER AI] Error: {e}")
            return self.extract(text)

    def enrich_documents(self, documents: list[dict]) -> list[dict]:
        """
        For each document with no explicit skills, run NER on description.
        Adds 'inferred_skills' key (list of strings) to every document.
        Modifies documents list in-place and returns it.
        """
        enriched = 0
        for doc in documents:
            has_skills = bool(doc.get("skills") and len(doc["skills"]) > 0)
            if not has_skills:
                desc = doc.get("full_description") or doc.get("description_snippet") or ""
                doc["inferred_skills"] = self.extract(desc)
                enriched += 1
            else:
                doc["inferred_skills"] = []
        print(f"[NER] Enrichment done: {enriched} documents enriched")
        return documents


ner_extractor = NERExtractor()
