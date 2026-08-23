"""
Site scoring engine — deterministic weighted multi-criteria ranking
"""


from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from copy import deepcopy

# ---------------------------------------------------------------------------
# Mission profiles
# ---------------------------------------------------------------------------

@dataclass
class MissionProfile:
    name: str
    weights: Dict[str, float]
    description: str

    def copy_with_weights(self, new_weights: Dict[str, float]) -> "MissionProfile":
        """Create a copy with custom weights (must sum to ~1.0)."""
        copied = deepcopy(self)
        copied.weights = {k: new_weights.get(k, self.weights[k]) for k in self.weights}
        # Normalize to ensure sum = 1.0
        total = sum(copied.weights.values())
        if total > 0:
            copied.weights = {k: v / total for k, v in copied.weights.items()}
        return copied

BUILT_IN_PROFILES: Dict[str, MissionProfile] = {
    "settlement": MissionProfile(
        name="Human settlement",
        weights={"terrain": 0.25, "water": 0.35, "solar": 0.20, "science": 0.10, "edl": 0.10},
        description="Prioritizes water accessibility and terrain safety for long-term habitation."
    ),
    "science": MissionProfile(
        name="Scientific discovery",
        weights={"terrain": 0.20, "water": 0.15, "solar": 0.15, "science": 0.40, "edl": 0.10},
        description="Prioritizes geological and astrobiological science return."
    ),
    "resource": MissionProfile(
        name="Resource extraction",
        weights={"terrain": 0.20, "water": 0.30, "solar": 0.15, "science": 0.25, "edl": 0.10},
        description="Balances ice mining access with mineral science targets."
    ),
}

# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class SiteScorer:
    """
    Deterministic weighted multi-criteria scorer.

    All calculations are transparent and reproducible:
    score = sum(feature_i * weight_i) for i in [terrain, water, solar, science, edl]
    """

    def score(self, site, profile: MissionProfile) -> float:
        """Compute weighted score for a single site."""
        features = site.features
        weights = profile.weights

        total = 0.0
        for key, weight in weights.items():
            total += getattr(features, key) * weight
        return total

    def rank(self, sites: List, profile: MissionProfile) -> List[Tuple]:
        """Rank all sites by score (highest first)."""
        scored = [(site, self.score(site, profile)) for site in sites]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, site, profile: MissionProfile) -> Dict:
        """Generate a breakdown of how each feature contributed to the score."""
        features = site.features
        weights = profile.weights

        breakdown = {}
        for key, weight in weights.items():
            value = getattr(features, key)
            contribution = value * weight
            breakdown[key] = {
                "raw_score": value,
                "weight": round(weight, 2),
                "contribution": round(contribution, 2),
                "percentage": round((contribution / self.score(site, profile)) * 100, 1)
            }
        return breakdown
