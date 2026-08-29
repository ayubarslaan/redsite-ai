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
        description="Optional custom weights. Will be normalized to sum to 1.0. Keys: terrain, water, solar, science, edl"
    )

class FeatureContribution(BaseModel):
    """Decomposed contribution of a single feature to the total score."""
    raw_score: float = Field(..., description="Raw feature value (0-100)")
    weight: float = Field(..., description="Normalized mission weight applied")
    contribution: float = Field(..., description="Weighted contribution to total score")
    percentage: float = Field(..., description="Percentage of total score from this feature")

class RankingItem(BaseModel):
    site_id: str
    score: float
    rank: int
    decomposition: Optional[Dict[str, FeatureContribution]] = Field(
        None, description="Per-feature score breakdown reproducing the total score"
    )

class RankingExplanation(BaseModel):
    """Natural-language explanation of why rankings changed (or are stable)."""
    text: str
    rank1_site_id: str
    rank1_site_name: str
    key_advantage_feature: str
    key_advantage_contribution_delta: float

class ScoreResponse(BaseModel):
    mission: str
    mission_key: str
    weights_used: Dict[str, float] = Field(..., description="The normalized weights actually applied")
    is_custom_weights: bool = Field(False, description="True when user-supplied weights were applied")
    rankings: List[RankingItem]
    explanation: Optional[RankingExplanation] = None

# ---------------------------------------------------------------------------
# Comparison models
# ---------------------------------------------------------------------------

class SiteComparisonEntry(BaseModel):
    site_id: str
    site_name: str
    site_code: str
    rank: int
    score: float
    decomposition: Dict[str, FeatureContribution]
    strengths: List[str] = Field(..., description="Features where this site leads the comparison")
    weaknesses: List[str] = Field(..., description="Features where this site trails the comparison")

class CompareRequest(BaseModel):
    mission: str
    weights: Optional[Dict[str, float]] = None
    site_ids: Optional[List[str]] = Field(
        None, description="Specific site IDs to compare. Defaults to top-2 ranked sites."
    )

class CompareResponse(BaseModel):
    mission: str
    weights_used: Dict[str, float]
    sites: List[SiteComparisonEntry]
    narrative: str = Field(..., description="Analyst narrative comparing the sites using actual contributions")

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

class AnalystSiteData(BaseModel):
    """Slim site representation passed to the analyst for context."""
    id: str
    name: str
    code: str
    coordinates: "Coordinates"
    features: "SiteFeatures"
    description: str
    score: Optional[float] = None
    rank: Optional[int] = None
    decomposition: Optional[Dict[str, "FeatureContribution"]] = Field(
        None, description="Score decomposition for this site under current weights"
    )

class AnalystContext(BaseModel):
    mission: Optional[str] = Field(None, description="Current mission profile key")
    selected_site: Optional[str] = Field(None, description="Currently selected site ID")
    sites: List["AnalystSiteData"] = Field(default_factory=list, description="All candidate sites with scores")
    custom_weights: Optional[Dict[str, float]] = Field(
        None, description="User-supplied what-if weights (pre-normalization)"
    )
    is_custom_weights: bool = Field(False, description="True when the user has modified default weights")

class AnalystChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="User question")
    context: Optional[AnalystContext] = None

class AnalystChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    model_used: str = "rule-based"

# ---------------------------------------------------------------------------
# Data provenance models
# ---------------------------------------------------------------------------

class FeatureProvenanceItem(BaseModel):
    """Provenance record for a single feature dimension."""
    derived_from: str = Field(..., description="Method or source that produced this value")
    status: str = Field(
        ...,
        description="One of: WORKING PROTOTYPE, SIMULATED, NOT IMPLEMENTED, STATIC/DEMO"
    )
    score_basis: Optional[float] = Field(
        None, description="Raw computed value before scaling to 0-100"
    )
    description: str = Field(..., description="Human-readable explanation of the computation")

class MOLAResult(BaseModel):
    site_id: str
    slope_safety_pct: float
    mean_slope_deg: float
    max_slope_deg_sampled: float
    published_mean_slope_deg: float
    rock_abundance: float
    data_source: str
    status: str
    notes: str

class SHARADDeposit(BaseModel):
    depth_m: float
    confidence: float
    type: str
    reference: str

class SHARADResult(BaseModel):
    site_id: str
    ice_deposits: List[SHARADDeposit]
    water_accessibility_score: float
    data_source: str
    status: str
    notes: str

class SolarResult(BaseModel):
    site_id: str
    latitude_deg: float
    annual_avg_insolation_relative: float
    equatorial_reference: float
    solar_score: float
    data_source: str
    status: str
    notes: str

class ProvenanceComponents(BaseModel):
    mola: MOLAResult
    sharad: SHARADResult
    solar: SolarResult

class SiteProvenanceResponse(BaseModel):
    """
    Structured data provenance document for a single candidate site.

    Describes how each feature score was derived, which computation
    method was used, and what the explicit status of that method is.
    """
    site_id: str
    pipeline_version: str
    components: ProvenanceComponents
    feature_provenance: Dict[str, FeatureProvenanceItem]
