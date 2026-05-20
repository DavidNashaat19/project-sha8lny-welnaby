"""
=============================================================================
 Sha8lny Welnaby — Freelance Market Explorer + IR Strategies Dashboard
 File  : eda_app.py
 Stack : Streamlit · Pandas · Plotly · scikit-learn
 Input : freelance_data.json  (scraper.py)
         data_after_cleaning.csv  (preprocess.py)
=============================================================================
Bona-fide manual scraping implemented using requests + BeautifulSoup as per CS313x Lab requirements. No automated bypass libraries used.
=============================================================================
TABS
  1. Skills Analysis       — top skills, platform comparison
  2. Budget Insights       — histogram, box, pie
  3. Categories            — distribution, budget by category
  4. IR Strategies         — Inverted Index, Positional, TDIM, VSM, LSA
  5. TF-IDF Explorer       — interactive query, TF/IDF/TF-IDF, phrase search
  6. Raw Data              — filterable table + CSV download
"""

import json, re, math, warnings
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

FILE_JSON  = "freelance_data.json"
FILE_CLEAN = "data_after_cleaning.csv"

st.set_page_config(
    page_title="Sha8lny Welnaby — Freelance Market Explorer",
    page_icon="📊", layout="wide", initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;background:#080b14;color:#d4d8e8;}
h1,h2,h3,h4{font-family:'Space Grotesk',sans-serif!important;}
.stApp{background:#080b14;}
.stTabs [data-baseweb="tab-list"]{background:#0f1322;border-radius:12px;padding:4px;gap:4px;border:1px solid #1e2540;}
.stTabs [data-baseweb="tab"]{border-radius:8px;color:#6b7399;font-weight:500;font-size:0.85rem;padding:8px 18px;letter-spacing:0.03em;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#1e3a8a,#1d4ed8)!important;color:#fff!important;}
.kpi-card{background:linear-gradient(135deg,#0f1322 0%,#0a0d1a 100%);border:1px solid #1e2540;border-radius:14px;padding:22px 20px;text-align:center;transition:border-color .25s,transform .2s;}
.kpi-card:hover{border-color:#3b82f6;transform:translateY(-2px);}
.kpi-value{font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;color:#60a5fa;line-height:1;}
.kpi-label{font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;color:#4b5680;margin-top:8px;}
.section-badge{display:inline-block;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3);color:#60a5fa;font-size:0.72rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;padding:4px 12px;border-radius:20px;margin-bottom:14px;}
.ir-card{background:#0f1322;border:1px solid #1e2540;border-radius:12px;padding:20px;margin-bottom:12px;}
.ir-title{color:#e8ecff;font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:600;margin-bottom:6px;}
.ir-desc{color:#6b7399;font-size:0.82rem;line-height:1.6;}
.formula-box{background:#050810;border:1px solid #1e2540;border-left:3px solid #3b82f6;border-radius:8px;padding:14px 18px;font-family:'Courier New',monospace;font-size:0.82rem;color:#93c5fd;margin:8px 0;}
.posting-badge{display:inline-block;background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.3);color:#34d399;font-size:0.75rem;padding:2px 8px;border-radius:10px;margin:2px;}
#MainMenu,footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

CHART_BG   = "#080b14"
TEXT_COLOR = "#8b93b8"
FONT_FAMILY= "Inter, sans-serif"
BASE_LAYOUT= dict(
    paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
    font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=12),
    margin=dict(t=48,b=36,l=36,r=16),
    title_font=dict(size=15,family="Space Grotesk, sans-serif",color="#d4d8e8"),
    hoverlabel=dict(bgcolor="#0f1322",bordercolor="#1e2540",
                    font_family=FONT_FAMILY,font_color="#d4d8e8"),
    xaxis=dict(showgrid=False,zeroline=False,color=TEXT_COLOR),
    yaxis=dict(showgrid=False,zeroline=False,color=TEXT_COLOR),
)
PLOTLY_CONFIG = {"displayModeBar":False,"responsive":True}
SEQ_BLUE  = ["#0d1b4b","#1e40af","#3b82f6","#93c5fd","#dbeafe"]
SEQ_TEAL  = ["#0f2d2d","#0f766e","#14b8a6","#5eead4","#ccfbf1"]
DISC_COLORS = ["#3b82f6","#06b6d4","#8b5cf6","#f59e0b","#10b981","#ef4444"]
PLATFORM_COLORS = {"Freelancer.com":"#3b82f6","Mostaqel.com":"#06b6d4"}


def apply_layout(fig, overrides=None):
    layout = dict(BASE_LAYOUT)
    if overrides:
        for k,v in overrides.items():
            if k in layout and isinstance(layout[k],dict) and isinstance(v,dict):
                merged = dict(layout[k]); merged.update(v); layout[k] = merged
            else:
                layout[k] = v
    fig.update_layout(**layout)
    return fig


# ===========================================================================
# DATA LOADING
# ===========================================================================
@st.cache_data(show_spinner="Loading data…")
def load_and_clean(path: str) -> pd.DataFrame:
    raw_path = Path(path)
    if not raw_path.exists():
        st.error(f"Cannot find **{path}**. Run `scraper.py` first.")
        st.stop()
    with open(raw_path, encoding="utf-8") as f:
        data = json.load(f)
    projects = data.get("projects", [])
    if not projects:
        st.warning("JSON exists but contains no projects.")
        st.stop()
    df = pd.DataFrame(projects)
    for col in ["platform","title","url","budget_currency","budget_type",
                "category","posted_date","description_snippet", "full_description"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    for col in ["budget_min","budget_max"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["budget_mid"] = df[["budget_min","budget_max"]].mean(axis=1)
    if "skills" in df.columns:
        def _to_list(v):
            if isinstance(v, list): return [s.strip() for s in v if str(s).strip()]
            if isinstance(v, str) and v: return [s.strip() for s in re.split(r"[,;|]",v) if s.strip()]
            return []
        df["skills"] = df["skills"].apply(_to_list)
        df["skills_count"] = df["skills"].apply(len)
    else:
        df["skills"] = [[] for _ in range(len(df))]
        df["skills_count"] = 0
    if "category" in df.columns:
        df["category"] = df["category"].replace("","Uncategorised")
    return df


@st.cache_data(show_spinner="Loading clean corpus…", hash_funcs={"builtins.list": id})
def load_clean_corpus(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, encoding="utf-8-sig")
    if "tokens" in df.columns:
        df["tokens_list"] = df["tokens"].fillna("").apply(
            lambda x: [t.strip() for t in x.split("|") if t.strip()])
    return df


def explode_skills(df):
    if "skills" not in df.columns:
        return pd.DataFrame(columns=["skill","platform"])
    exp = df[["platform","skills"]].explode("skills").dropna(subset=["skills"])
    exp = exp[exp["skills"].str.strip()!=""].rename(columns={"skills":"skill"})
    return exp


# ===========================================================================
# CHART BUILDERS (existing)
# ===========================================================================
def chart_top_skills(df_exp, n=12):
    counts = df_exp["skill"].value_counts().head(n).reset_index()
    counts.columns = ["skill","count"]
    fig = px.bar(counts,x="count",y="skill",orientation="h",text="count",
                 color="count",color_continuous_scale=SEQ_BLUE[::-1])
    fig.update_traces(textposition="outside",marker_line_width=0,
                      textfont=dict(color="#8b93b8",size=11))
    return apply_layout(fig,{"title":f"Top {n} Most In-Demand Skills",
        "yaxis":{"categoryorder":"total ascending"},
        "coloraxis_showscale":False,"height":460})


def chart_skills_by_platform(df_exp, n=10):
    fig = go.Figure()
    colors = list(PLATFORM_COLORS.values())
    for i,plat in enumerate(df_exp["platform"].unique()):
        sub = df_exp[df_exp["platform"]==plat]["skill"].value_counts().head(n).reset_index()
        sub.columns=["skill","count"]
        fig.add_trace(go.Bar(name=plat,x=sub["count"],y=sub["skill"],orientation="h",
            marker_color=colors[i%len(colors)],marker_line_width=0,
            text=sub["count"],textposition="outside",
            textfont=dict(color="#8b93b8",size=10)))
    fig.update_layout(barmode="group")
    return apply_layout(fig,{"title":"Top Skills by Platform",
        "yaxis":{"categoryorder":"total ascending"},"height":460,
        "legend":dict(bgcolor="rgba(0,0,0,0)",borderwidth=0)})


def chart_budget_histogram(df):
    budgets = df["budget_mid"].dropna()
    upper = budgets.quantile(0.99)
    budgets = budgets[budgets<=upper]
    fig = px.histogram(budgets,nbins=40,color_discrete_sequence=["#3b82f6"],opacity=0.85)
    fig.update_traces(marker_line_width=0.4,marker_line_color="#080b14")
    return apply_layout(fig,{"title":"Budget Distribution (mid-point, 99th pct cap)",
        "xaxis":{"title":"Budget"},"yaxis":{"title":"Projects"},
        "showlegend":False,"height":380})


def chart_budget_box(df):
    sub = df.dropna(subset=["budget_mid","platform"])
    upper = sub["budget_mid"].quantile(0.99)
    sub = sub[sub["budget_mid"]<=upper]
    fig = px.box(sub,x="platform",y="budget_mid",color="platform",
                 color_discrete_map=PLATFORM_COLORS,points="outliers",
                 labels={"platform":"Platform","budget_mid":"Budget"})
    fig.update_traces(marker_size=3)
    return apply_layout(fig,{"title":"Budget Spread by Platform",
        "showlegend":False,"height":360})


def chart_budget_type_pie(df):
    counts = df["budget_type"].value_counts().reset_index()
    counts.columns=["type","count"]
    fig = px.pie(counts,names="type",values="count",hole=0.58,
                 color_discrete_sequence=DISC_COLORS)
    fig.update_traces(textposition="outside",textinfo="label+percent",
        pull=[0.04]*len(counts),marker=dict(line=dict(color="#080b14",width=2)))
    return apply_layout(fig,{"title":"Budget Type Split","showlegend":True,
        "legend":dict(bgcolor="rgba(0,0,0,0)",borderwidth=0),"height":360})


def chart_projects_per_platform(df):
    counts = df["platform"].value_counts().reset_index()
    counts.columns=["platform","count"]
    colors=[PLATFORM_COLORS.get(p,"#8b5cf6") for p in counts["platform"]]
    fig = go.Figure(go.Bar(x=counts["platform"],y=counts["count"],
        marker_color=colors,marker_line_width=0,text=counts["count"],
        textposition="outside",textfont=dict(color="#8b93b8")))
    return apply_layout(fig,{"title":"Projects per Platform",
        "yaxis":{"title":"Number of Projects"},"showlegend":False,"height":320})


def chart_top_categories(df, n=12):
    sub = df[(df["category"].str.strip()!="")&(df["category"]!="Uncategorised")]
    counts = sub["category"].value_counts().head(n).reset_index()
    counts.columns=["category","count"]
    fig = px.bar(counts,x="count",y="category",orientation="h",text="count",
                 color="count",color_continuous_scale=SEQ_TEAL[::-1])
    fig.update_traces(textposition="outside",marker_line_width=0,
                      textfont=dict(color="#8b93b8",size=11))
    return apply_layout(fig,{"title":f"Top {n} Project Categories",
        "yaxis":{"categoryorder":"total ascending"},
        "coloraxis_showscale":False,"height":460})


def chart_skills_per_project(df):
    counts = df["skills_count"].value_counts().sort_index().reset_index()
    counts.columns=["skills_count","projects"]
    fig = px.bar(counts,x="skills_count",y="projects",color="projects",
                 color_continuous_scale=SEQ_BLUE[::-1],
                 labels={"skills_count":"Skills per Project","projects":"# Projects"})
    fig.update_traces(marker_line_width=0)
    return apply_layout(fig,{"title":"Skills per Project Distribution",
        "coloraxis_showscale":False,"height":320})


def chart_category_budget(df, n=10):
    sub = df[(df["category"]!="Uncategorised")&df["budget_mid"].notna()]
    top_cats = sub["category"].value_counts().head(n).index.tolist()
    sub = sub[sub["category"].isin(top_cats)]
    upper = sub["budget_mid"].quantile(0.99)
    sub = sub[sub["budget_mid"]<=upper]
    avg = sub.groupby("category")["budget_mid"].median().sort_values(ascending=False).reset_index()
    avg.columns=["category","median_budget"]
    fig = px.bar(avg,x="median_budget",y="category",orientation="h",
                 text=avg["median_budget"].map(lambda x: f"${x:,.0f}"),
                 color="median_budget",color_continuous_scale=SEQ_TEAL[::-1])
    fig.update_traces(textposition="outside",marker_line_width=0,
                      textfont=dict(color="#8b93b8",size=11))
    return apply_layout(fig,{"title":"Median Budget by Category (Top 10)",
        "xaxis":{"title":"Median Budget ($)"},
        "yaxis":{"categoryorder":"total ascending"},
        "coloraxis_showscale":False,"height":400})


# ===========================================================================
# IR ENGINE  (built from clean corpus)
# ===========================================================================
@st.cache_data(show_spinner="Building IR index…")
def build_ir_structures(df_clean: pd.DataFrame):
    """Build inverted index, positional index, and TF-IDF matrix."""
    if df_clean.empty or "tokens_list" not in df_clean.columns:
        return {}, {}, {}, [], [], []

    docs      = df_clean["tokens_list"].tolist()
    doc_ids   = df_clean.index.tolist()
    titles    = df_clean.get("title_clean", pd.Series([""] * len(df_clean))).tolist()
    descs     = df_clean.get("full_description", pd.Series([""] * len(df_clean))).tolist()
    N         = len(docs)

    # ── Inverted Index: term -> {doc_id: count} ──────────────────────────
    inv_index = defaultdict(lambda: defaultdict(int))
    for doc_id, tokens in zip(doc_ids, docs):
        for tok in tokens:
            inv_index[tok][doc_id] += 1

    # ── Positional Index: term -> {doc_id: [positions]} ──────────────────
    pos_index = defaultdict(lambda: defaultdict(list))
    for doc_id, tokens in zip(doc_ids, docs):
        for pos, tok in enumerate(tokens):
            pos_index[tok][doc_id].append(pos)

    # ── TF-IDF (manual implementation matching slide formulas) ────────────
    # TF(t,d) = count(t in d) / |d|
    # IDF(t)  = log(N / df(t))
    # TF-IDF  = TF * IDF
    tfidf = {}   # doc_id -> {term: score}
    for doc_id, tokens in zip(doc_ids, docs):
        if not tokens:
            continue
        tf_raw = defaultdict(int)
        for t in tokens:
            tf_raw[t] += 1
        doc_len = len(tokens)
        scores = {}
        for term, cnt in tf_raw.items():
            tf  = cnt / doc_len
            df  = len(inv_index[term])
            idf = math.log(N / df) if df else 0
            scores[term] = round(tf * idf, 6)
        tfidf[doc_id] = scores

    return dict(inv_index), dict(pos_index), tfidf, doc_ids, titles, descs


def query_tfidf(query: str, tfidf: dict, doc_ids: list,
                titles: list, top_k: int = 10) -> list:
    """Rank documents by summed TF-IDF score for query terms."""
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    scores = defaultdict(float)
    for doc_id in doc_ids:
        doc_scores = tfidf.get(doc_id, {})
        for term in terms:
            scores[doc_id] += doc_scores.get(term, 0.0)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for doc_id, score in ranked[:top_k]:
        if score > 0:
            idx = doc_ids.index(doc_id) if doc_id in doc_ids else -1
            results.append({
                "doc_id": doc_id,
                "title":  titles[idx] if 0 <= idx < len(titles) else str(doc_id),
                "score":  round(score, 5),
            })
    return results


def phrase_query(phrase: str, pos_index: dict, doc_ids: list,
                 titles: list, descs: list) -> list:
    """Find documents where all phrase tokens appear consecutively."""
    words = [w.strip().lower() for w in phrase.split() if w.strip()]
    if not words:
        return []
    candidate_docs = set(pos_index.get(words[0], {}).keys())
    for w in words[1:]:
        candidate_docs &= set(pos_index.get(w, {}).keys())
    results = []
    for doc_id in candidate_docs:
        positions_w0 = pos_index[words[0]][doc_id]
        for start_pos in positions_w0:
            if all(
                start_pos + offset in pos_index.get(words[offset], {}).get(doc_id, [])
                for offset in range(1, len(words))
            ):
                idx = doc_ids.index(doc_id) if doc_id in doc_ids else -1
                results.append({
                    "doc_id":   doc_id,
                    "title":    titles[idx] if 0 <= idx < len(titles) else str(doc_id),
                    "position": start_pos,
                    "desc":     descs[idx] if 0 <= idx < len(descs) else ""
                })
                break
    return results[:20]


# ===========================================================================
# TAB 4: IR STRATEGIES
# ===========================================================================
def render_ir_strategies(df_clean, inv_index, pos_index, tfidf, doc_ids, titles):
    st.markdown("<div class='section-badge'>Information Retrieval Strategies</div>",
                unsafe_allow_html=True)

    sub1, sub2, sub3, sub4, sub5 = st.tabs([
        "📋 General & Inverted Index",
        "📍 Positional Index",
        "🔲 TDIM",
        "📐 Vector Space Model",
        "🔮 LSA",
    ])

    # ── General Indexing ──────────────────────────────────────────────────
    with sub1:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>General Indexing</div>
<div class='ir-desc'>
The process of analyzing documents to identify key terms or phrases and recording
their locations to enable faster search and retrieval. Our corpus of <strong>750 freelance
project records</strong> is indexed by tokenizing titles, descriptions, skills, and categories
after the full IR preprocessing pipeline (noise reduction → Arabic normalization →
stop-word removal → tokenization).
</div></div>""", unsafe_allow_html=True)

        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Inverted Index — Maps Terms → Document Frequency + Posting List</div>
<div class='ir-desc'>An inverted index maps each unique term to the list of documents
(posting list) that contain it, along with the term frequency in each document.</div>
</div>""", unsafe_allow_html=True)

        if inv_index:
            term_input = st.text_input("🔍 Look up a term in the Inverted Index",
                                       value="python", key="inv_term")
            term_lower = term_input.strip().lower()
            if term_lower and term_lower in inv_index:
                postings = inv_index[term_lower]
                df_val = sum(postings.values())
                st.markdown(f"""
<div class='formula-box'>
Term: <strong>{term_lower}</strong><br>
Document Frequency (DF): <strong>{len(postings)}</strong> documents<br>
Total Term Frequency:    <strong>{df_val}</strong> occurrences
</div>""", unsafe_allow_html=True)
                posting_html = " ".join(
                    f"<span class='posting-badge'>doc {d} (tf={c})</span>"
                    for d, c in list(postings.items())[:30])
                st.markdown(f"**Posting List** (first 30): {posting_html}",
                            unsafe_allow_html=True)

                top_terms = sorted(inv_index.items(),
                                   key=lambda x: len(x[1]), reverse=True)[:15]
                df_chart = pd.DataFrame(
                    {"term": [t for t,_ in top_terms],
                     "doc_freq": [len(p) for _,p in top_terms]})
                fig = px.bar(df_chart, x="doc_freq", y="term", orientation="h",
                             color="doc_freq", color_continuous_scale=SEQ_BLUE[::-1],
                             text="doc_freq")
                fig.update_traces(textposition="outside", marker_line_width=0)
                apply_layout(fig, {"title": "Top 15 Terms by Document Frequency",
                                   "yaxis": {"categoryorder": "total ascending"},
                                   "coloraxis_showscale": False, "height": 420})
                st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
            elif term_lower:
                st.info(f"Term **'{term_lower}'** not found in index.")
        else:
            st.info("Load `data_after_cleaning.csv` to enable IR index features.")

    # ── Positional Index ──────────────────────────────────────────────────
    with sub2:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Positional Indexing</div>
<div class='ir-desc'>
An advanced method that stores each term, its document frequency, and the
<strong>exact position offsets</strong> within each document. This enables phrase queries
(exact word sequences) that a basic inverted index cannot support.
<br><br>Format: <code>term → {doc_id: [pos1, pos2, ...]}</code>
</div></div>""", unsafe_allow_html=True)

        if pos_index:
            pt = st.text_input("🔍 Look up positional postings", value="react",
                               key="pos_term")
            pt_lower = pt.strip().lower()
            if pt_lower and pt_lower in pos_index:
                postings = pos_index[pt_lower]
                rows = [{"doc_id": d, "positions": str(p[:10]),
                         "occurrences": len(p)}
                        for d, p in list(postings.items())[:20]]
                st.dataframe(pd.DataFrame(rows), width='stretch')
            elif pt_lower:
                st.info(f"Term **'{pt_lower}'** not found in positional index.")

    # ── TDIM ─────────────────────────────────────────────────────────────
    with sub3:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Term-Document Incidence Matrix (TDIM)</div>
<div class='ir-desc'>
A binary matrix tracking the <strong>presence (1) or absence (0)</strong> of terms
in documents. Steps: tokenize documents, remove duplicates, mark presence per document.
Shown below for the top terms × a sample of 15 documents.
</div></div>""", unsafe_allow_html=True)

        if inv_index and doc_ids:
            top_terms_tdim = [t for t, _ in sorted(
                inv_index.items(), key=lambda x: len(x[1]), reverse=True)[:20]]
            sample_docs = doc_ids[:15]
            matrix = []
            for term in top_terms_tdim:
                row = [1 if d in inv_index.get(term, {}) else 0
                       for d in sample_docs]
                matrix.append(row)
            fig = go.Figure(go.Heatmap(
                z=matrix, x=[f"D{d}" for d in sample_docs],
                y=top_terms_tdim,
                colorscale=[[0, "#080b14"], [1, "#3b82f6"]],
                showscale=False,
                text=matrix, texttemplate="%{text}",
                hovertemplate="Term: %{y}<br>Doc: %{x}<br>Present: %{z}<extra></extra>",
            ))
            apply_layout(fig, {"title": "TDIM — Top 20 Terms × 15 Documents",
                               "height": 540,
                               "xaxis": {"side": "top"}})
            st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)

    # ── VSM ───────────────────────────────────────────────────────────────
    with sub4:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Vector Space Model (VSM)</div>
<div class='ir-desc'>
Documents and queries are represented as <strong>TF-IDF weighted vectors</strong> in a
high-dimensional term space. Similarity between a query and a document is computed as
the cosine of the angle between their vectors.
</div></div>""", unsafe_allow_html=True)
        st.markdown("""
<div class='formula-box'>
TF(t,d) = count(t in d) / |d|<br>
IDF(t)  = log( N / DF(t) )<br>
TF-IDF(t,d) = TF(t,d) × IDF(t)<br><br>
cosine_sim(q, d) = (q · d) / (||q|| × ||d||)
</div>""", unsafe_allow_html=True)

        if tfidf and doc_ids:
            sample_id = doc_ids[0]
            vec = tfidf.get(sample_id, {})
            top_vec = sorted(vec.items(), key=lambda x: x[1], reverse=True)[:12]
            if top_vec:
                df_vec = pd.DataFrame(top_vec, columns=["term", "tfidf"])
                fig = px.bar(df_vec, x="tfidf", y="term", orientation="h",
                             color="tfidf", color_continuous_scale=SEQ_TEAL[::-1],
                             text=df_vec["tfidf"].map(lambda v: f"{v:.4f}"))
                fig.update_traces(textposition="outside", marker_line_width=0)
                apply_layout(fig, {"title": f"TF-IDF Vector — Document {sample_id}",
                                   "yaxis": {"categoryorder": "total ascending"},
                                   "coloraxis_showscale": False, "height": 380})
                st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)

    # ── LSA ───────────────────────────────────────────────────────────────
    with sub5:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Latent Semantic Analysis (LSA)</div>
<div class='ir-desc'>
LSA applies <strong>Singular Value Decomposition (SVD)</strong> to the TF-IDF matrix,
reducing it to a lower-dimensional semantic space. This allows the search engine to
understand <em>conceptual similarity</em> rather than exact term matching — e.g., finding
that "React" and "frontend development" are semantically related.
<br><br>
<strong>Steps:</strong><br>
1. Build TF-IDF matrix  M (terms × documents)<br>
2. Decompose: M = U · Σ · Vᵀ<br>
3. Keep top-k singular values (k=50 by default)<br>
4. Project queries and documents into the reduced semantic space<br>
5. Rank by cosine similarity in that space
</div></div>""", unsafe_allow_html=True)

        try:
            from sklearn.decomposition import TruncatedSVD
            from sklearn.feature_extraction.text import TfidfVectorizer
            if not df_clean.empty and "tokens_list" in df_clean.columns:
                corpus = df_clean["tokens_list"].apply(lambda x: " ".join(x)).tolist()
                corpus = [c for c in corpus if c.strip()]
                if len(corpus) >= 10:
                    with st.spinner("Running SVD…"):
                        vec_lsa = TfidfVectorizer(max_features=500, min_df=2)
                        X = vec_lsa.fit_transform(corpus)
                        k = min(50, X.shape[1] - 1, X.shape[0] - 1)
                        svd = TruncatedSVD(n_components=k, random_state=42)
                        X_r = svd.fit_transform(X)
                        ev = svd.explained_variance_ratio_[:20]
                    df_ev = pd.DataFrame({"component": range(1, len(ev)+1),
                                          "explained_variance": ev})
                    fig = px.bar(df_ev, x="component", y="explained_variance",
                                 color="explained_variance",
                                 color_continuous_scale=SEQ_TEAL[::-1])
                    fig.update_traces(marker_line_width=0)
                    apply_layout(fig, {
                        "title": f"LSA — Explained Variance (k={k} components, top 20 shown)",
                        "xaxis": {"title": "Semantic Component"},
                        "yaxis": {"title": "Explained Variance Ratio"},
                        "coloraxis_showscale": False, "height": 360})
                    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
                    st.success(f"LSA decomposed {X.shape[0]} docs × {X.shape[1]} terms "
                               f"into {k} semantic components. "
                               f"Top 20 components explain "
                               f"{sum(ev)*100:.1f}% of variance.")
        except ImportError:
            st.info("scikit-learn not installed. Run: pip install scikit-learn")
        except Exception as exc:
            st.warning(f"LSA error: {exc}")


# ===========================================================================
# TAB 5: TF-IDF EXPLORER
# ===========================================================================
def render_tfidf_explorer(df_clean, inv_index, pos_index, tfidf, doc_ids, titles, descs):
    st.markdown("<div class='section-badge'>TF-IDF Interactive Explorer</div>",
                unsafe_allow_html=True)

    st.markdown("""
<div class='ir-card'>
<div class='ir-title'>TF-IDF Formulas</div>
<div class='formula-box'>
TF(t,d)  =  (Number of times term t appears in document d) / (Total terms in d)<br><br>
IDF(t)   =  log( N / DF(t) )   where N = total documents, DF = docs containing t<br><br>
TF-IDF(t,d)  =  TF(t,d) × IDF(t)
</div>
<div class='ir-desc'>Higher TF-IDF = term is frequent in this doc but rare across the corpus → highly relevant signal.</div>
</div>""", unsafe_allow_html=True)

    ex1, ex2, ex3 = st.tabs(["🔎 Term Query", "💬 Phrase Query", "📊 TF/IDF Breakdown"])

    # ── Term Query ────────────────────────────────────────────────────────
    with ex1:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Term Query — AND / OR Search</div>
<div class='ir-desc'>
Searches for documents containing specific individual words.
Enter multiple words for AND (all terms) or OR (any term) search.
Ranked by cumulative TF-IDF score.
</div></div>""", unsafe_allow_html=True)

        col_q, col_mode = st.columns([3, 1])
        with col_q:
            term_query_input = st.text_input("Enter search terms",
                                             value="python django api",
                                             key="term_query_inp")
        with col_mode:
            query_mode = st.radio("Mode", ["OR (any)", "AND (all)"], key="qmode")

        if term_query_input.strip() and tfidf:
            terms = [t.strip().lower() for t in term_query_input.split() if t.strip()]
            scores = defaultdict(float)
            for doc_id in doc_ids:
                doc_vec = tfidf.get(doc_id, {})
                if query_mode == "AND (all)":
                    if all(t in doc_vec for t in terms):
                        for t in terms:
                            scores[doc_id] += doc_vec.get(t, 0)
                else:
                    for t in terms:
                        scores[doc_id] += doc_vec.get(t, 0)

            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
            if ranked and ranked[0][1] > 0:
                rows = []
                for doc_id, score in ranked:
                    idx = doc_ids.index(doc_id) if doc_id in doc_ids else -1
                    t_title = titles[idx] if 0 <= idx < len(titles) else str(doc_id)
                    rows.append({"Rank": len(rows)+1, "Doc ID": doc_id,
                                 "Title (cleaned)": t_title[:60],
                                 "TF-IDF Score": round(score, 5)})
                df_res = pd.DataFrame(rows)
                st.dataframe(df_res, width='stretch')

                st.markdown("#### Search Results Preview")
                for doc_id, score in ranked[:5]:
                    idx = doc_ids.index(doc_id) if doc_id in doc_ids else -1
                    t_title = titles[idx] if 0 <= idx < len(titles) else str(doc_id)
                    t_desc = str(descs[idx] if 0 <= idx < len(descs) else "")
                    
                    highlighted_desc = t_desc
                    for t in terms:
                        highlighted_desc = re.sub(f"(?i)({re.escape(t)})", r"<mark style='background-color:#3b82f6;color:white;border-radius:3px;padding:0 2px;'>\1</mark>", highlighted_desc)
                    
                    st.markdown(f"""
                    <div style='background:#0f1322;border:1px solid #1e2540;border-radius:8px;padding:12px;margin-bottom:8px;'>
                        <div style='color:#60a5fa;font-weight:600;margin-bottom:4px;'>{t_title} (Score: {score:.4f})</div>
                        <div style='color:#d4d8e8;font-size:0.85rem;line-height:1.5;'>{highlighted_desc[:800]}...</div>
                    </div>
                    """, unsafe_allow_html=True)

                fig = px.bar(df_res, x="TF-IDF Score", y="Title (cleaned)",
                             orientation="h", color="TF-IDF Score",
                             color_continuous_scale=SEQ_BLUE[::-1],
                             text="TF-IDF Score")
                fig.update_traces(textposition="outside", marker_line_width=0,
                                  textfont=dict(size=10, color="#8b93b8"))
                apply_layout(fig, {"title": f"Top 10 Results for: '{term_query_input}'",
                                   "yaxis": {"categoryorder": "total ascending"},
                                   "coloraxis_showscale": False, "height": 400})
                st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
            else:
                st.info("No matching documents found.")
        elif not tfidf:
            st.info("Load `data_after_cleaning.csv` to enable search.")

    # ── Phrase Query ──────────────────────────────────────────────────────
    with ex2:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>Phrase Query — Exact Sequence Search</div>
<div class='ir-desc'>
Searches for a <strong>specific sequence of words</strong> appearing in the exact same order
within a document. Uses the Positional Index to verify consecutive positions.
<br>Example: "machine learning" only matches docs where these words appear adjacent.
</div></div>""", unsafe_allow_html=True)

        phrase_input = st.text_input("Enter exact phrase", value="machine learning",
                                     key="phrase_inp")
        if phrase_input.strip() and pos_index:
            results = phrase_query(phrase_input, pos_index, doc_ids, titles, descs)
            if results:
                st.success(f"Found **{len(results)}** document(s) containing "
                           f"the phrase **'{phrase_input}'**")
                
                df_res = pd.DataFrame([{k:v for k,v in r.items() if k != 'desc'} for r in results])
                st.dataframe(df_res, width='stretch')
                
                st.markdown("#### Phrase Match Previews")
                for r in results[:5]:
                    t_title = r["title"]
                    t_desc = str(r["desc"])
                    
                    phrase_esc = re.escape(phrase_input)
                    highlighted_desc = re.sub(f"(?i)({phrase_esc})", r"<mark style='background-color:#10b981;color:white;border-radius:3px;padding:0 2px;'>\1</mark>", t_desc)
                    
                    st.markdown(f"""
                    <div style='background:#0f1322;border:1px solid #1e2540;border-radius:8px;padding:12px;margin-bottom:8px;'>
                        <div style='color:#34d399;font-weight:600;margin-bottom:4px;'>{t_title}</div>
                        <div style='color:#d4d8e8;font-size:0.85rem;line-height:1.5;'>{highlighted_desc[:800]}...</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"Phrase **'{phrase_input}'** not found in any document.")
        elif not pos_index:
            st.info("Load `data_after_cleaning.csv` to enable phrase search.")

    # ── TF / IDF Breakdown ────────────────────────────────────────────────
    with ex3:
        st.markdown("""
<div class='ir-card'>
<div class='ir-title'>TF / IDF / TF-IDF Breakdown for a Single Term</div>
<div class='ir-desc'>
Enter a term and a document ID to see the exact TF, IDF, and TF-IDF values
computed by the formulas above.
</div></div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            bd_term = st.text_input("Term", value="react", key="bd_term")
        with c2:
            bd_doc  = st.number_input("Document ID", value=0, min_value=0,
                                      max_value=max(doc_ids) if doc_ids else 0,
                                      key="bd_doc")

        if bd_term.strip() and tfidf and inv_index:
            t = bd_term.strip().lower()
            N = len(doc_ids)
            df_t = len(inv_index.get(t, {}))
            doc_vec = tfidf.get(bd_doc, {})

            # Recompute for display
            doc_tokens_df = df_clean[df_clean.index == bd_doc]
            if not doc_tokens_df.empty:
                tok_list = doc_tokens_df.iloc[0].get("tokens_list", [])
                doc_len  = len(tok_list) if tok_list else 1
                tf_cnt   = tok_list.count(t) if tok_list else 0
                tf_val   = tf_cnt / doc_len if doc_len else 0
            else:
                tf_val = 0.0; tf_cnt = 0; doc_len = 1

            idf_val    = math.log(N / df_t) if df_t > 0 else 0
            tfidf_val  = tf_val * idf_val

            st.markdown(f"""
<div class='formula-box'>
Term: <strong>{t}</strong> | Document ID: <strong>{bd_doc}</strong><br><br>
TF({t}, d{bd_doc})  =  {tf_cnt} / {doc_len}  =  <strong>{tf_val:.6f}</strong><br>
IDF({t})            =  log({N} / {df_t})      =  <strong>{idf_val:.6f}</strong><br>
TF-IDF({t}, d{bd_doc}) =  {tf_val:.4f} × {idf_val:.4f}  =  <strong>{tfidf_val:.6f}</strong>
</div>""", unsafe_allow_html=True)

            if df_t > 0:
                sample_docs_bd = list(inv_index[t].keys())[:20]
                rows_bd = []
                for did in sample_docs_bd:
                    dv = tfidf.get(did, {})
                    rows_bd.append({"doc_id": did, "TF-IDF": round(dv.get(t, 0), 5)})
                df_bd = pd.DataFrame(rows_bd).sort_values("TF-IDF", ascending=False)
                fig = px.bar(df_bd, x="doc_id", y="TF-IDF",
                             color="TF-IDF", color_continuous_scale=SEQ_BLUE[::-1])
                fig.update_traces(marker_line_width=0)
                apply_layout(fig, {
                    "title": f"TF-IDF score for '{t}' across sample documents",
                    "coloraxis_showscale": False, "height": 320})
                st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)


# ===========================================================================
# MAIN APP
# ===========================================================================
def main():
    df   = load_and_clean(FILE_JSON)
    df_clean = load_clean_corpus(FILE_CLEAN)
    df_skills = explode_skills(df)

    # Build IR structures from clean corpus
    inv_index, pos_index, tfidf, doc_ids, titles, descs = build_ir_structures(df_clean)

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown("""
<div style='padding:28px 0 4px 0;'>
  <h1 style='font-family:"Space Grotesk",sans-serif;font-size:2.4rem;
             font-weight:700;margin:0;color:#e8ecff;letter-spacing:-0.02em;'>
    Sha8lny Welnaby
    <span style='color:#3b82f6;'> · Freelance Market Explorer</span>
  </h1>
  <p style='color:#3d4569;font-size:0.82rem;margin-top:8px;letter-spacing:0.06em;'>
    CS313x INFORMATION RETRIEVAL &nbsp;·&nbsp;
    DATA SOURCE: FREELANCER.COM &amp; MOSTAQEL.COM
  </p>
</div>
<hr style='border:none;border-top:1px solid #1e2540;margin:8px 0 24px 0;'>
""", unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## Filters")
        platforms = ["All"] + sorted(df["platform"].unique().tolist())
        selected_platform = st.selectbox("Platform", platforms)
        budget_types = ["All"] + sorted(df["budget_type"].unique().tolist())
        selected_btype = st.selectbox("Budget Type", budget_types)
        st.markdown("---")
        st.caption(f"Data file: `{FILE_JSON}`")
        st.caption(f"Total raw rows: {len(df):,}")
        if not df_clean.empty:
            st.caption(f"Clean corpus: {len(df_clean):,} docs")
            st.caption(f"Index terms: {len(inv_index):,}")

    # ── Apply filters ────────────────────────────────────────────────────────
    fdf = df.copy()
    if selected_platform != "All":
        fdf = fdf[fdf["platform"] == selected_platform]
    if selected_btype != "All":
        fdf = fdf[fdf["budget_type"] == selected_btype]
    fdf_skills = explode_skills(fdf)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_projects  = len(fdf)
    avg_budget      = fdf["budget_mid"].mean()
    median_budget   = fdf["budget_mid"].median()
    pct_with_budget = (fdf["budget_mid"].notna().sum() / max(total_projects, 1)) * 100
    unique_skills   = fdf_skills["skill"].nunique() if not fdf_skills.empty else 0
    platform_count  = fdf["platform"].nunique()

    kpis = [
        ("Total Projects",  f"{total_projects:,}"),
        ("Platforms",       f"{platform_count}"),
        ("Avg Budget",      f"${avg_budget:,.0f}" if pd.notna(avg_budget) else "N/A"),
        ("Median Budget",   f"${median_budget:,.0f}" if pd.notna(median_budget) else "N/A"),
        ("Budget Coverage", f"{pct_with_budget:.0f}%"),
        ("Unique Skills",   f"{unique_skills:,}"),
    ]
    cols = st.columns(6)
    for col, (label, value) in zip(cols, kpis):
        with col:
            st.markdown(f"""
<div class='kpi-card'>
  <div class='kpi-value'>{value}</div>
  <div class='kpi-label'>{label}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🛠  Skills Analysis",
        "💰  Budget Insights",
        "📂  Categories",
        "🔬  IR Strategies",
        "📐  TF-IDF Explorer",
        "🗄  Raw Data",
    ])

    with tab1:
        st.markdown("<div class='section-badge'>Skills Overview</div>",
                    unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            if not fdf_skills.empty:
                st.plotly_chart(chart_top_skills(fdf_skills),
                                width='stretch', config=PLOTLY_CONFIG)
            else:
                st.info("No skill data available.")
        with c2:
            st.plotly_chart(chart_projects_per_platform(fdf),
                            width='stretch', config=PLOTLY_CONFIG)
            st.plotly_chart(chart_skills_per_project(fdf),
                            width='stretch', config=PLOTLY_CONFIG)
        if len(fdf["platform"].unique()) > 1:
            with st.expander("Skills by Platform Comparison", expanded=False):
                st.plotly_chart(chart_skills_by_platform(fdf_skills),
                                width='stretch', config=PLOTLY_CONFIG)

    with tab2:
        st.markdown("<div class='section-badge'>Budget Analysis</div>",
                    unsafe_allow_html=True)
        has_budget = fdf["budget_mid"].notna().sum() > 0
        if has_budget:
            b1, b2 = st.columns(2)
            with b1:
                st.plotly_chart(chart_budget_histogram(fdf),
                                width='stretch', config=PLOTLY_CONFIG)
            with b2:
                st.plotly_chart(chart_budget_type_pie(fdf),
                                width='stretch', config=PLOTLY_CONFIG)
            if len(fdf["platform"].unique()) > 1:
                st.plotly_chart(chart_budget_box(fdf),
                                width='stretch', config=PLOTLY_CONFIG)
        else:
            st.info("No numeric budget data for current filter.")

    with tab3:
        st.markdown("<div class='section-badge'>Category Breakdown</div>",
                    unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(chart_top_categories(fdf),
                            width='stretch', config=PLOTLY_CONFIG)
        with c4:
            if fdf["budget_mid"].notna().sum() > 0:
                st.plotly_chart(chart_category_budget(fdf),
                                width='stretch', config=PLOTLY_CONFIG)
            else:
                st.info("Budget data unavailable.")

    with tab4:
        render_ir_strategies(df_clean, inv_index, pos_index,
                             tfidf, doc_ids, titles)

    with tab5:
        render_tfidf_explorer(df_clean, inv_index, pos_index,
                              tfidf, doc_ids, titles, descs)

    with tab6:
        st.markdown("<div class='section-badge'>Sample Data</div>",
                    unsafe_allow_html=True)
        display_cols = [c for c in [
            "platform", "title", "budget_min", "budget_max",
            "budget_currency", "budget_type", "category",
            "posted_date", "skills_count",
        ] if c in fdf.columns]
        st.markdown(f"Showing **{min(50,len(fdf))}** of **{len(fdf):,}** filtered projects")
        st.dataframe(fdf[display_cols].head(50), width='stretch', height=400)
        with st.expander("Download filtered data as CSV"):
            csv = fdf[display_cols].to_csv(index=False)
            st.download_button(label="Download CSV", data=csv,
                               file_name="sha8lny_filtered.csv", mime="text/csv")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
<hr style='border:none;border-top:1px solid #1e2540;margin:40px 0 12px 0;'>
<p style='color:#2a3050;font-size:0.72rem;text-align:center;letter-spacing:0.08em;'>
  SHA8LNY WELNABY &nbsp;·&nbsp; CS313x Information Retrieval &nbsp;·&nbsp;
  Freelancer.com &amp; Mostaqel.com
</p>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
