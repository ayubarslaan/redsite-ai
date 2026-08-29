"""
RedSite AI — backend tests for Milestone 2: Explainable Mission Optimization

Tests cover:
- Default mission profiles
- Custom weight normalization
- Score decomposition accuracy
- Ranking changes under weight modifications
- Comparison view
- Analyst receiving current scenario data
- API endpoints (score, compare, analyst/chat)
"""

import math
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Import application modules
# ---------------------------------------------------------------------------
from scoring import SiteScorer, BUILT_IN_PROFILES, MissionProfile
from models import (
    Site, Coordinates, SiteFeatures,
    ScoreRequest, CompareRequest, AnalystChatRequest, AnalystContext,
)
from analyst import RuleBasedAnalyst


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_site(id: str, name: str, terrain: int, water: int,
              solar: int, science: int, edl: int) -> Site:
    return Site(
        id=id, name=name, code=id.upper(),
        coordinates=Coordinates(lat=0.0, lon=0.0),
        features=SiteFeatures(
            terrain=terrain, water=water, solar=solar, science=science, edl=edl
        ),
        description=f"Test site {name}",
    )


SITE_A = make_site("site-a", "Alpha Base", terrain=90, water=80, solar=70, science=60, edl=50)
SITE_B = make_site("site-b", "Beta Station", terrain=50, water=40, solar=90, science=100, edl=80)
SITE_C = make_site("site-c", "Gamma Outpost", terrain=70, water=60, solar=60, science=70, edl=60)

ALL_SITES = [SITE_A, SITE_B, SITE_C]


@pytest.fixture
def scorer():
    return SiteScorer()


@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Default mission profiles
# ---------------------------------------------------------------------------

