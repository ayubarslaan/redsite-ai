# RedSite AI — Mars Site Intelligence & Decision Engine

> **An explainable, mission-aware AI system for selecting safe and resource-rich human landing sites on Mars.**
> Built for the IBM AI Builders Challenge — August 2026.

[![Challenge](https://img.shields.io/badge/IBM%20AI%20Builders%20Challenge-August%202026-blue)]()
[![Theme](https://img.shields.io/badge/Theme-Advance%20Space%20Exploration%20with%20AI-orange)]()
[![Stack](https://img.shields.io/badge/Stack-Python%20%7C%20FastAPI%20%7C%20Next.js%20%7C%20IBM%20Granite-green)]()

---

## 🎯 Problem Statement

Humanity may eventually need to choose where to build its first permanent settlement on another planet. Mars spans **144.8 million km²** of heterogeneous terrain, subsurface ice, solar potential, and scientific value. NASA and commercial partners (SpaceX, Blue Origin) are actively evaluating candidate regions, but the process remains manual, siloed across datasets, and inaccessible to mission planners who need to weigh competing priorities.

**Key gaps:**
- No unified platform integrates elevation (MOLA), ice (SHARAD), imagery (HiRISE), and solar models
- No tool lets planners change mission priorities and watch rankings recalculate in real time
- No AI assistant explains *why* one site beats another using retrieved scientific evidence

---

## 💡 Solution Description

**RedSite AI** is a decision-support engine that:

1. **Ingests** real NASA planetary data (MOLA DEM, SHARAD ice, HiRISE terrain, solar insolation models)
2. **Scores** candidate sites using deterministic scientific calculations + ML terrain classification
3. **Optimizes** rankings based on user-defined mission profiles (settlement, science, resource extraction)
4. **Explains** results via an IBM Granite-powered AI analyst that answers natural language questions over structured site data

### Core Features

| Feature | Description |
|---------|-------------|
| 🗺️ **Interactive Mars Map** | 3D globe with toggleable data layers (elevation, ice, slope, solar, science) |
| 📊 **Mission-Aware Scoring** | Multi-criteria weighted model that recalculates when priorities change |
| 🔍 **Candidate Ranking** | Real-time leaderboard of 5+ validated sites with radar-chart breakdowns |
| 🤖 **Granite AI Analyst** | RAG-based assistant that explains rankings, compares sites, and flags risks |
| ⚡ **What-If Simulator** | Adjust weight sliders to see how rankings shift under different mission constraints |

---

## 🤖 AI Approach & Architecture

```
NASA Planetary Data
      │
      ├── MOLA DEM ──────────► Elevation / Slope / Terrain Safety
      ├── SHARAD ────────────► Subsurface Ice Proximity
      ├── HiRISE ────────────► Rock / Hazard Detection (CV)
      ├── CRISM ─────────────► Mineral / Scientific Value
      └── Solar Model ───────► Energy Potential by Latitude
                    │
                    ▼
             Feature Store (PostgreSQL + PostGIS)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
 Scientific Models          ML / CV Models
 (deterministic)            (terrain classification)
        │                       │
        └───────────┬───────────┘
                    ▼
            Site Suitability Scorer
            (weighted multi-criteria)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  Global Heatmap          Candidate Ranking
                                │
                                ▼
                      Mission Profile Optimizer
                                │
                                ▼
                      IBM Granite AI Analyst
                      (LangChain + watsonx.ai RAG)
                                │
                                ▼
                    Human-Readable Explanation
```

### AI Components

| Component | Technology | Role |
|-----------|-----------|------|
| **Terrain Classification** | PyTorch / Hugging Face | Classifies HiRISE imagery into safe/rocky/dune terrain |
| **Site Scoring** | Weighted multi-criteria algorithm | Deterministic scoring across 5 dimensions |
| **Mission Optimizer** | Constraint-based ranking | Recalculates rankings when user changes priorities |
| **AI Analyst** | IBM Granite (watsonx.ai) + LangChain | Natural language explanations, comparisons, risk assessment |
| **RAG Pipeline** | Vector DB (Chroma) + watsonx.ai | Retrieves NASA mission docs and scientific sources for grounded answers |

---

## 🏷️ Selected Challenge Theme

**Advance Space Exploration with AI** — Space operations and decision-support systems

RedSite AI directly addresses the challenge prompt:
> *"Build AI-powered solutions that help advance space exploration by improving mission success, enabling smarter decisions, and making space more accessible and understandable."*

It transforms Mars exploration from **data-heavy to insight-driven** by unifying disparate NASA datasets into a single decision engine with explainable AI.

---

## 🛠️ How IBM Bob Was Used

**IBM Bob is the primary development tool for this project.**

This repository includes:
- `docs/BOB_USAGE.md` — **Living log** of every Bob session (to be filled in as development progresses)
- `docs/BOB_SELF_LOGGING.md` — Instructions for having Bob generate its own usage evidence

### Evidence Approach

Rather than fabricating a log after the fact, we use this workflow:

1. **Use Bob to implement each feature** (backend, frontend, ML, docs)
2. **After each session, ask Bob to generate a log entry** using the self-logging prompt
3. **Append Bob's output to `docs/BOB_USAGE.md`**
4. **Commit with message referencing the Bob session**

This creates an **authentic, timestamped audit trail** where:
- The log entries are generated by Bob itself
- Git history proves when each entry was added
- The content matches actual code in the repository

### Target Metrics

| Metric | Target |
|--------|--------|
| Files generated by Bob | 14+ (backend, frontend, Docker, docs) |
| Bob-generated lines | ~2,000+ |
| Development sessions | 10–12 |
| Bobcoins consumed | ~150–200 |

> **See `docs/BOB_USAGE.md` for the actual session log** (populated throughout development).
> **See `docs/BOB_SELF_LOGGING.md` for the exact prompt to use after each session.**

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional)
- IBM watsonx.ai API key (for Granite analyst)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export WATSONX_API_KEY="your-key"
export WATSONX_PROJECT_ID="your-project-id"

# Run
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker (Full Stack)

```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
redsite-ai/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models.py            # Pydantic data models
│   ├── scoring.py           # Site scoring engine
│   ├── analyst.py           # IBM Granite AI analyst
│   ├── data_ingest.py       # NASA data pipeline
│   ├── terrain_cv.py        # HiRISE terrain classifier
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js app router
│   ├── components/          # React components
│   └── package.json
├── data/
│   └── sample_sites.json    # Pre-computed candidate sites
├── docs/
│   ├── ARCHITECTURE.md      # Detailed system design
│   ├── BOB_USAGE.md         # IBM Bob session log (LIVING DOCUMENT)
│   ├── BOB_SELF_LOGGING.md  # How to log Bob usage authentically
│   └── DATA_SOURCES.md      # NASA data source guide
├── README.md
└── docker-compose.yml
```

---

## 📡 Data Sources

All data is **publicly available** from NASA and USGS:

| Dataset | Source | URL |
|---------|--------|-----|
| MOLA DEM | NASA PDS / WUSTL ODE | https://ode.rsl.wustl.edu/mars/ |
| SHARAD | NASA PDS Geosciences | https://pds-geosciences.wustl.edu/missions/mro/sharad.htm |
| HiRISE | USGS Astrogeology STAC | https://stac.astrogeology.usgs.gov/docs/data/mars/uncontrolled_hirise/ |
| CRISM | NASA PDS | https://pds-geosciences.wustl.edu/missions/mro/crism.htm |
| Solar Model | Derived from MOLA latitude | Calculated in-app |

---

## 🎬 Demo Video

**[Watch the 3-minute demo →](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)**

The video covers:
1. **0:00–0:30** — Problem: Mars is vast, data is siloed, decisions are manual
2. **0:30–1:15** — Live demo: Interactive map, layer toggles, site selection
3. **1:15–2:00** — AI feature: Mission profile switch + Granite analyst explanation
4. **2:00–2:30** — Technical depth: Architecture, IBM Bob usage, data pipeline
5. **2:30–3:00** — Impact: Supports Artemis-scale Mars mission planning

---

## 👥 Team

| Name | Role |
|------|------|
| [Your Name] | Project Lead / Full-Stack Developer |
| [Teammate 2] | ML / Data Engineering |
| [Teammate 3] | Frontend / UX |

---

## 🏆 Judging Criteria Alignment

| Criterion | How RedSite AI Delivers |
|-----------|------------------------|
| **Technical Execution** | Full-stack FastAPI + Next.js, IBM Granite RAG, PyTorch CV, PostGIS spatial queries |
| **Innovation** | First Mars-focused project in the challenge; mission-aware what-if simulator; explainable AI analyst |
| **Challenge Fit** | Directly addresses "decision-support" and "making space more accessible" |
| **Feasibility** | 100% public NASA data; no space hardware required; scalable to additional sites |
| **Real-World Impact** | Supports NASA Artemis III planning, SpaceX Starship site selection, and academic Mars research |

---

## 📄 License

MIT License — See [LICENSE](LICENSE)

---

> Built for the IBM AI Builders Challenge — August 2026
