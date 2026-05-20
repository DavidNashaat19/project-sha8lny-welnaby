"""
=============================================================================
 preprocess.py  —  IR Text Processing Pipeline
 Course  : CS313x Information Retrieval
 Project : Freelance Market Monitor (Sha8lny Welnaby)
=============================================================================
Bona-fide manual scraping implemented using requests + BeautifulSoup as per CS313x Lab requirements. No automated bypass libraries used.

WHAT THIS SCRIPT DOES (Slide-06 Implementation)
-------------------------------------------------
Reads  : freelance_data.json   (raw scraper output)
Writes : data_before_cleaning.csv  (raw, unformatted data)
         data_after_cleaning.csv   (tokenized, normalized, IR-ready data)

NLP PIPELINE STEPS
------------------
1. Noise Reduction (Regex)     — strip HTML tags, URLs, special chars
2. Arabic Normalization        — unify Alef/Ta-Marbuta/Waw/Yaa variants
3. English Lowercasing         — all Latin text -> lowercase
4. Stop-word Removal           — remove EN + AR common words
5. Tokenization                — whitespace split on clean text
6. Entity Extraction (Budget)  — parse "SR 200-500" -> 300.0 (midpoint float)

HOW TO RUN
----------
    python preprocess.py
    python preprocess.py --input my_data.json --output-dir ./output
"""

import argparse
import json
import re
import sys
from pathlib import Path

import nltk
import pandas as pd
from nltk.corpus import stopwords

# Download NLTK stopwords corpus (only downloads once, silent after that)
nltk.download('stopwords', quiet=True)

# ---------------------------------------------------------------------------
# Arabic stop-words — loaded from NLTK's complete corpus (754 words)
# ---------------------------------------------------------------------------
NLTK_ARABIC_STOPWORDS = set(stopwords.words('arabic'))
ARABIC_STOPWORDS = NLTK_ARABIC_STOPWORDS

# ---------------------------------------------------------------------------
# English stop-words — loaded from NLTK's complete corpus (179 words)
# Using NLTK instead of a manual list ensures no common words are missed.
# Doctor's Feedback Point #3: "use NLTK for stopword removal"
# ---------------------------------------------------------------------------
ENGLISH_STOPWORDS = set(stopwords.words('english'))

ALL_STOPWORDS = ARABIC_STOPWORDS | ENGLISH_STOPWORDS

# ---------------------------------------------------------------------------
# Step 1 — Noise Reduction (Regex HTML stripping)
# ---------------------------------------------------------------------------
_HTML_TAG   = re.compile(r"<[^>]+>")
_URL_PAT    = re.compile(r"https?://\S+|www\.\S+")
_SPECIAL    = re.compile(r"[^\w\s\u0600-\u06FF\.\-]", re.UNICODE)
_MULTI_SPC  = re.compile(r"\s+")


def remove_noise(text: str) -> str:
    """Strip HTML tags, URLs, and non-alphanumeric characters."""
    if not text or not isinstance(text, str):
        return ""
    text = _HTML_TAG.sub(" ", text)      # <p>...</p> -> space
    text = _URL_PAT.sub(" ", text)       # https://... -> space
    text = _SPECIAL.sub(" ", text)       # special chars -> space
    text = _MULTI_SPC.sub(" ", text)     # collapse whitespace
    return text.strip()

# ---------------------------------------------------------------------------
# Step 2 — Arabic Normalization
# ---------------------------------------------------------------------------
_ALEF_VARIANTS  = re.compile(r"[أإآٱ]")          # normalize to bare Alef ا
_TA_MARBUTA     = re.compile(r"ة")                # ة -> ه (for IR matching)
_WAW_VARIANTS   = re.compile(r"ؤ")               # ؤ -> و
_YAA_VARIANTS   = re.compile(r"[ىئ]")            # ى ئ -> ي
_TATWEEL        = re.compile(r"\u0640")           # remove tatweel ـ
_DIACRITICS     = re.compile(r"[\u064B-\u065F]")  # remove tashkeel (harakat)


def normalize_arabic(text: str) -> str:
    """
    Unify Arabic character variants for consistent IR matching.
    Example: 'أحمد' and 'احمد' should map to the same token.
    """
    if not text:
        return text
    text = _ALEF_VARIANTS.sub("ا", text)
    text = _TA_MARBUTA.sub("ه", text)
    text = _WAW_VARIANTS.sub("و", text)
    text = _YAA_VARIANTS.sub("ي", text)
    text = _TATWEEL.sub("", text)
    text = _DIACRITICS.sub("", text)
    return text

# ---------------------------------------------------------------------------
# Step 3 — Lowercasing (English)
# ---------------------------------------------------------------------------
def lowercase_english(text: str) -> str:
    """Lowercase only ASCII/Latin characters; preserve Arabic case."""
    return text.lower()   # safe for mixed AR/EN — Arabic has no case

# ---------------------------------------------------------------------------
# Step 4 — Stop-word Removal & Tokenization
# ---------------------------------------------------------------------------
def tokenize_and_filter(text: str) -> list:
    """
    Split on whitespace, remove stop-words and single-character tokens.
    Returns a list of meaningful tokens ready for IR indexing.
    """
    tokens = text.split()
    return [t for t in tokens if t not in ALL_STOPWORDS and len(t) > 1]

