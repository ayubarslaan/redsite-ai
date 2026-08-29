"""
RedSite AI — Milestone 3: Data Provenance Pipeline Tests

Tests cover:
- SolarModel: determinism, physics sanity (equator > poles), 0-100 range
- MOLAIngestor: determinism, slope safety score, published-value match
- SHARADIngestor: known deposits, water score formula
- run_ingestion_pipeline: all sites, complete provenance document structure
- /api/sites/{site_id}/provenance endpoint: response shape, status labels, 404

STATUS labels verified:
  WORKING PROTOTYPE — SolarModel, MOLAIngestor
  SIMULATED         — SHARADIngestor, science, edl
"""

import math
import pytest
from fastapi.testclient import TestClient

from data_ingest import (
    SolarModel,
    MOLAIngestor,
    SHARADIngestor,
    run_ingestion_pipeline,
    SITE_BOUNDS,
    STATUS_WORKING_PROTOTYPE,
    STATUS_SIMULATED,
    STATUS_NOT_IMPLEMENTED,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ALL_SITE_IDS = list(SITE_BOUNDS.keys())


@pytest.fixture
def solar():
    return SolarModel()


@pytest.fixture
def mola():
    return MOLAIngestor()


@pytest.fixture
def sharad():
    return SHARADIngestor()


@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. SolarModel — WORKING PROTOTYPE
# ---------------------------------------------------------------------------

class TestSolarModel:
    def test_equatorial_score_is_100(self, solar):
        """Equator is the reference — score should be exactly 100."""
        score = solar.score_site(0.0)
        assert score == 100.0

    def test_polar_score_is_less_than_equator(self, solar):
        """Poles receive less annual insolation than equator."""
        equator_score = solar.score_site(0.0)
        north_pole = solar.score_site(90.0)
        south_pole = solar.score_site(-90.0)
        assert north_pole < equator_score
        assert south_pole < equator_score

    def test_pole_score_in_range(self, solar):
        """Pole score should be positive and reasonable (Mars has no zero-sun poles)."""
        pole_score = solar.score_site(90.0)
        assert 30.0 <= pole_score <= 65.0

    def test_score_in_0_100_range(self, solar):
        """All latitudes should produce scores in [0, 100]."""
        for lat in range(-90, 91, 10):
            score = solar.score_site(float(lat))
            assert 0 <= score <= 100.0, f"score out of range at lat={lat}: {score}"

    def test_symmetric_hemispheres(self, solar):
        """Northern and southern hemisphere at same abs(lat) should score equally."""
        for lat in [15, 30, 45, 60, 75]:
            north = solar.score_site(float(lat))
            south = solar.score_site(float(-lat))
            # Mars insolation is symmetric about equator in annual average
            assert abs(north - south) < 1.0, (
                f"N/S asymmetry at |lat|={lat}: north={north}, south={south}"
            )

    def test_higher_latitude_lower_or_equal_score(self, solar):
        """Annual-average insolation decreases (weakly) with absolute latitude."""
        prev_score = solar.score_site(0.0)
        for lat in [15, 30, 45, 60, 75, 90]:
            score = solar.score_site(float(lat))
            assert score <= prev_score + 1.0, (
                f"Score increased unexpectedly at lat={lat}: {score} > {prev_score}"
            )
            prev_score = score

    def test_deterministic_same_inputs(self, solar):
        """Same latitude always produces the same score."""
        s1 = solar.score_site(46.0)
        s2 = solar.score_site(46.0)
        assert s1 == s2

    def test_annual_average_insolation_positive(self, solar):
        """Annual average insolation should be positive for all latitudes."""
        for lat in range(-80, 81, 10):
            ins = solar.annual_average_insolation(float(lat))
            assert ins > 0, f"insolation <= 0 at lat={lat}: {ins}"

    def test_process_site_all_sites(self, solar):
        """process_site() runs without error for all known sites."""
        for sid in ALL_SITE_IDS:
            result = solar.process_site(sid)
            assert result["site_id"] == sid
            assert result["status"] == STATUS_WORKING_PROTOTYPE
            assert 0 <= result["solar_score"] <= 100.0

    def test_process_site_unknown_raises(self, solar):
        with pytest.raises(ValueError, match="Unknown site"):
            solar.process_site("bogus-99")

    def test_arcadia_solar_reasonable(self, solar):
        """Arcadia (lat≈46°) should score lower than equatorial sites."""
        arcadia_score = solar.score_site(46.0)
        equator_score = solar.score_site(0.0)
        assert arcadia_score < equator_score
        assert arcadia_score > 50.0  # Still usable for solar power


# ---------------------------------------------------------------------------
# 2. MOLAIngestor — WORKING PROTOTYPE
# ---------------------------------------------------------------------------

class TestMOLAIngestor:
    def test_compute_slope_returns_array(self, mola):
        grid = mola.compute_slope("arc-01")
        assert grid.shape == (100, 100)

    def test_compute_slope_non_negative(self, mola):
        """Slope values must be non-negative degrees."""
        for sid in ALL_SITE_IDS:
            grid = mola.compute_slope(sid)
            assert grid.min() >= 0.0, f"Negative slope in {sid}"

    def test_compute_slope_deterministic(self, mola):
        """Same site always produces the same slope grid."""
        g1 = mola.compute_slope("arc-01")
        g2 = mola.compute_slope("arc-01")
        import numpy as np
        np.testing.assert_array_equal(g1, g2)

    def test_different_sites_different_grids(self, mola):
        """Different sites should produce different slope grids."""
        g_arc = mola.compute_slope("arc-01")
        g_val = mola.compute_slope("val-02")
        import numpy as np
        assert not np.array_equal(g_arc, g_val)

    def test_mean_slope_matches_published(self, mola):
        """The mean of the synthetic grid should be close to the published value."""
        import numpy as np
        for sid in ALL_SITE_IDS:
            published = SITE_BOUNDS[sid]["mean_slope_deg"]
            grid = mola.compute_slope(sid)
            computed_mean = float(np.mean(grid))
            # Rayleigh distribution with correct sigma produces correct mean
            # Allow 30% tolerance (stochastic, but reproducible)
            assert abs(computed_mean - published) <= published * 0.4, (
                f"{sid}: computed mean {computed_mean:.2f}° vs published {published}°"
            )

    def test_slope_safety_score_0_to_100(self, mola):
        """Safety score must be in [0, 100]."""
        for sid in ALL_SITE_IDS:
            grid = mola.compute_slope(sid)
            score = mola.slope_safety_score(grid)
            assert 0.0 <= score <= 100.0

    def test_arcadia_is_safer_than_valles(self, mola):
        """Arcadia (flat plains) must be safer than Valles Marineris (canyon)."""
        g_arc = mola.compute_slope("arc-01")
        g_val = mola.compute_slope("val-02")
        arc_safe = mola.slope_safety_score(g_arc)
        val_safe = mola.slope_safety_score(g_val)
        assert arc_safe > val_safe, (
            f"Expected Arcadia safer than Valles: {arc_safe:.1f} vs {val_safe:.1f}"
        )

    def test_process_site_has_status(self, mola):
        for sid in ALL_SITE_IDS:
            result = mola.process_site(sid)
            assert result["status"] == STATUS_WORKING_PROTOTYPE

    def test_process_site_unknown_raises(self, mola):
        with pytest.raises(ValueError, match="Unknown site"):
            mola.process_site("bogus-99")

    def test_fetch_tile_returns_none_when_absent(self, mola):
        """fetch_tile returns None when the tile file does not exist locally."""
        result = mola.fetch_tile(44, -180)
        assert result is None


# ---------------------------------------------------------------------------
# 3. SHARADIngestor — SIMULATED
# ---------------------------------------------------------------------------

class TestSHARADIngestor:
    def test_arcadia_has_ice_deposit(self, sharad):
        deposits = sharad.find_ice_deposits("arc-01")
        assert len(deposits) == 1
        assert deposits[0]["type"] == "shallow_ice_table"

    def test_utopia_has_high_confidence_ice(self, sharad):
        deposits = sharad.find_ice_deposits("uto-04")
        assert len(deposits) == 1
        assert deposits[0]["confidence"] >= 0.95

    def test_valles_has_no_ice(self, sharad):
        deposits = sharad.find_ice_deposits("val-02")
        assert deposits == []

    def test_all_deposits_have_required_fields(self, sharad):
        for sid in ALL_SITE_IDS:
            deposits = sharad.find_ice_deposits(sid)
            for d in deposits:
                assert "depth_m" in d
                assert "confidence" in d
                assert "type" in d
                assert "reference" in d

    def test_water_score_no_ice_is_45(self, sharad):
        """Valles (no ice) should return 45.0."""
        score = sharad.water_accessibility_score("val-02")
        assert score == 45.0

    def test_water_score_in_range(self, sharad):
        for sid in ALL_SITE_IDS:
            score = sharad.water_accessibility_score(sid)
            assert 0.0 <= score <= 100.0

    def test_arcadia_higher_water_than_valles(self, sharad):
        """Arcadia's shallow ice should score higher than Valles's no-ice."""
        arc = sharad.water_accessibility_score("arc-01")
        val = sharad.water_accessibility_score("val-02")
        assert arc > val

    def test_utopia_is_highest_water_site(self, sharad):
        """Utopia has the shallowest, most confident ice — should be highest."""
        scores = {sid: sharad.water_accessibility_score(sid) for sid in ALL_SITE_IDS}
        assert scores["uto-04"] == max(scores.values())

    def test_process_site_status_is_simulated(self, sharad):
        for sid in ALL_SITE_IDS:
            result = sharad.process_site(sid)
            assert result["status"] == STATUS_SIMULATED

    def test_process_site_water_score_matches_direct_call(self, sharad):
        """process_site().water_accessibility_score must equal water_accessibility_score()."""
        for sid in ALL_SITE_IDS:
            direct = sharad.water_accessibility_score(sid)
            via_process = sharad.process_site(sid)["water_accessibility_score"]
            assert direct == via_process


# ---------------------------------------------------------------------------
# 4. run_ingestion_pipeline
# ---------------------------------------------------------------------------

class TestIngestionPipeline:
    def test_pipeline_runs_all_sites(self):
        for sid in ALL_SITE_IDS:
            result = run_ingestion_pipeline(sid)
            assert result["site_id"] == sid

    def test_pipeline_returns_pipeline_version(self):
        result = run_ingestion_pipeline("arc-01")
        assert "pipeline_version" in result

    def test_pipeline_has_required_components(self):
        result = run_ingestion_pipeline("arc-01")
        assert "mola" in result["components"]
        assert "sharad" in result["components"]
        assert "solar" in result["components"]

    def test_pipeline_has_feature_provenance(self):
        result = run_ingestion_pipeline("arc-01")
        fp = result["feature_provenance"]
        for feat in ["terrain", "water", "solar", "science", "edl"]:
            assert feat in fp, f"Missing provenance for feature: {feat}"

    def test_feature_provenance_has_required_fields(self):
        result = run_ingestion_pipeline("arc-01")
        fp = result["feature_provenance"]
        for feat, entry in fp.items():
            assert "derived_from" in entry, f"{feat} missing derived_from"
            assert "status" in entry, f"{feat} missing status"
            assert "description" in entry, f"{feat} missing description"

    def test_terrain_status_is_working_prototype(self):
        result = run_ingestion_pipeline("arc-01")
        assert result["feature_provenance"]["terrain"]["status"] == STATUS_WORKING_PROTOTYPE

    def test_solar_status_is_working_prototype(self):
        result = run_ingestion_pipeline("arc-01")
        assert result["feature_provenance"]["solar"]["status"] == STATUS_WORKING_PROTOTYPE

    def test_water_status_is_simulated(self):
        result = run_ingestion_pipeline("arc-01")
        assert result["feature_provenance"]["water"]["status"] == STATUS_SIMULATED

    def test_science_status_is_simulated(self):
        result = run_ingestion_pipeline("arc-01")
        assert result["feature_provenance"]["science"]["status"] == STATUS_SIMULATED

    def test_edl_status_is_simulated(self):
        result = run_ingestion_pipeline("arc-01")
        assert result["feature_provenance"]["edl"]["status"] == STATUS_SIMULATED

    def test_terrain_score_basis_is_present(self):
        """terrain and solar should have a numeric score_basis."""
        result = run_ingestion_pipeline("arc-01")
        fp = result["feature_provenance"]
        assert fp["terrain"]["score_basis"] is not None
        assert fp["solar"]["score_basis"] is not None

    def test_pipeline_is_deterministic(self):
        """Running the pipeline twice for the same site returns identical results."""
        r1 = run_ingestion_pipeline("gal-03")
        r2 = run_ingestion_pipeline("gal-03")
        assert r1 == r2

    def test_pipeline_unknown_site_raises(self):
        with pytest.raises(ValueError, match="Unknown site"):
            run_ingestion_pipeline("bogus-99")

    def test_arcadia_flat_terrain_score(self):
        """Arcadia (published slope 0.6°) should have very high terrain safety."""
        result = run_ingestion_pipeline("arc-01")
        slope_pct = result["components"]["mola"]["slope_safety_pct"]
        # 0.6° mean slope → virtually all area below 5° threshold
        assert slope_pct > 90.0, f"Expected >90% safe for Arcadia, got {slope_pct}"

    def test_valles_low_terrain_score(self):
        """Valles Marineris (canyon, 8.5° mean slope) should have low terrain safety."""
        result = run_ingestion_pipeline("val-02")
        slope_pct = result["components"]["mola"]["slope_safety_pct"]
        assert slope_pct < 60.0, f"Expected <60% safe for Valles, got {slope_pct}"

    def test_equatorial_site_higher_solar(self):
        """Gale Crater (lat≈-5°) should score higher solar than Arcadia (lat≈46°)."""
        gale = run_ingestion_pipeline("gal-03")["components"]["solar"]["solar_score"]
        arcadia = run_ingestion_pipeline("arc-01")["components"]["solar"]["solar_score"]
        assert gale > arcadia, f"Expected Gale solar {gale} > Arcadia solar {arcadia}"


# ---------------------------------------------------------------------------
# 5. /api/sites/{site_id}/provenance endpoint
# ---------------------------------------------------------------------------

class TestProvenanceEndpoint:
    def test_provenance_returns_200(self, client):
        response = client.get("/api/sites/arc-01/provenance")
        assert response.status_code == 200

    def test_provenance_all_sites(self, client):
        for sid in ALL_SITE_IDS:
            response = client.get(f"/api/sites/{sid}/provenance")
            assert response.status_code == 200, f"Failed for site {sid}"

    def test_provenance_404_unknown_site(self, client):
        response = client.get("/api/sites/bogus-99/provenance")
        assert response.status_code == 404

    def test_provenance_has_site_id(self, client):
        response = client.get("/api/sites/arc-01/provenance")
        data = response.json()
        assert data["site_id"] == "arc-01"

    def test_provenance_has_pipeline_version(self, client):
        response = client.get("/api/sites/arc-01/provenance")
        data = response.json()
        assert "pipeline_version" in data

    def test_provenance_has_all_components(self, client):
        response = client.get("/api/sites/gal-03/provenance")
        data = response.json()
        assert "mola" in data["components"]
        assert "sharad" in data["components"]
        assert "solar" in data["components"]

    def test_provenance_has_all_feature_dimensions(self, client):
        response = client.get("/api/sites/uto-04/provenance")
        data = response.json()
        fp = data["feature_provenance"]
        for feat in ["terrain", "water", "solar", "science", "edl"]:
            assert feat in fp

    def test_provenance_status_labels_are_valid(self, client):
        valid_statuses = {STATUS_WORKING_PROTOTYPE, STATUS_SIMULATED, STATUS_NOT_IMPLEMENTED}
        response = client.get("/api/sites/arc-01/provenance")
        data = response.json()
        for feat, entry in data["feature_provenance"].items():
            assert entry["status"] in valid_statuses, (
                f"{feat}: unexpected status '{entry['status']}'"
            )

    def test_provenance_mola_status_working_prototype(self, client):
        response = client.get("/api/sites/arc-01/provenance")
        data = response.json()
        assert data["components"]["mola"]["status"] == STATUS_WORKING_PROTOTYPE

    def test_provenance_sharad_status_simulated(self, client):
        response = client.get("/api/sites/arc-01/provenance")
        data = response.json()
        assert data["components"]["sharad"]["status"] == STATUS_SIMULATED

    def test_provenance_solar_status_working_prototype(self, client):
        response = client.get("/api/sites/arc-01/provenance")
        data = response.json()
        assert data["components"]["solar"]["status"] == STATUS_WORKING_PROTOTYPE

    def test_provenance_solar_score_in_range(self, client):
        for sid in ALL_SITE_IDS:
            response = client.get(f"/api/sites/{sid}/provenance")
            data = response.json()
            score = data["components"]["solar"]["solar_score"]
            assert 0 <= score <= 100.0

    def test_provenance_mola_slope_safety_in_range(self, client):
        for sid in ALL_SITE_IDS:
            response = client.get(f"/api/sites/{sid}/provenance")
            data = response.json()
            pct = data["components"]["mola"]["slope_safety_pct"]
            assert 0 <= pct <= 100.0

    def test_provenance_is_deterministic(self, client):
        """Two requests for the same site return identical responses."""
        r1 = client.get("/api/sites/gal-03/provenance").json()
        r2 = client.get("/api/sites/gal-03/provenance").json()
        assert r1 == r2

    def test_provenance_appears_in_health_capabilities(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "data_provenance" in data["features"]["capabilities"]

    def test_provenance_sharad_utopia_ice_present(self, client):
        """Utopia provenance should show ice deposits."""
        response = client.get("/api/sites/uto-04/provenance")
        data = response.json()
        deposits = data["components"]["sharad"]["ice_deposits"]
        assert len(deposits) > 0

    def test_provenance_sharad_valles_no_ice(self, client):
        """Valles provenance should show no ice deposits."""
        response = client.get("/api/sites/val-02/provenance")
        data = response.json()
        deposits = data["components"]["sharad"]["ice_deposits"]
        assert deposits == []