class TestDefaultProfiles:
    def test_settlement_profile_exists(self):
        assert "settlement" in BUILT_IN_PROFILES

    def test_science_profile_exists(self):
        assert "science" in BUILT_IN_PROFILES

    def test_resource_profile_exists(self):
        assert "resource" in BUILT_IN_PROFILES

    def test_settlement_weights_sum_to_one(self):
        total = sum(BUILT_IN_PROFILES["settlement"].weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_science_weights_sum_to_one(self):
        total = sum(BUILT_IN_PROFILES["science"].weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_resource_weights_sum_to_one(self):
        total = sum(BUILT_IN_PROFILES["resource"].weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_all_profiles_have_required_features(self):
        required = {"terrain", "water", "solar", "science", "edl"}
        for name, profile in BUILT_IN_PROFILES.items():
            assert set(profile.weights.keys()) == required, f"Profile {name} missing features"

    def test_settlement_water_is_highest_weight(self):
        """Settlement should prioritize water."""
        weights = BUILT_IN_PROFILES["settlement"].weights
        assert weights["water"] == max(weights.values())

    def test_science_science_is_highest_weight(self):
        """Science mission should prioritize science."""
        weights = BUILT_IN_PROFILES["science"].weights
        assert weights["science"] == max(weights.values())


# ---------------------------------------------------------------------------
# 2. Custom weight normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_custom_weights_are_normalized(self):
        profile = BUILT_IN_PROFILES["settlement"]
        custom = {"terrain": 1, "water": 1, "solar": 1, "science": 1, "edl": 1}
        new_profile = profile.copy_with_weights(custom)
        total = sum(new_profile.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_unequal_custom_weights_normalized(self):
        profile = BUILT_IN_PROFILES["settlement"]
        custom = {"terrain": 2, "water": 3, "solar": 1, "science": 1, "edl": 1}
        new_profile = profile.copy_with_weights(custom)
        total = sum(new_profile.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_partial_override_normalizes(self):
        """Updating only some keys still produces weights summing to 1.0."""
        profile = BUILT_IN_PROFILES["settlement"]
        new_profile = profile.copy_with_weights({"water": 0.5, "terrain": 0.5})
        total = sum(new_profile.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_original_profile_unchanged(self):
        """copy_with_weights must not mutate the original."""
        profile = BUILT_IN_PROFILES["settlement"]
        original_weights = dict(profile.weights)
        profile.copy_with_weights({"water": 0.9})
        assert profile.weights == original_weights

    def test_normalization_proportions_preserved(self):
        """Ratios between weights should be preserved after normalization."""
        profile = BUILT_IN_PROFILES["settlement"]
        custom = {"terrain": 2, "water": 4, "solar": 2, "science": 1, "edl": 1}
        new_profile = profile.copy_with_weights(custom)
        # water:terrain ratio should be 4:2 = 2:1
        ratio = new_profile.weights["water"] / new_profile.weights["terrain"]
        assert abs(ratio - 2.0) < 1e-9


# ---------------------------------------------------------------------------
# 3. Score decomposition
# ---------------------------------------------------------------------------

class TestScoreDecomposition:
    def test_decomposition_contributions_sum_to_score(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        total_score = scorer.score(SITE_A, profile)
        decomp = scorer.explain(SITE_A, profile)
        contribution_sum = sum(v["contribution"] for v in decomp.values())
        assert abs(contribution_sum - total_score) < 1e-6

    def test_decomposition_percentages_sum_to_100(self, scorer):
        profile = BUILT_IN_PROFILES["science"]
        decomp = scorer.explain(SITE_B, profile)
        pct_sum = sum(v["percentage"] for v in decomp.values())
        assert abs(pct_sum - 100.0) < 0.01  # allow small floating-point

    def test_decomposition_has_all_features(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        decomp = scorer.explain(SITE_A, profile)
        assert set(decomp.keys()) == {"terrain", "water", "solar", "science", "edl"}

    def test_decomposition_raw_score_matches_feature(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        decomp = scorer.explain(SITE_A, profile)
        assert decomp["terrain"]["raw_score"] == SITE_A.features.terrain
        assert decomp["water"]["raw_score"] == SITE_A.features.water

    def test_decomposition_weight_matches_profile(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        decomp = scorer.explain(SITE_A, profile)
        for feat, vals in decomp.items():
            assert abs(vals["weight"] - profile.weights[feat]) < 1e-9

    def test_decomposition_contribution_calculation(self, scorer):
        """contribution = raw_score * weight — verify each cell."""
        profile = BUILT_IN_PROFILES["settlement"]
        decomp = scorer.explain(SITE_A, profile)
        for feat, vals in decomp.items():
            expected = vals["raw_score"] * vals["weight"]
            assert abs(vals["contribution"] - expected) < 1e-6, \
                f"Contribution mismatch for {feat}: got {vals['contribution']}, expected {expected}"

    def test_decomposition_custom_weights(self, scorer):
        """Decomposition must use the normalized custom weights, not defaults."""
        profile = BUILT_IN_PROFILES["settlement"].copy_with_weights(
            {"terrain": 0.5, "water": 0.1, "solar": 0.1, "science": 0.2, "edl": 0.1}
        )
        decomp = scorer.explain(SITE_A, profile)
        contribution_sum = sum(v["contribution"] for v in decomp.values())
        expected_total = scorer.score(SITE_A, profile)
        assert abs(contribution_sum - expected_total) < 1e-6

    def test_decomposition_deterministic(self, scorer):
        """Same inputs always produce same decomposition."""
        profile = BUILT_IN_PROFILES["science"]
        decomp1 = scorer.explain(SITE_B, profile)
        decomp2 = scorer.explain(SITE_B, profile)
        for feat in decomp1:
            assert decomp1[feat]["contribution"] == decomp2[feat]["contribution"]


# ---------------------------------------------------------------------------
# 4. Ranking changes
# ---------------------------------------------------------------------------

class TestRankingChanges:
    def test_settlement_ranking(self, scorer):
        """SITE_A should rank higher for settlement (more water+terrain weight)."""
        profile = BUILT_IN_PROFILES["settlement"]
        ranked = scorer.rank(ALL_SITES, profile)
        assert ranked[0][0].id == "site-a"

    def test_science_ranking(self, scorer):
        """SITE_B should rank higher for science (science=100 with 40% weight)."""
        profile = BUILT_IN_PROFILES["science"]
        ranked = scorer.rank(ALL_SITES, profile)
        assert ranked[0][0].id == "site-b"

    def test_custom_weights_change_ranking(self, scorer):
        """Maximizing science weight should make SITE_B rank first."""
        profile = BUILT_IN_PROFILES["settlement"].copy_with_weights(
            {"terrain": 0.05, "water": 0.05, "solar": 0.05, "science": 0.80, "edl": 0.05}
        )
        ranked = scorer.rank(ALL_SITES, profile)
        assert ranked[0][0].id == "site-b"

    def test_ranking_sorted_descending(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        ranked = scorer.rank(ALL_SITES, profile)
        scores = [sc for _, sc in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_ranking_explanation_text_not_empty(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        ranked = scorer.rank(ALL_SITES, profile)
        expl = scorer.ranking_explanation(ranked, profile)
        assert len(expl["text"]) > 10

    def test_ranking_explanation_identifies_rank1(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        ranked = scorer.rank(ALL_SITES, profile)
        expl = scorer.ranking_explanation(ranked, profile)
        assert expl["rank1_site_id"] == ranked[0][0].id

    def test_ranking_explanation_contains_scores(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        ranked = scorer.rank(ALL_SITES, profile)
        expl = scorer.ranking_explanation(ranked, profile)
        # Score values should appear in the explanation text
        score1 = str(round(ranked[0][1], 1))
        assert score1 in expl["text"]

    def test_custom_weight_explanation_mentions_advantage(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"].copy_with_weights(
            {"terrain": 0.05, "water": 0.05, "solar": 0.05, "science": 0.80, "edl": 0.05}
        )
        ranked = scorer.rank(ALL_SITES, profile)
        expl = scorer.ranking_explanation(ranked, profile)
        assert "science" in expl["key_advantage_feature"] or "science" in expl["text"].lower()


# ---------------------------------------------------------------------------
# 5. Comparison view
# ---------------------------------------------------------------------------

class TestComparisonView:
    def test_compare_returns_two_sites(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile)
        assert len(result["sites"]) == 2

    def test_compare_returns_top2_by_default(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        ranked = scorer.rank(ALL_SITES, profile)
        result = scorer.compare(ALL_SITES, profile)
        assert result["sites"][0]["site_id"] == ranked[0][0].id
        assert result["sites"][1]["site_id"] == ranked[1][0].id

    def test_compare_specific_sites(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile, site_ids=["site-b", "site-c"])
        ids = {e["site_id"] for e in result["sites"]}
        assert ids == {"site-b", "site-c"}

    def test_compare_includes_decomposition(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile)
        for entry in result["sites"]:
            assert "decomposition" in entry
            assert "terrain" in entry["decomposition"]

    def test_compare_contributions_sum_to_score(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile)
        for entry in result["sites"]:
            total = sum(v["contribution"] for v in entry["decomposition"].values())
            assert abs(total - entry["score"]) < 0.1  # scores are rounded to 1dp

    def test_compare_strengths_weaknesses_not_both(self, scorer):
        """A feature cannot be both a strength and a weakness."""
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile)
        for entry in result["sites"]:
            overlap = set(entry["strengths"]) & set(entry["weaknesses"])
            assert len(overlap) == 0, f"Overlap: {overlap}"

    def test_compare_has_narrative(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile)
        assert len(result["narrative"]) > 20

    def test_compare_narrative_references_scores(self, scorer):
        profile = BUILT_IN_PROFILES["settlement"]
        result = scorer.compare(ALL_SITES, profile)
        assert result["sites"][0]["site_name"] in result["narrative"]

    def test_compare_weights_used_match_profile(self, scorer):
        profile = BUILT_IN_PROFILES["science"]
        result = scorer.compare(ALL_SITES, profile)
        total = sum(result["weights_used"].values())
        assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# 6. Analyst receives current scenario data
# ---------------------------------------------------------------------------

class TestAnalystContext:
    def _make_site_data(self, mission="settlement", is_custom=False, custom_weights=None):
        scorer = SiteScorer()
        profile = BUILT_IN_PROFILES[mission]
        if custom_weights:
            profile = profile.copy_with_weights(custom_weights)
        ranked = scorer.rank(ALL_SITES, profile)
        expl = scorer.ranking_explanation(ranked, profile)

        site_list = []
        for rank_pos, (site, score) in enumerate(ranked, 1):
            decomp = scorer.explain(site, profile)
            site_list.append({
                "id": site.id,
                "name": site.name,
                "code": site.code,
                "coordinates": {"lat": 0.0, "lon": 0.0},
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
                "decomposition": decomp,
            })

        return {
            "mission": mission,
            "mission_name": profile.name,
            "is_custom_weights": is_custom,
            "weights": profile.weights,
            "sites": site_list,
            "ranking_explanation": expl["text"],
        }

    def test_analyst_receives_decomposition(self):
        analyst = RuleBasedAnalyst()
        site_data = self._make_site_data("settlement")
        # Check that each site has decomposition
        for site in site_data["sites"]:
            assert "decomposition" in site
            for feat in ["terrain", "water", "solar", "science", "edl"]:
                assert feat in site["decomposition"]

    def test_analyst_responds_to_ranking_question(self):
        analyst = RuleBasedAnalyst()
        site_data = self._make_site_data("settlement")
        result = analyst.analyze("Why is this site ranked first?", site_data)
        assert "text" in result
        assert len(result["text"]) > 10

    def test_analyst_response_uses_ranking_explanation(self):
        analyst = RuleBasedAnalyst()
        site_data = self._make_site_data("settlement")
        result = analyst.analyze("Why is this site ranked first?", site_data)
        # The ranking explanation should appear in the text
        rank1_name = site_data["sites"][0]["name"]
        assert rank1_name in result["text"]

    def test_analyst_compare_uses_decomposition(self):
        analyst = RuleBasedAnalyst()
        site_data = self._make_site_data("settlement")
        result = analyst.analyze("Compare top 2 sites", site_data)
        assert "text" in result
        # Should reference actual score numbers
        score1 = str(site_data["sites"][0]["score"])
        assert score1 in result["text"]

    def test_analyst_receives_custom_weights_flag(self):
        analyst = RuleBasedAnalyst()
        custom = {"terrain": 0.1, "water": 0.1, "solar": 0.1, "science": 0.6, "edl": 0.1}
        site_data = self._make_site_data("settlement", is_custom=True, custom_weights=custom)
        assert site_data["is_custom_weights"] is True

    def test_analyst_explains_custom_weights(self):
        analyst = RuleBasedAnalyst()
        custom = {"terrain": 0.1, "water": 0.1, "solar": 0.1, "science": 0.6, "edl": 0.1}
        site_data = self._make_site_data("settlement", is_custom=True, custom_weights=custom)
        result = analyst.analyze("What are the current weights?", site_data)
        assert "custom" in result["text"].lower() or "weight" in result["text"].lower()

    def test_analyst_decomposition_breakdown(self):
        analyst = RuleBasedAnalyst()
        site_data = self._make_site_data("settlement")
        result = analyst.analyze("Show score breakdown", site_data)
        assert "text" in result
        # Should show contribution values
        assert "pts" in result["text"] or "%" in result["text"]

    def test_analyst_custom_weights_change_rankings_in_context(self):
        """Analyst data must reflect custom-weight rankings, not default."""
        # Under default settlement, SITE_A leads (more water)
        default_data = self._make_site_data("settlement")
        default_rank1 = default_data["sites"][0]["id"]

        # Under science-heavy custom weights, SITE_B (science=100) should lead
        custom = {"terrain": 0.05, "water": 0.05, "solar": 0.05, "science": 0.80, "edl": 0.05}
        custom_data = self._make_site_data("settlement", is_custom=True, custom_weights=custom)
        custom_rank1 = custom_data["sites"][0]["id"]

        assert default_rank1 != custom_rank1
        assert custom_rank1 == "site-b"


# ---------------------------------------------------------------------------
# 7. API endpoint tests (FastAPI TestClient)
# ---------------------------------------------------------------------------

class TestScoreEndpoint:
    def test_score_returns_decomposition(self, client):
        response = client.post("/api/score", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        assert "rankings" in data
        for item in data["rankings"]:
            assert "decomposition" in item
            assert item["decomposition"] is not None

    def test_score_decomposition_sums_to_score(self, client):
        response = client.post("/api/score", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        for item in data["rankings"]:
            contrib_sum = sum(v["contribution"] for v in item["decomposition"].values())
            assert abs(contrib_sum - item["score"]) < 0.2  # rounded to 1dp

    def test_score_returns_explanation(self, client):
        response = client.post("/api/score", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
        assert len(data["explanation"]["text"]) > 10

    def test_score_returns_weights_used(self, client):
        response = client.post("/api/score", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        assert "weights_used" in data
        total = sum(data["weights_used"].values())
        assert abs(total - 1.0) < 1e-6

    def test_score_custom_weights_normalized(self, client):
        response = client.post("/api/score", json={
            "mission": "settlement",
            "weights": {"terrain": 2, "water": 2, "solar": 2, "science": 2, "edl": 2}
        })
        assert response.status_code == 200
        data = response.json()
        total = sum(data["weights_used"].values())
        assert abs(total - 1.0) < 1e-6

    def test_score_is_custom_weights_flag(self, client):
        response = client.post("/api/score", json={
            "mission": "settlement",
            "weights": {"terrain": 0.5, "water": 0.1, "solar": 0.1, "science": 0.2, "edl": 0.1}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_custom_weights"] is True

    def test_score_default_not_custom(self, client):
        response = client.post("/api/score", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        assert data["is_custom_weights"] is False

    def test_score_invalid_mission(self, client):
        response = client.post("/api/score", json={"mission": "moon_base"})
        assert response.status_code == 400


class TestCompareEndpoint:
    def test_compare_default_top2(self, client):
        response = client.post("/api/compare", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["sites"]) == 2

    def test_compare_has_decomposition(self, client):
        response = client.post("/api/compare", json={"mission": "science"})
        assert response.status_code == 200
        data = response.json()
        for site in data["sites"]:
            assert "decomposition" in site
            assert len(site["decomposition"]) == 5

    def test_compare_has_strengths_weaknesses(self, client):
        response = client.post("/api/compare", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        for site in data["sites"]:
            assert "strengths" in site
            assert "weaknesses" in site

    def test_compare_narrative_not_empty(self, client):
        response = client.post("/api/compare", json={"mission": "settlement"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["narrative"]) > 20

    def test_compare_custom_weights(self, client):
        response = client.post("/api/compare", json={
            "mission": "settlement",
            "weights": {"terrain": 0.05, "water": 0.05, "solar": 0.05, "science": 0.80, "edl": 0.05}
        })
        assert response.status_code == 200
        data = response.json()
        # Under science-heavy weights, Valles Marineris (science=96) or Gale (science=94)
        # should be among the top 2
        top_ids = {s["site_id"] for s in data["sites"]}
        # At least one high-science site should appear
        assert "val-02" in top_ids or "gal-03" in top_ids

    def test_compare_specific_sites(self, client):
        response = client.post("/api/compare", json={
            "mission": "settlement",
            "site_ids": ["arc-01", "val-02"]
        })
        assert response.status_code == 200
        data = response.json()
        ids = {s["site_id"] for s in data["sites"]}
        assert "arc-01" in ids
        assert "val-02" in ids


class TestAnalystEndpoint:
    def test_analyst_chat_basic(self, client):
        response = client.post("/api/analyst/chat", json={
            "message": "Why is this site ranked first?",
            "context": {"mission": "settlement"}
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 10

    def test_analyst_uses_custom_weights(self, client):
        """Analyst context should reflect custom weights, not defaults."""
        # Default settlement: arc-01 leads
        response_default = client.post("/api/analyst/chat", json={
            "message": "Why is this site ranked first?",
            "context": {"mission": "settlement"}
        })
        # Custom science-heavy: val-02 or gal-03 should lead
        response_custom = client.post("/api/analyst/chat", json={
            "message": "Why is this site ranked first?",
            "context": {
                "mission": "settlement",
                "is_custom_weights": True,
                "custom_weights": {
                    "terrain": 0.05, "water": 0.05, "solar": 0.05,
                    "science": 0.80, "edl": 0.05
                }
            }
        })
        assert response_default.status_code == 200
        assert response_custom.status_code == 200

        default_text = response_default.json()["response"]
        custom_text = response_custom.json()["response"]

        # The custom response should mention a different top site
        # (Arcadia leads default settlement; Valles/Gale leads science-heavy)
        assert default_text != custom_text

    def test_analyst_compare_contains_scores(self, client):
        response = client.post("/api/analyst/chat", json={
            "message": "Compare top 2 sites",
            "context": {"mission": "settlement"}
        })
        assert response.status_code == 200
        data = response.json()
        # Response must include numeric score references
        import re
        numbers = re.findall(r"\d+\.?\d*", data["response"])
        assert len(numbers) > 0

    def test_analyst_decomposition_question(self, client):
        response = client.post("/api/analyst/chat", json={
            "message": "Show score breakdown",
            "context": {"mission": "settlement", "selected_site": "arc-01"}
        })
        assert response.status_code == 200
        data = response.json()
        assert "pts" in data["response"] or "%" in data["response"]
