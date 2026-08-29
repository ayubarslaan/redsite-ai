# RedSite AI — System Architecture

## Overview

RedSite AI is a full-stack decision-support platform for Mars landing site selection. It combines deterministic scientific computing, machine learning computer vision, and large language model (LLM) reasoning into a unified, explainable system.

## Design Principles

1. **Deterministic science first** — Elevation, slope, distance, solar exposure, and terrain statistics are computed with verified orbital mechanics and geospatial algorithms. The LLM never invents scientific values.
2. **ML for perception** — Computer vision classifies HiRISE imagery into terrain categories (safe, rocky, dune, cratered). This augments, not replaces, scientific models.
3. **LLM for explanation** — IBM Granite generates natural language summaries, comparisons, and risk assessments based on structured data retrieved via RAG.
4. **Mission-aware** — The scoring model is parameterized by mission profile, allowing real-time what-if analysis.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │ Mars Globe      │  │ Site Dashboard  │  │ Granite AI Analyst Chat     │ │
│  │ (Canvas/SVG)    │  │ (Radar + Bars)  │  │ (Streaming LLM responses)   │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘ │
│           │                    │                          │                 │
│           └────────────────────┴──────────────────────────┘                 │
│                              REST API + WebSocket                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            BACKEND (FastAPI)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ /sites       │  │ /score       │  │ /analyst     │  │ /mission     │  │
│  │ GET list     │  │ POST rank    │  │ POST chat    │  │ GET/PUT      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │                 │           │
│         └─────────────────┴──────────────────┴─────────────────┘           │
│                                    │                                       │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                         Service Layer                                  │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │ │
│  │  │ SiteService │  │ ScoreEngine │  │ AnalystService│  │ DataService│ │ │
│  │  │ (CRUD)      │  │ (Weighted   │  │ (RAG +       │  │ (NASA PDS  │ │ │
│  │  │             │  │  ranking)   │  │  Granite)    │  │  fetch)    │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           DATA & AI LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ PostgreSQL   │  │ ChromaDB     │  │ PyTorch      │  │ watsonx.ai   │  │
│  │ + PostGIS    │  │ (Vector DB)  │  │ (CNN)        │  │ (IBM Granite)│  │
│  │ Site +       │  │ NASA docs    │  │ Terrain      │  │ LLM +        │  │
│  │ spatial data │  │ embeddings   │  │ classifier   │  │ embeddings   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Ingestion Pipeline

```
NASA PDS / ODE
      │
      ├── MOLA DEM tiles ──► GDAL / rasterio ──► slope grid ──► PostGIS raster
      ├── SHARAD tracks ───► PDS parser ────────► ice polygons ──► PostGIS geometry
      ├── HiRISE images ───► PyTorch CNN ───────► terrain labels ──► PostgreSQL
      └── CRISM spectra ───► PDS parser ────────► mineral indices ──► PostgreSQL
```

### 2. Scoring Pipeline

```
User selects mission profile
      │
      ▼
┌─────────────────┐
│ Mission Profile │  { terrain: 25, water: 35, solar: 20, science: 10, edl: 10 }
│ (weights)       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Site Feature Vector                                         │
│ { terrain: 91, water: 97, solar: 84, science: 73, edl: 92 } │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Weighted Score = Σ(feature_i × weight_i)                    │
│ = 91×0.25 + 97×0.35 + 84×0.20 + 73×0.10 + 92×0.10 = 94.2  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
   Ranked candidate list
```

### 3. Analyst Pipeline (RAG)

```
User asks: "Why is Arcadia Planitia better than Gale Crater?"
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Retrieve site data from PostgreSQL                       │
│    { ARC-01: {...}, GAL-03: {...} }                        │
│ 2. Retrieve relevant NASA docs from ChromaDB                │
│    "Arcadia Planitia ice table..." "Gale Crater sediment..."│
│ 3. Build structured prompt with retrieved evidence          │
│ 4. Send to IBM Granite (watsonx.ai)                       │
│ 5. Stream response to frontend                              │
└─────────────────────────────────────────────────────────────┘
```

## API Specification

### `GET /api/sites`
Returns all candidate sites with raw feature vectors.

