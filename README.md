# Sha8lny Welnaby | شغلني ولنبي

**An Information Retrieval–powered freelance market intelligence platform** for monitoring and analyzing public project listings from [Freelancer.com](https://www.freelancer.com) and [Mostaqel.com](https://mostaql.com) (مستقل).

Built for **CS313x — Information Retrieval** as a full-stack application combining classical IR algorithms, semantic search, market analytics, and skill-to-job matching.

<p align="center">
  <a href="https://github.com/DavidNashaat19/project-sha8lny-welnaby">Repository</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#api-reference">API</a> ·
  <a href="#architecture">Architecture</a>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Running the Application](#running-the-application)
- [Data Pipeline](#data-pipeline)
- [Information Retrieval Engine](#information-retrieval-engine)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Updating the Dataset](#updating-the-dataset)
- [Troubleshooting](#troubleshooting)
- [Contributors](#contributors)

---

## Overview

**Sha8lny Welnaby** (Arabic: *شغلني ولنبي* — “Get me work and we’re good”) helps freelancers and researchers:

- **Search** thousands of tokenized project postings using TF-IDF, Boolean logic, phrase search, Vector Space Model, semantic embeddings, and hybrid ranking.
- **Analyze** market trends — top skills, platform distribution, budget patterns.
- **Match** a freelancer’s skill profile against open jobs with gap analysis and learning suggestions.
- **Explore** IR internals in a dedicated lab (inverted index, TF-IDF breakdown, VSM).

The current dataset contains **75 deep-crawled projects** (50 from Freelancer.com, 25 from Mostaqel.com), stored in `freelance_data.json`.

---

## Key Features

| Module | Description |
|--------|-------------|
| **Smart Search** | Multi-mode retrieval: TF-IDF, Hybrid (lexical + semantic), Semantic AI, Boolean, Phrase, VSM |
| **Market Analytics** | Interactive charts — skill demand, platform split, budget insights |
| **Skill Match** | Cosine similarity ranking, gap skills, suggested learning paths |
| **Resume Parser** | PDF upload → skill extraction via NER |
| **IR Lab** | Inspect inverted index postings, per-term TF-IDF, VSM scores |
| **Bilingual UI** | English / Arabic (i18n) with RTL-ready layout |
| **Market Insights** | AI-generated summaries for top search results |

---

## Architecture

```mermaid
flowchart TB
    subgraph Sources
        FL[Freelancer.com]
        MQ[Mostaqel.com]
    end

    subgraph Data
        SC[scraper_ManualSubmission.py]
        JSON[(freelance_data.json)]
    end

    subgraph Backend["FastAPI Backend :8000"]
        DL[data_loader.py]
        IX[Inverted Index]
        TF[TF-IDF / VSM / Boolean / Positional]
        SE[Semantic Engine]
        NER[NER Skill Extractor]
        API[/api/*]
    end

    subgraph Frontend["React + Vite :5173"]
        UI[Landing · Search · Analytics · Match · IR Lab]
    end

    FL --> SC
    MQ --> SC
    SC --> JSON
    JSON --> DL
    DL --> IX & TF & SE & NER
    IX & TF & SE --> API
    UI <-->|REST| API
```

---

## Tech Stack

### Backend
- **FastAPI** + **Uvicorn** — REST API
- **NLTK** — tokenization, stemming, stopwords (Arabic + English)
- **scikit-learn** — VSM / similarity utilities
- **sentence-transformers** — semantic embeddings
- **pandas**, **numpy** — analytics
- **PyPDF2** — resume parsing

### Frontend
- **React 19** + **Vite 8**
- **Tailwind CSS** + **Framer Motion**
- **Recharts** — analytics visualizations
- **react-i18next** — EN / AR localization
- **Zustand** — client state

### Data Collection
- **Selenium** deep crawler (`scraper_ManualSubmission.py`)
- **GitHub Actions** — automated scrape + preprocess pipeline (`.github/workflows/`)

---

## Repository Structure

```
project-sha8lny-welnaby/
├── freelance_data.json          # Primary dataset (75 projects)
├── scraper_ManualSubmission.py  # Freelancer + Mostaqel deep crawler
├── preprocess.py                # Standalone CSV preprocessor (legacy pipeline)
├── presentation.HTML            # Project presentation deck
│
├── phase2/
│   ├── requirements.txt         # Backend Python dependencies
│   ├── backend/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── data_loader.py       # JSON load + on-the-fly tokenization
│   │   ├── ir_engine.py         # Inverted index, TF-IDF, VSM, Boolean, Phrase
│   │   ├── semantic_engine.py   # Sentence-transformer semantic search
│   │   ├── analytics.py         # Market statistics
│   │   ├── match.py             # Freelancer–job matching
│   │   ├── ner_extractor.py     # Skill NER enrichment
│   │   ├── preprocess.py        # Text cleaning utilities
│   │   └── data/
│   │       └── freelance_data.json  # Synced copy for NER
│   │
│   └── frontend/
│       ├── src/pages/           # Landing, Search, Analytics, Match, IRLab
│       └── package.json
│
└── .github/workflows/           # CI scraper pipeline
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ (3.13 tested) |
| Node.js | 18+ |
| npm | 9+ |
| Git | Any recent version |

> **First backend startup** downloads the sentence-transformer model (~400 MB) and builds the semantic index (~30 seconds).

---

## Quick Start

### 1. Clone the repository

```cmd
git clone https://github.com/DavidNashaat19/project-sha8lny-welnaby.git
cd project-sha8lny-welnaby
```

### 2. Install dependencies (one time)

**Backend:**
```cmd
cd phase2
py -m pip install -r requirements.txt
cd ..
```

**Frontend:**
```cmd
cd phase2\frontend
npm install
cd ..\..
```

### 3. Sync dataset (recommended)

Ensure the backend NER module uses the same data as the root file:

```cmd
copy /Y freelance_data.json phase2\backend\data\freelance_data.json
```

---

## Running the Application

Use **two separate terminals**. Keep both running while using the app.

### Terminal 1 — Backend API

```cmd
cd phase2
py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

> **Important:** Run from the `phase2` folder, not `phase2\backend`.  
> The app uses package imports (`backend.main:app`).

**Success indicators:**
```
[DataLoader] Loading from: ...\freelance_data.json
Loaded 75 documents.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

- API docs: http://127.0.0.1:8000/docs  
- Health check: http://127.0.0.1:8000/api/search?per_page=1

### Terminal 2 — Frontend

```cmd
cd phase2\frontend
npm run dev
```

Open **http://localhost:5173/** in your browser.

| Page | URL |
|------|-----|
| Home | http://localhost:5173/ |
| Search | http://localhost:5173/search |
| Analytics | http://localhost:5173/analytics |
| Match | http://localhost:5173/match |
| IR Lab | http://localhost:5173/ir-lab |

---

## Data Pipeline

```
Freelancer.com + Mostaqel.com
        │
        ▼  scraper_ManualSubmission.py (Selenium deep crawl)
        │
freelance_data.json  (schema v2.0)
        │
        ▼  data_loader.py (clean_text_full + inverted index build)
        │
   FastAPI IR Engine  ──►  React Frontend
```

### Dataset schema (`freelance_data.json`)

```json
{
  "metadata": {
    "total_records": 75,
    "platforms": ["Freelancer.com", "Mostaqel.com"],
    "schema_version": "2.0"
  },
  "projects": [
    {
      "platform": "Freelancer.com",
      "title": "...",
      "url": "...",
      "budget_min": 10.0,
      "budget_max": 30.0,
      "budget_currency": "USD",
      "skills": ["..."],
      "full_description": "...",
      "description_snippet": "..."
    }
  ]
}
```

---

## Information Retrieval Engine

| Mode | Algorithm | Endpoint param |
|------|-----------|----------------|
| **TF-IDF** | Inverted index + BM25-style scoring (default) | `mode=tfidf` |
| **Hybrid** | Weighted lexical + semantic fusion | `mode=hybrid` |
| **Semantic** | Sentence-transformer cosine similarity | `mode=semantic` |
| **Boolean** | AND / OR / NOT query parser | `mode=boolean` |
| **Phrase** | Positional index phrase matching | `mode=phrase` |
| **VSM** | Vector Space Model cosine similarity | `mode=vsm` |

**Preprocessing pipeline** (`preprocess.py`):
- Lowercasing, punctuation removal
- Arabic + English stopword removal
- Porter stemming (English) + Arabic normalization
- On-the-fly tokenization at load time (no CSV required for runtime)

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search` | Search jobs (`q`, `mode`, `platform`, `budget_*`, `skills`, pagination) |
| `GET` | `/api/analytics` | Market stats (`platform` filter) |
| `POST` | `/api/match` | Match freelancer skills to jobs |
| `POST` | `/api/parse-resume` | Extract skills from PDF resume |
| `GET` | `/api/ir/index` | Inverted index lookup for a term |
| `GET` | `/api/ir/tfidf` | TF-IDF explanation for term + document |
| `POST` | `/api/ir/vsm` | Vector Space Model search |

**Example — search Mostaqel projects:**
```bash
curl "http://127.0.0.1:8000/api/search?platform=Mostaqel.com&per_page=5"
```

**Example — analytics:**
```bash
curl "http://127.0.0.1:8000/api/analytics?platform=all"
```

Interactive documentation: **http://127.0.0.1:8000/docs**

---

## Frontend Pages

| Route | Purpose |
|-------|---------|
| `/` | Landing — project overview, feature cards |
| `/search` | Job search with filters, relevance bars, IR breakdown |
| `/analytics` | Charts — skills, platforms, budgets |
| `/match` | Skill profile matching + gap analysis |
| `/ir-lab` | Educational IR tooling for course demonstration |

The UI connects to `http://localhost:8000` for all API calls.

---

## Updating the Dataset

1. Run the scraper (requires Chrome + Selenium):
   ```cmd
   py scraper_ManualSubmission.py
   ```
2. Copy the output to the backend data folder:
   ```cmd
   copy /Y freelance_data.json phase2\backend\data\freelance_data.json
   ```
3. Restart the backend server.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: attempted relative import` | Start uvicorn from `phase2/`, use `backend.main:app` |
| `pip` / `py` not found | Install Python and enable **Add to PATH** |
| Frontend shows network errors | Ensure backend is running on port **8000** |
| `Loaded 300 documents` instead of 75 | Root `freelance_data.json` missing; backend fell back to old data — restore root JSON |
| Platform filter returns nothing | Use exact values: `Freelancer.com`, `Mostaqel.com` (case-sensitive) |
| Slow first startup | Normal — semantic model download + index build |
| Port already in use | Change port: `--port 8001` |

---

## Production Build (optional)

**Frontend static build:**
```cmd
cd phase2\frontend
npm run build
npm run preview
```

Serve the `dist/` folder behind any static host; point API calls to your deployed backend URL.

---

## Contributors

**Course:** CS313x — Information Retrieval  

**Repository:** [DavidNashaat19/project-sha8lny-welnaby](https://github.com/DavidNashaat19/project-sha8lny-welnaby)

---

## License

This project was developed as an academic submission. Contact the repository owner for usage terms outside the course context.

---

<p align="center">
  <strong>Sha8lny Welnaby</strong> — Classical IR meets modern semantic search for the freelance economy.
</p>
