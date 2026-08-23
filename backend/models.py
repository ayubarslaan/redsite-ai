"""
Pydantic v2 data models for RedSite AI API
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Site models
# ---------------------------------------------------------------------------

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in degrees")

class SiteFeatures(BaseModel):
    terrain: int = Field(..., ge=0, le=100, description="Terrain safety score (0-100)")
    water: int = Field(..., ge=0, le=100, description="Water accessibility score (0-100)")
    solar: int = Field(..., ge=0, le=100, description="Solar potential score (0-100)")
    science: int = Field(..., ge=0, le=100, description="Scientific value score (0-100)")
    edl: int = Field(..., ge=0, le=100, description="Entry-Descent-Landing safety score (0-100)")

class Site(BaseModel):
    id: str = Field(..., description="Unique site identifier")
    name: str = Field(..., description="Human-readable site name")
    code: str = Field(..., description="Site code (e.g., ARC-01)")
    coordinates: Coordinates
    features: SiteFeatures
    description: str = Field(..., description="Scientific description of the site")

class SiteListResponse(BaseModel):
    sites: List[Site]

# ---------------------------------------------------------------------------
# Scoring models
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    mission: str = Field(..., description="Mission profile key (settlement, science, resource)")
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Optional custom weights. Must sum to 1.0. Keys: terrain, water, solar, science, edl"
    )

class RankingItem(BaseModel):
    site_id: str
    score: float
    rank: int

class ScoreResponse(BaseModel):
    mission: str
    rankings: List[RankingItem]

# ---------------------------------------------------------------------------
# Mission profile models
# ---------------------------------------------------------------------------

class MissionProfileResponse(BaseModel):
    key: str
    name: str
    weights: Dict[str, float]
    description: str

# ---------------------------------------------------------------------------
# Analyst models
# ---------------------------------------------------------------------------

class AnalystContext(BaseModel):
    mission: Optional[str] = Field(None, description="Current mission profile key")
    selected_site: Optional[str] = Field(None, description="Currently selected site ID")

class AnalystChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="User question")
    context: Optional[AnalystContext] = None

class AnalystChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    model_used: str = "rule-based"