**Response:**
```json
{
  "sites": [
    {
      "id": "arc-01",
      "name": "Arcadia Planitia",
      "code": "ARC-01",
      "coordinates": { "lat": 46.0, "lon": -180.0 },
      "features": {
        "terrain": 91,
        "water": 97,
        "solar": 84,
        "science": 73,
        "edl": 92
      }
    }
  ]
}
```

### `POST /api/score`
Ranks sites for a given mission profile.

**Request:**
```json
{
  "mission": "settlement",
  "weights": { "terrain": 25, "water": 35, "solar": 20, "science": 10, "edl": 10 }
}
```

**Response:**
```json
{
  "rankings": [
    { "site_id": "arc-01", "score": 94.2, "rank": 1 },
    { "site_id": "gal-03", "score": 81.5, "rank": 2 }
  ]
}
```

### `POST /api/analyst/chat`
Chat with the Granite AI analyst.

**Request:**
```json
{
  "message": "Compare ARC-01 and GAL-03 for a settlement mission",
  "context": {
    "mission": "settlement",
    "selected_site": "arc-01"
  }
}
```

**Response:**
```json
{
  "response": "ARC-01 leads primarily due to superior water accessibility...",
  "sources": ["NASA MOLA Product Spec", "SHARAD Ice Detection Paper"]
}
```

## Technology Choices

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Backend** | FastAPI | Async Python, auto-generated OpenAPI docs, Pydantic validation |
| **Frontend** | Next.js 14 | App router, SSR for SEO, React Server Components |
| **Database** | PostgreSQL + PostGIS | Native spatial queries for Mars coordinates and raster tiles |
| **Vector DB** | ChromaDB | Lightweight, embeds with sentence-transformers, integrates with LangChain |
| **ML** | PyTorch + torchvision | Custom CNN for HiRISE terrain; pre-trained ResNet backbone |
| **LLM** | IBM Granite 13B (watsonx.ai) | Required by challenge; strong reasoning; enterprise-grade |
| **Orchestration** | LangChain | Structured tool calling, RAG chains, prompt templates |
| **Deployment** | Docker + Vercel | Containerized backend, edge-deployed frontend |

## Security & Reliability

- **Input validation:** All API inputs validated with Pydantic models
- **LLM grounding:** Granite responses are constrained to retrieved evidence; no hallucinated scientific facts
- **Fallback mode:** If watsonx.ai is unavailable, the analyst falls back to rule-based templates
- **Rate limiting:** API endpoints protected with slowapi rate limits

## Data Provenance (Milestone 3)

The `GET /api/sites/{site_id}/provenance` endpoint was added in Milestone 3.
It calls `data_ingest.run_ingestion_pipeline()` and returns a structured document
with explicit `status` labels per feature dimension:

```json
{
  "site_id": "arc-01",
  "pipeline_version": "1.0.0",
  "components": {
    "mola": { "slope_safety_pct": 100.0, "status": "WORKING PROTOTYPE", ... },
    "sharad": { "water_accessibility_score": 73.1, "status": "SIMULATED", ... },
    "solar": { "solar_score": 73.3, "status": "WORKING PROTOTYPE", ... }
  },
  "feature_provenance": {
    "terrain": { "status": "WORKING PROTOTYPE", "score_basis": 100.0 },
    "water":   { "status": "SIMULATED",          "score_basis": 73.1  },
    "solar":   { "status": "WORKING PROTOTYPE",  "score_basis": 73.3  },
    "science": { "status": "SIMULATED",          "score_basis": null  },
    "edl":     { "status": "SIMULATED",          "score_basis": null  }
  }
}
```

## Future Extensions

1. **Real MOLA tile ingestion** — `MOLAIngestor.fetch_tile()` is scaffolded; connect HTTP download from WUSTL ODE and replace `compute_slope()` with real rasterio processing
2. **SHARAD live query** — Replace `ICE_CATALOG` dict with live PDS track database query
3. **Additional sites** — Expand from 5 candidates to 50+ using automated region-of-interest detection
4. **HiRISE terrain CNN** — `terrain_cv.py` has a correct ResNet-18 architecture; requires training data and weights
5. **3D terrain mesh** — Generate CesiumJS-compatible terrain meshes from MOLA DEM
6. **Multi-mission optimization** — Pareto-frontier analysis for conflicting objectives