# ---------------------------------------------------------------------------
# Step 5 — Entity Extraction (Budget)
# ---------------------------------------------------------------------------
_CURRENCY_MAP = {
    "$": "USD", "\u00a3": "GBP", "\u20ac": "EUR",
    "SAR": "SAR", "SR": "SAR", "\u0631.\u0633": "SAR",
    "EGP": "EGP", "\u062c.\u0645": "EGP",
}
_NUMBER_PAT = re.compile(r"[\d,]+\.?\d*")


def extract_budget_float(raw: str) -> float | None:
    """
    Parse a messy budget string into a single float (midpoint).
    Slide-06 example: 'SR 200 - 500' -> 350.0
    """
    if not raw or not isinstance(raw, str):
        return None
    raw_clean = raw.replace(",", "")
    nums = [float(n) for n in _NUMBER_PAT.findall(raw_clean) if n]
    if not nums:
        return None
    return sum(nums) / len(nums)   # midpoint

# ---------------------------------------------------------------------------
# Full pipeline function
# ---------------------------------------------------------------------------
def clean_text_full(text: str) -> tuple[str, list]:
    """
    Run the complete 4-step NLP pipeline on a single text field.
    Returns: (cleaned_text_string, tokens_list)
    """
    t = remove_noise(text)
    t = normalize_arabic(t)
    t = lowercase_english(t)
    tokens = tokenize_and_filter(t)
    return " ".join(tokens), tokens


