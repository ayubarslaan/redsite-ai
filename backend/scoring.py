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
        """Create a copy with custom weights.

        Accepts partial or full overrides.  The resulting weights are always
        normalized to sum exactly to 1.0, matching the behavior applied
        server-side when the frontend sends what-if sliders.
        """
        copied = deepcopy(self)
        # Only replace keys that exist in the profile; ignore unknown keys
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

    The decomposition returned by `explain()` is the single source of truth —
    the LLM never recalculates scores; it only interprets these values.
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
        """Rank all sites by score (highest first).

        Returns list of (site, score) tuples sorted descending.
        """
        scored = [(site, self.score(site, profile)) for site in sites]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, site, profile: MissionProfile) -> Dict:
        """Return the exact per-feature decomposition that reproduces the total score.

        The contribution values sum to the total score (within floating-point
        precision).  percentage values sum to 100%.
        """
        features = site.features
        weights = profile.weights
        total = self.score(site, profile)

        breakdown = {}
        for key, weight in weights.items():
            value = getattr(features, key)
            contribution = value * weight
            breakdown[key] = {
                "raw_score": value,
                "weight": weight,
                "contribution": round(contribution, 4),
                "percentage": round((contribution / total) * 100, 2) if total > 0 else 0.0,
            }
        return breakdown

    def ranking_explanation(
        self,
        ranked: List[Tuple],
        profile: MissionProfile,
    ) -> Dict:
        """Generate a natural-language explanation of why the #1 site leads.

        Uses actual computed contribution deltas — no hardcoded text.
        """
        if len(ranked) < 2:
            return {
                "text": f"{ranked[0][0].name} is the only candidate site.",
                "rank1_site_id": ranked[0][0].id,
                "rank1_site_name": ranked[0][0].name,
                "key_advantage_feature": "—",
                "key_advantage_contribution_delta": 0.0,
            }

        site1, score1 = ranked[0]
        site2, score2 = ranked[1]

        decomp1 = self.explain(site1, profile)
        decomp2 = self.explain(site2, profile)

        # Find the feature where site1's contribution most exceeds site2's
        deltas = {
            feat: decomp1[feat]["contribution"] - decomp2[feat]["contribution"]
            for feat in decomp1
        }
        best_feat = max(deltas, key=lambda f: deltas[f])
        worst_feat = min(deltas, key=lambda f: deltas[f])
        score_gap = round(score1 - score2, 1)

        feat_labels = {
            "terrain": "terrain safety",
            "water": "water accessibility",
            "solar": "solar potential",
            "science": "science value",
            "edl": "EDL safety",
        }
        best_label = feat_labels.get(best_feat, best_feat)
        worst_label = feat_labels.get(worst_feat, worst_feat)

        best_delta = round(deltas[best_feat], 2)
        worst_delta = round(deltas[worst_feat], 2)

        # Build explanation text from contributions
        advantage_parts = []
        for feat, delta in sorted(deltas.items(), key=lambda x: x[1], reverse=True):
            if delta > 0.5:
                advantage_parts.append(
                    f"{feat_labels.get(feat, feat)} (+{round(delta, 1)} pts)"
                )

        disadvantage_parts = []
        for feat, delta in sorted(deltas.items(), key=lambda x: x[1]):
            if delta < -0.5:
                disadvantage_parts.append(
                    f"{feat_labels.get(feat, feat)} ({round(delta, 1)} pts)"
                )

        mission_name = profile.name.lower()
        text = (
            f"{site1.name} ranks #1 (score {round(score1, 1)}) over {site2.name} "
            f"(score {round(score2, 1)}) by {score_gap} points under the {mission_name} mission."
        )

        if advantage_parts:
            text += f" Its {mission_name} advantages are driven by: {', '.join(advantage_parts)}."
        if disadvantage_parts:
            text += f" {site2.name} leads on: {', '.join(d.replace('(', '(+').replace('+-', '-') for d in disadvantage_parts)}"
            # reformat: the delta for site2 is positive where site1's delta was negative
            site2_advantages = []
            for feat, delta in sorted(deltas.items(), key=lambda x: x[1]):
                if delta < -0.5:
                    site2_advantages.append(
                        f"{feat_labels.get(feat, feat)} (+{round(-delta, 1)} pts)"
                    )
            text = (
                f"{site1.name} ranks #1 (score {round(score1, 1)}) over {site2.name} "
                f"(score {round(score2, 1)}) by {score_gap} points under the {mission_name} mission."
            )
            if advantage_parts:
                text += f" Advantages: {', '.join(advantage_parts)}."
            if site2_advantages:
                text += f" {site2.name} leads on: {', '.join(site2_advantages)}, but these are outweighed under current weights."

        return {
            "text": text,
            "rank1_site_id": site1.id,
            "rank1_site_name": site1.name,
            "key_advantage_feature": best_feat,
            "key_advantage_contribution_delta": best_delta,
        }

    def compare(self, sites: List, profile: MissionProfile, site_ids: List[str] = None) -> Dict:
        """Compare two (or more) specific sites, or default to top-2 ranked.

        Returns full decomposition + per-site strengths/weaknesses.
        """
        ranked = self.rank(sites, profile)

        if site_ids:
            # Pick the requested sites from the ranked list (preserving rank order)
            target_ids = set(site_ids)
            candidates = [(s, sc) for s, sc in ranked if s.id in target_ids]
        else:
            candidates = ranked[:2]

        if len(candidates) < 2:
            # Fall back to top-2
            candidates = ranked[:2]

        result = []
        decomps = {s.id: self.explain(s, profile) for s, _ in candidates}

        for i, (site, score) in enumerate(candidates):
            decomp = decomps[site.id]

            # Strengths: features where this site's raw_score is the highest among candidates
            strengths = []
            weaknesses = []
            feat_labels = {
                "terrain": "Terrain safety",
                "water": "Water access",
                "solar": "Solar potential",
                "science": "Science value",
                "edl": "EDL safety",
            }
            for feat in decomp:
                my_val = decomp[feat]["raw_score"]
                others = [
                    decomps[s.id][feat]["raw_score"]
                    for s, _ in candidates if s.id != site.id
                ]
                if others:
                    best_other = max(others)
                    if my_val > best_other + 5:
                        strengths.append(feat_labels.get(feat, feat))
                    elif my_val < best_other - 5:
                        weaknesses.append(feat_labels.get(feat, feat))

            # Also flag weighted contribution advantages
            contribution_strengths = []
            contribution_weaknesses = []
            for feat in decomp:
                my_contrib = decomp[feat]["contribution"]
                other_contribs = [
                    decomps[s.id][feat]["contribution"]
                    for s, _ in candidates if s.id != site.id
                ]
                if other_contribs:
                    best_other = max(other_contribs)
                    feat_label = feat_labels.get(feat, feat)
                    if my_contrib > best_other + 1 and feat_label not in strengths:
                        contribution_strengths.append(feat_label)
                    elif my_contrib < best_other - 1 and feat_label not in weaknesses:
                        contribution_weaknesses.append(feat_label)

            result.append({
                "site_id": site.id,
                "site_name": site.name,
                "site_code": site.code,
                "rank": i + 1,  # rank within this comparison set
                "score": round(score, 1),
                "decomposition": decomp,
                "strengths": strengths + contribution_strengths,
                "weaknesses": weaknesses + contribution_weaknesses,
            })

        # Build narrative using actual contributions
        if len(result) >= 2:
            s1, s2 = result[0], result[1]
            narrative = self._comparison_narrative(s1, s2, profile)
        else:
            narrative = f"Comparing {result[0]['site_name']} under the {profile.name} mission."

        return {
            "mission": profile.name,
            "weights_used": profile.weights,
            "sites": result,
            "narrative": narrative,
        }

    def _comparison_narrative(self, s1: Dict, s2: Dict, profile: MissionProfile) -> str:
        """Build a narrative from actual contribution data."""
        feat_labels = {
            "terrain": "terrain safety",
            "water": "water access",
            "solar": "solar potential",
            "science": "science value",
            "edl": "EDL safety",
        }

        score_gap = round(s1["score"] - s2["score"], 1)
        mission = profile.name.lower()

        # Feature where s1 most outperforms s2 by weighted contribution
        decomp1 = s1["decomposition"]
        decomp2 = s2["decomposition"]

        deltas = {
            feat: decomp1[feat]["contribution"] - decomp2[feat]["contribution"]
            for feat in decomp1
        }

        s1_advantages = [(feat_labels.get(f, f), round(d, 1)) for f, d in deltas.items() if d > 0.5]
        s2_advantages = [(feat_labels.get(f, f), round(-d, 1)) for f, d in deltas.items() if d < -0.5]

        s1_advantages.sort(key=lambda x: x[1], reverse=True)
        s2_advantages.sort(key=lambda x: x[1], reverse=True)

        def fmt_advantages(advs):
            return ", ".join(f"{name} (+{v} pts)" for name, v in advs[:3])

        lines = []
        if score_gap >= 0:
            lines.append(
                f"{s1['site_name']} leads with {s1['score']}/100 vs {s2['site_name']}'s "
                f"{s2['score']}/100 (gap: {score_gap} pts) under the {mission} mission."
            )
        else:
            lines.append(
                f"{s2['site_name']} leads with {s2['score']}/100 vs {s1['site_name']}'s "
                f"{s1['score']}/100 (gap: {-score_gap} pts) under the {mission} mission."
            )

        if s1_advantages:
            lines.append(f"{s1['site_name']} advantage: {fmt_advantages(s1_advantages)}.")
        if s2_advantages:
            lines.append(f"{s2['site_name']} advantage: {fmt_advantages(s2_advantages)}.")

        # Point out the decisive factor
        if s1_advantages and score_gap > 0:
            decisive_feat, decisive_delta = s1_advantages[0]
            lines.append(
                f"The decisive factor is {decisive_feat}: {s1['site_name']}'s contribution "
                f"({round(decomp1[list(deltas.keys())[list(deltas.values()).index(max(deltas.values()))]]['contribution'], 1)} pts) "
                f"outweighs {s2['site_name']}'s under current weights."
            )

        return " ".join(lines)
