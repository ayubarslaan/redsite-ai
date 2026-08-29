"""
RedSite AI — FastAPI Backend
Mars Site Intelligence & Decision Engine
"""


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models import (
    Site, SiteListResponse, ScoreRequest, ScoreResponse, RankingItem,
    FeatureContribution, RankingExplanation,
    CompareRequest, CompareResponse, SiteComparisonEntry,
    AnalystChatRequest, AnalystChatResponse, MissionProfileResponse,
    AnalystSiteData, AnalystContext,
)
from scoring import SiteScorer, BUILT_IN_PROFILES
from analyst import GraniteAnalyst, RuleBasedAnalyst
import os

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.scorer = SiteScorer()
    app.state.sites = load_sample_sites()

    # Try to initialize Granite; fall back to rule-based if unavailable
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    if api_key and project_id:
        try:
            app.state.analyst = GraniteAnalyst(api_key, project_id)
        except Exception:
            app.state.analyst = RuleBasedAnalyst()
    else:
        app.state.analyst = RuleBasedAnalyst()

    yield
    # Shutdown
    pass

app = FastAPI(
    title="RedSite AI API",
    description="Mars landing site intelligence and decision engine",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Sample data (pre-computed from NASA sources)
# ---------------------------------------------------------------------------

def load_sample_sites() -> list[Site]:
    """Load pre-computed candidate sites."""
    return [
        Site(
            id="arc-01",
            name="Arcadia Planitia",
            code="ARC-01",
            coordinates={"lat": 46.0, "lon": -180.0},
            features={"terrain": 91, "water": 97, "solar": 84, "science": 73, "edl": 92},
            description="Flat northern plains with shallow ice table. Low rock abundance. High solar at mid-latitudes."
        ),
        Site(
            id="val-02",
            name="Valles Marineris",
            code="VAL-02",
            coordinates={"lat": -14.0, "lon": -59.0},
            features={"terrain": 62, "water": 45, "solar": 88, "science": 96, "edl": 58},
            description="Massive canyon system. Extreme scientific value but challenging terrain and limited accessible ice."
        ),
        Site(
            id="gal-03",
            name="Gale Crater",
            code="GAL-03",
            coordinates={"lat": -5.4, "lon": 137.8},
            features={"terrain": 78, "water": 55, "solar": 81, "science": 94, "edl": 85},
            description="Proven rover landing site. Rich sedimentary record. Moderate ice, well-characterized EDL corridor."
        ),
        Site(
            id="uto-04",
            name="Utopia Planitia",
            code="UTO-04",
            coordinates={"lat": 46.7, "lon": 117.5},
            features={"terrain": 89, "water": 95, "solar": 72, "science": 68, "edl": 88},
            description="Vast ice-rich basin. Flat and safe but lower solar potential at high latitude. Proven by Phoenix lander."
        ),
        Site(
            id="hel-05",
            name="Hellas Planitia",
            code="HEL-05",
            coordinates={"lat": -42.4, "lon": 70.5},
            features={"terrain": 75, "water": 60, "solar": 90, "science": 80, "edl": 70},
            description="Deep impact basin with higher pressure. Good solar but rougher terrain and deeper atmosphere for EDL."
        ),
    ]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_profile(mission_key: str, custom_weights):
    """
    Resolve a MissionProfile from a mission key and optional custom weights.

    Always normalizes custom weights — the SiteScorer is the single source
    of truth; the frontend never scores independently.
    """
    profile = BUILT_IN_PROFILES.get(mission_key)
    if not profile:
        raise HTTPException(status_code=400, detail=f"Unknown mission profile: {mission_key}")
    is_custom = False
    if custom_weights:
        profile = profile.copy_with_weights(custom_weights)
        is_custom = True
    return profile, is_custom


def _build_decomposition(scorer: SiteScorer, site: Site, profile) -> dict:
    """Return explain() output wrapped as FeatureContribution dicts."""
    return scorer.explain(site, profile)

# ---------------------------------------------------------------------------
# Static frontend (production build)
# ---------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_out = os.path.join(os.path.dirname(__file__), "..", "frontend", "out")
if os.path.exists(frontend_out):
    app.mount("/static", StaticFiles(directory=frontend_out), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the built Next.js frontend in production."""
    index_path = os.path.join(frontend_out, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "RedSite AI API is running.",
        "docs": "/docs",
        "health": "/api/health"
    }

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "redsite-ai",
        "version": "2.0.0",
        "features": {
            "sites_loaded": len(app.state.sites),
            "analyst_mode": "granite" if hasattr(app.state.analyst, "llm") else "rule-based",
            "mission_profiles": list(BUILT_IN_PROFILES.keys()),
            "capabilities": ["score_decomposition", "what_if_weights", "ranking_explanation", "comparison"],
        }
    }

@app.get("/api/sites", response_model=SiteListResponse)
async def list_sites():
    """Return all candidate sites with raw feature vectors."""
    return SiteListResponse(sites=app.state.sites)

@app.get("/api/sites/{site_id}", response_model=Site)
async def get_site(site_id: str):
    """Return a single site by ID."""
    for site in app.state.sites:
        if site.id == site_id:
            return site
    raise HTTPException(status_code=404, detail="Site not found")

@app.post("/api/score", response_model=ScoreResponse)
async def score_sites(request: ScoreRequest):
    """Rank sites for a given mission profile.

    Returns full score decomposition for every site so the frontend can
    display exactly how each score was calculated without any client-side
    scoring logic.
    """
    profile, is_custom = _resolve_profile(request.mission, request.weights)
    scorer: SiteScorer = app.state.scorer

    ranked = scorer.rank(app.state.sites, profile)

    # Build ranking items with full decomposition
    ranking_items = []
    for i, (site, score) in enumerate(ranked):
        decomp_raw = scorer.explain(site, profile)
        decomp = {
            feat: FeatureContribution(
                raw_score=vals["raw_score"],
                weight=vals["weight"],
                contribution=vals["contribution"],
                percentage=vals["percentage"],
            )
            for feat, vals in decomp_raw.items()
        }
        ranking_items.append(RankingItem(
            site_id=site.id,
            score=round(score, 1),
            rank=i + 1,
            decomposition=decomp,
        ))

    # Generate ranking explanation from contributions
    expl_raw = scorer.ranking_explanation(ranked, profile)
    explanation = RankingExplanation(**expl_raw)

    return ScoreResponse(
        mission=profile.name,
        mission_key=request.mission,
        weights_used=profile.weights,
        is_custom_weights=is_custom,
        rankings=ranking_items,
        explanation=explanation,
    )

@app.post("/api/compare", response_model=CompareResponse)
async def compare_sites(request: CompareRequest):
    """Compare two sites side-by-side with full score decomposition.

    Defaults to the top-2 ranked sites. Pass site_ids to compare specific
    candidates.
    """
    profile, _ = _resolve_profile(request.mission, request.weights)
    scorer: SiteScorer = app.state.scorer

    result = scorer.compare(app.state.sites, profile, site_ids=request.site_ids)

    entries = []
    for entry in result["sites"]:
        decomp = {
            feat: FeatureContribution(
                raw_score=vals["raw_score"],
                weight=vals["weight"],
                contribution=vals["contribution"],
                percentage=vals["percentage"],
            )
            for feat, vals in entry["decomposition"].items()
        }
        entries.append(SiteComparisonEntry(
            site_id=entry["site_id"],
            site_name=entry["site_name"],
            site_code=entry["site_code"],
            rank=entry["rank"],
            score=entry["score"],
            decomposition=decomp,
            strengths=entry["strengths"],
            weaknesses=entry["weaknesses"],
        ))

    return CompareResponse(
        mission=result["mission"],
        weights_used=result["weights_used"],
        sites=entries,
        narrative=result["narrative"],
    )

@app.get("/api/mission/profiles", response_model=list[MissionProfileResponse])
async def list_profiles():
    """Return all built-in mission profiles."""
    return [
        MissionProfileResponse(
            key=key,
            name=profile.name,
            weights=profile.weights,
            description=profile.description
        )
        for key, profile in BUILT_IN_PROFILES.items()
    ]

@app.post("/api/analyst/chat", response_model=AnalystChatResponse)
async def analyst_chat(request: AnalystChatRequest):
    """Chat with the AI analyst.

    The analyst always operates on the CURRENT scenario — if the user has
    applied what-if weights, those weights are used for scoring here so that
    explanations match what the user sees on screen.
    """
    ctx = request.context or AnalystContext()
    mission_key = ctx.mission or "settlement"

    # Resolve profile — honor what-if weights from the frontend
    profile, is_custom = _resolve_profile(mission_key, ctx.custom_weights)
    scorer: SiteScorer = app.state.scorer

    ranked = scorer.rank(app.state.sites, profile)

    # Build ranked site list with decomposition for the analyst
    site_list = []
    for rank_pos, (site, score) in enumerate(ranked, 1):
        decomp_raw = scorer.explain(site, profile)
        decomp_serializable = {
            feat: {
                "raw_score": vals["raw_score"],
                "weight": round(vals["weight"], 4),
                "contribution": vals["contribution"],
                "percentage": vals["percentage"],
            }
            for feat, vals in decomp_raw.items()
        }
        site_list.append({
            "id": site.id,
            "name": site.name,
            "code": site.code,
            "coordinates": {"lat": site.coordinates.lat, "lon": site.coordinates.lon},
            "features": {
                "terrain": site.features.terrain,
                "water": site.features.water,
                "solar": site.features.solar,
                "science": site.features.science,
                "edl": site.features.edl,
            },
            "description": site.description,
            "score": round(score, 1),
            "rank": rank_pos,
            "decomposition": decomp_serializable,
        })

    # Generate explanation for the analyst's context
    expl = scorer.ranking_explanation(ranked, profile)

    site_data = {
        "mission": mission_key,
        "mission_name": profile.name,
        "is_custom_weights": is_custom,
        "weights": profile.weights,
        "sites": site_list,
        "ranking_explanation": expl["text"],
    }

    response = app.state.analyst.analyze(
        question=request.message,
        site_data=site_data,
        selected_site_id=ctx.selected_site,
    )
    return AnalystChatResponse(
        response=response["text"],
        sources=response.get("sources", []),
        model_used=response.get("model", "rule-based")
    )

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