def safe_str(val) -> str:
    """Safe conversion to string, stripping NaN values."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() == 'nan':
        return ""
    return s


def process_row(row: dict) -> dict:
    """
    Apply the full IR preprocessing pipeline to one project record.
    Combines title + description_snippet as the main text corpus field.
    """
    # --- Combine text fields ---
    desc = safe_str(row.get("full_description") or row.get("description_snippet") or "")
    
    skills_list = []
    for s in (row.get("skills") or []):
        s_str = safe_str(s)
        if s_str:
            skills_list.append(s_str)

    raw_text = " ".join(filter(None, [
        safe_str(row.get("title")),
        desc,
        " ".join(skills_list),
        safe_str(row.get("category")),
    ]))

    cleaned_text, tokens = clean_text_full(raw_text)

    # --- Budget entity extraction ---
    budget_raw = (
        safe_str(row.get("budget_min")) + " " +
        safe_str(row.get("budget_max"))
    ).strip()
    # Use numeric budget if already parsed; fall back to raw string parsing
    b_min = row.get("budget_min")
    b_max = row.get("budget_max")
    if b_min is not None and b_max is not None and not pd.isna(b_min) and not pd.isna(b_max):
        try:
            budget_extracted = (float(b_min) + float(b_max)) / 2
        except (ValueError, TypeError):
            budget_extracted = None
    else:
        budget_extracted = extract_budget_float(budget_raw)

    return {
        "platform":          row.get("platform"),
        "title_raw":         safe_str(row.get("title")) or "Unknown Title",
        "title_clean":       cleaned_text[:120] if cleaned_text else "",
        "cleaned_text":      cleaned_text,
        "full_description":  desc,
        "tokens":            tokens,
        "token_count":       len(tokens),
        "budget_extracted":  budget_extracted,
        "budget_currency":   row.get("budget_currency"),
        "budget_type":       row.get("budget_type"),
        "skills_clean":      [
            " ".join(tokenize_and_filter(
                lowercase_english(normalize_arabic(remove_noise(safe_str(s))))))
            for s in (row.get("skills") or []) if safe_str(s)
        ],
        "category_clean":    lowercase_english(
            normalize_arabic(remove_noise(safe_str(row.get("category"))))),
        "posted_date":       row.get("posted_date"),
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="IR Text Processing Pipeline — Sha8lny Welnaby")
    parser.add_argument("--input",      default="freelance_data.json",
                        help="Path to raw JSON from scraper.py")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to write CSV outputs")
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_dir  = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    before_path = output_dir / "data_before_cleaning.csv"
    after_path  = output_dir / "data_after_cleaning.csv"

    # ── Load JSON ───────────────────────────────────────────────────────────
    if not input_path.exists():
        print(f"ERROR: Cannot find {input_path}. Run scraper.py first.")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    projects = data.get("projects", [])
    if not projects:
        print("ERROR: No projects found in JSON.")
        sys.exit(1)

    # ── Deduplicate by url ──────────────────────────────────────────────────
    df_raw = pd.DataFrame(projects)
    if "url" in df_raw.columns:
        df_raw.drop_duplicates(subset=["url"], keep="first", inplace=True)
        before_len = len(projects)
        if len(df_raw) < before_len:
            print(f"Deduplicated {before_len - len(df_raw)} records based on unique url.")
    projects = df_raw.to_dict(orient="records")

    print(f"Loaded {len(projects)} raw records from {input_path}")

    # ── Missing Value Detection & Treatment ─────────────────────────────────
    # Doctor's Feedback Point #4: "missing values are still not properly handled"
    print("\n" + "=" * 55)
    print("  MISSING VALUE ANALYSIS (Before Cleaning)")
    print("=" * 55)
    df_check = pd.DataFrame(projects)
    missing = df_check.isnull().sum()
    missing_pct = (missing / len(df_check) * 100).round(1)
    missing_report = missing[missing > 0]
    if missing_report.empty:
        print("  ✔ No missing values detected.")
    else:
        print(f"  {'Column':<30} {'Missing':>8} {'% Missing':>10}")
        print(f"  {'-'*50}")
        for col in missing_report.index:
            print(f"  {col:<30} {missing[col]:>8} {missing_pct[col]:>9}%")

    # Treatment strategy:
    # 1. Drop rows completely missing BOTH title and full_description (useless for text modeling)
    df_check.dropna(subset=['title', 'full_description'], how='all', inplace=True)
    
    # 2. Fill remaining text columns with 'Unknown' instead of empty string
    text_cols = ["title", "full_description", "description_snippet", "category"]
    for col in text_cols:
        if col in df_check.columns:
            df_check[col] = df_check[col].fillna("Unknown")

    # 3. Numeric columns: Fill missing budgets using the median OF THAT CURRENCY
    if "budget_currency" not in df_check.columns:
        df_check["budget_currency"] = "Unknown"

    numeric_cols = ["budget_min", "budget_max"]
    for col in numeric_cols:
        if col in df_check.columns:
            df_check[col] = pd.to_numeric(df_check[col], errors='coerce')
            # Impute using the median per currency
            df_check[col] = df_check.groupby('budget_currency')[col].transform(
                lambda x: x.fillna(x.median() if not x.dropna().empty else 0)
            )
            df_check[col] = df_check[col].fillna(0) # Fallback if entirely missing

    if "skills" in df_check.columns:
        df_check["skills"] = df_check["skills"].apply(
            lambda x: x if isinstance(x, list) else [])

    for col in ["platform", "url", "posted_date", "budget_currency", "budget_type"]:
        if col in df_check.columns:
            df_check[col] = df_check[col].fillna("Unknown")

    # Count remaining missing values after treatment
    remaining = df_check.isnull().sum().sum()
    print(f"\n  Missing values after treatment: {remaining}")
    print("=" * 55)

    projects = df_check.to_dict(orient="records")

    # ── BEFORE: raw data CSV ─────────────────────────────────────────────────
    df_raw = pd.DataFrame(projects)
    # Flatten the skills list to a pipe-separated string for CSV readability
    if "skills" in df_raw.columns:
        df_raw["skills"] = df_raw["skills"].apply(
            lambda x: " | ".join(x) if isinstance(x, list) else str(x or ""))
    df_raw.to_csv(before_path, index=False, encoding="utf-8-sig")
    print(f"[BEFORE] data_before_cleaning.csv  -> {len(df_raw)} rows, "
          f"{len(df_raw.columns)} columns saved to {before_path}")

    # ── Apply IR pipeline ────────────────────────────────────────────────────
    print("\nRunning IR preprocessing pipeline...")
    processed = []
    for i, row in enumerate(projects):
        try:
            processed.append(process_row(row))
        except Exception as exc:
            print(f"  WARNING: Row {i} failed: {exc}")

    df_clean = pd.DataFrame(processed)
    # Convert tokens list to pipe-separated string for CSV
    if "tokens" in df_clean.columns:
        df_clean["tokens"] = df_clean["tokens"].apply(
            lambda x: " | ".join(x) if isinstance(x, list) else str(x or ""))
    if "skills_clean" in df_clean.columns:
        df_clean["skills_clean"] = df_clean["skills_clean"].apply(
            lambda x: " | ".join(x) if isinstance(x, list) else str(x or ""))

    df_clean.to_csv(after_path, index=False, encoding="utf-8-sig")
    print(f"[AFTER]  data_after_cleaning.csv   -> {len(df_clean)} rows, "
          f"{len(df_clean.columns)} columns saved to {after_path}")

    # ── Summary stats ────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  PREPROCESSING SUMMARY")
    print("=" * 55)
    print(f"  Total records processed : {len(processed)}")
    if "token_count" in df_clean.columns:
        print(f"  Avg tokens per record   : {df_clean['token_count'].mean():.1f}")
    if "budget_extracted" in df_clean.columns:
        n_budgets = df_clean["budget_extracted"].notna().sum()
        print(f"  Records with budget     : {n_budgets} "
              f"({n_budgets/len(df_clean)*100:.0f}%)")
    print("=" * 55)

    # ── Sample transformation ────────────────────────────────────────────────
    print("\nSample transformation (first record):")
    if projects:
        raw_sample = projects[0]
        clean_sample = processed[0]
        print(f"  RAW title    : {raw_sample.get('title', '')[:80]}")
        print(f"  CLEAN tokens : {clean_sample['tokens'][:8]}")
        print(f"  Budget       : {raw_sample.get('budget_min')} - "
              f"{raw_sample.get('budget_max')}  ->  {clean_sample['budget_extracted']}")
    print("\nDone.")


if __name__ == "__main__":
    main()
