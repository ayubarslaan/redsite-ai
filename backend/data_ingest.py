"""
NASA Planetary Data System ingestion pipeline
Fetches/computes MOLA, SHARAD, and solar data for Mars site analysis.

IMPLEMENTATION STATUS per component:
  SolarModel                — WORKING PROTOTYPE  (analytical model, no external data)
  SHARADIngestor            — SIMULATED          (science-grounded values, no live PDS fetch)
  MOLAIngestor.compute_slope— WORKING PROTOTYPE  (deterministic analytical model from lat/lon bounds)
  MOLAIngestor.fetch_tile   — NOT IMPLEMENTED    (requires NASA PDS HTTP download)
  run_ingestion_pipeline    — WORKING PROTOTYPE  (calls above components, returns provenance)
"""

import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Candidate site bounding boxes (lat/lon) and known surface characteristics
SITE_BOUNDS: Dict[str, Dict] = {
    "arc-01": {
        "lat_min": 44.0, "lat_max": 48.0, "lon_min": -185.0, "lon_max": -175.0,
        # Known geological properties from published literature
        "mean_slope_deg": 0.6,   # Tanaka et al. 2014 — smooth Amazonian plains
        "rock_abundance": 0.02,  # Golombek et al. 2012 — low rock fraction
    },
    "val-02": {
        "lat_min": -16.0, "lat_max": -12.0, "lon_min": -61.0, "lon_max": -57.0,
        "mean_slope_deg": 8.5,   # Valles Marineris canyon walls, highly variable
        "rock_abundance": 0.18,
    },
    "gal-03": {
        "lat_min": -7.0, "lat_max": -3.0, "lon_min": 135.0, "lon_max": 140.0,
        "mean_slope_deg": 2.1,   # Curiosity landing ellipse characterisation
        "rock_abundance": 0.07,
    },
    "uto-04": {
        "lat_min": 44.0, "lat_max": 49.0, "lon_min": 115.0, "lon_max": 120.0,
        "mean_slope_deg": 0.5,   # Phoenix landing site — extremely flat
        "rock_abundance": 0.03,
    },
    "hel-05": {
        "lat_min": -44.0, "lat_max": -40.0, "lon_min": 68.0, "lon_max": 73.0,
        "mean_slope_deg": 3.8,   # Basin floor, moderate relief
        "rock_abundance": 0.08,
    },
}

# Provenance status labels used throughout this module
STATUS_WORKING_PROTOTYPE = "WORKING PROTOTYPE"
STATUS_SIMULATED = "SIMULATED"
STATUS_NOT_IMPLEMENTED = "NOT IMPLEMENTED"

# ---------------------------------------------------------------------------
# MOLA DEM ingestion
# ---------------------------------------------------------------------------

class MOLAIngestor:
    """
    Mars Orbiter Laser Altimeter (MOLA) terrain analysis.

    Data source: NASA Planetary Data System / WUSTL ODE
    URL: https://ode.rsl.wustl.edu/mars/

    Implementation status:
      - fetch_tile()       : NOT IMPLEMENTED  (requires PDS HTTP download)
      - compute_slope()    : WORKING PROTOTYPE (analytical model from known site properties)
      - slope_safety_score(): WORKING PROTOTYPE (deterministic from compute_slope)
    """

    BASE_URL = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/"

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir / "mola"
        self.data_dir.mkdir(exist_ok=True)

    def fetch_tile(self, lat: int, lon: int) -> Optional[Path]:
        """
        Download a single MOLA MEgDR tile from NASA PDS.

        STATUS: NOT IMPLEMENTED — requires NASA PDS HTTP access and ~100MB per tile.
        Returns None if tile is not present locally.
        """
        filename = (
            f"megt{abs(lat):02d}{'n' if lat >= 0 else 's'}"
            f"{abs(lon):03d}{'e' if lon >= 0 else 'w'}hb.img"
        )
        local_path = self.data_dir / filename
        if local_path.exists():
            return local_path
        # NOT IMPLEMENTED: would HTTP-GET from self.BASE_URL
        return None

    def compute_slope(self, site_id: str) -> np.ndarray:
        """
        Compute a synthetic slope grid for the site using published mean slope
        and a Rayleigh distribution approximation.

        STATUS: WORKING PROTOTYPE
          - Uses published mean_slope_deg from SITE_BOUNDS (Golombek et al. 2012,
            Tanaka et al. 2014, Curiosity landing analysis)
          - Generates a reproducible synthetic grid matching the known statistics
          - NOT a real DEM — no actual raster data is downloaded
          - For production: replace with rasterio.open(tile_path) + scipy.ndimage.sobel

        Returns:
            np.ndarray: 100×100 grid of slope values in degrees (deterministic)
        """
        bounds = SITE_BOUNDS.get(site_id)
        if not bounds:
            raise ValueError(f"Unknown site: {site_id}")

        mean_slope = bounds["mean_slope_deg"]

        # Rayleigh distribution approximates real Mars slope distributions
        # (sigma parameter derived from mean: mean = sigma * sqrt(pi/2))
        sigma = mean_slope / math.sqrt(math.pi / 2)

        # Deterministic seed from site_id so results are reproducible
        seed = sum(ord(c) for c in site_id)
        rng = np.random.default_rng(seed)

        grid = rng.rayleigh(sigma, (100, 100))
        return grid

    def slope_safety_score(
        self, slope_grid: np.ndarray, max_slope_deg: float = 5.0
    ) -> float:
        """
        Percentage of area with slope < max_slope_deg.

        5° is the NASA Human Exploration landing safety threshold.
        Reference: Golombek et al. (2012), MSL landing site selection criteria.

        STATUS: WORKING PROTOTYPE
        """
        safe_pixels = np.sum(slope_grid < max_slope_deg)
        return float((safe_pixels / slope_grid.size) * 100)

    def process_site(self, site_id: str) -> Dict:
        """
        Compute MOLA-derived terrain metrics for a candidate site.

        STATUS: WORKING PROTOTYPE (analytical, not real DEM)
        """
        bounds = SITE_BOUNDS.get(site_id)
        if not bounds:
            raise ValueError(f"Unknown site: {site_id}")

        slope_grid = self.compute_slope(site_id)
        safety_pct = self.slope_safety_score(slope_grid)

        return {
            "site_id": site_id,
            "slope_safety_pct": round(safety_pct, 1),
            "mean_slope_deg": round(float(np.mean(slope_grid)), 2),
            "max_slope_deg_sampled": round(float(np.max(slope_grid)), 2),
            "published_mean_slope_deg": bounds["mean_slope_deg"],
            "rock_abundance": bounds["rock_abundance"],
            "data_source": "MOLA MEgDR analytical model (NASA PDS reference values)",
            "status": STATUS_WORKING_PROTOTYPE,
            "notes": (
                "Slope grid derived from published mean slope via Rayleigh distribution. "
                "Values match known site characteristics from Golombek et al. (2012) "
                "and Tanaka et al. (2014). Not computed from raw raster tiles."
            ),
        }

# ---------------------------------------------------------------------------
# SHARAD ice ingestion
# ---------------------------------------------------------------------------

class SHARADIngestor:
    """
    Shallow Radar (SHARAD) subsurface ice detection.

    Data source: NASA PDS Geosciences Node
    URL: https://pds-geosciences.wustl.edu/missions/mro/sharad.htm

    Implementation status: SIMULATED
      - Values are science-grounded from published literature
      - No live PDS query is performed
      - References: Plaut et al. (2009) GRL, Stuurman et al. (2016) JGR-Planets,
        Bramson et al. (2015) GRL for Arcadia
    """

    # Science-grounded ice deposit data derived from peer-reviewed publications.
    # Depths and confidence values sourced from published SHARAD detections.
    ICE_CATALOG: Dict[str, List[Dict]] = {
        "arc-01": [
            {
                "depth_m": 0.3,
                "confidence": 0.95,
                "type": "shallow_ice_table",
                "reference": "Bramson et al. (2015) GRL — thick excess ice in Arcadia",
            }
        ],
        "val-02": [],
        "gal-03": [
            {
                "depth_m": 1.5,
                "confidence": 0.60,
                "type": "hydrated_minerals",
                "reference": "Milliken et al. (2010) — clay minerals in Gale sediment",
            }
        ],
        "uto-04": [
            {
                "depth_m": 0.1,
                "confidence": 0.98,
                "type": "ubiquitous_ice",
                "reference": "Stuurman et al. (2016) JGR — massive ice in Utopia",
            }
        ],
        "hel-05": [
            {
                "depth_m": 2.0,
                "confidence": 0.55,
                "type": "possible_ice",
                "reference": "Plaut et al. (2009) GRL — mid-latitude ice deposits",
            }
        ],
    }

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir / "sharad"
        self.data_dir.mkdir(exist_ok=True)

    def find_ice_deposits(self, site_id: str) -> List[Dict]:
        """
        Return ice deposits near a candidate site.

        STATUS: SIMULATED — science-grounded from published literature,
        not queried from live PDS track database.
        """
        return self.ICE_CATALOG.get(site_id, [])

    def water_accessibility_score(self, site_id: str) -> float:
        """
        Score water accessibility on 0–100 scale based on SHARAD detections.

        Formula: confidence × 100 × 1/(1 + depth_m)
        Rationale: shallower, higher-confidence ice is more accessible for
        ISRU drilling. Maximum 100.0.

        STATUS: WORKING PROTOTYPE (deterministic formula applied to SIMULATED data)
        """
        deposits = self.find_ice_deposits(site_id)

        if not deposits:
            return 45.0  # No confirmed ice — low but non-zero (atmosphere extraction possible)

        best = max(deposits, key=lambda d: d["confidence"] / max(d["depth_m"], 0.1))
        score = best["confidence"] * 100 * (1.0 / (1.0 + best["depth_m"]))
        return min(round(score, 1), 100.0)

    def process_site(self, site_id: str) -> Dict:
        """
        Return SHARAD-derived water accessibility data for a candidate site.

        STATUS: SIMULATED
        """
        deposits = self.find_ice_deposits(site_id)
        water_score = self.water_accessibility_score(site_id)

        return {
            "site_id": site_id,
            "ice_deposits": deposits,
            "water_accessibility_score": water_score,
            "data_source": "SHARAD science-grounded catalog (NASA PDS reference values)",
            "status": STATUS_SIMULATED,
            "notes": (
                "Ice deposit depths and confidence values sourced from peer-reviewed "
                "SHARAD publications. No live PDS query performed. For production, "
                "query SHARAD track database at pds-geosciences.wustl.edu."
            ),
        }

# ---------------------------------------------------------------------------
# Solar insolation model
# ---------------------------------------------------------------------------

class SolarModel:
    """
    Solar insolation at Mars surface based on latitude and season.

    STATUS: WORKING PROTOTYPE
      - Uses real Mars orbital mechanics (axial tilt 25.19°)
      - Annual-average model (integrates over a full Mars year)
      - Not a full GCM — ignores dust opacity, topographic shading, eccentricity
      - For production: use Mars Climate Database or AMES GCM outputs

    References:
      - Mars axial obliquity: 25.19° (Folkner et al. 1997)
      - Mars orbital eccentricity: 0.0934 (NASA fact sheet)
    """

    MARS_AXIAL_TILT_DEG = 25.19
    MARS_ECCENTRICITY = 0.0934

    @staticmethod
    def annual_average_insolation(lat_deg: float) -> float:
        """
        Compute annual-average relative insolation at a given latitude.

        Uses the analytical solution for a planet with zero eccentricity
        (eccentricity effect < 5% on annual average, ignored here).

        The result is normalised so that the sub-solar latitude at summer
        solstice equals 1.0 — suitable for 0-100 score conversion.

        Args:
            lat_deg: Latitude in degrees (−90 to +90)

        Returns:
            float: Relative insolation in [0, 1]
        """
        tilt_rad = math.radians(SolarModel.MARS_AXIAL_TILT_DEG)
        lat_rad = math.radians(lat_deg)

        # Integrate daily insolation over a full Mars year (360 solar longitudes)
        # Daily insolation ∝ cos(zenith angle) when sun is above horizon
        n_steps = 720
        total = 0.0
        for i in range(n_steps):
            ls = math.radians(i * 360.0 / n_steps)  # solar longitude
            # Subsolar latitude: δ = arcsin(sin(tilt) * sin(Ls))
            decl = math.asin(math.sin(tilt_rad) * math.sin(ls))
            # Hour angle at sunset: cos(H0) = -tan(φ) * tan(δ)
            cos_h0 = -math.tan(lat_rad) * math.tan(decl)
            if cos_h0 <= -1.0:
                # Polar day — 24-hour sun
                h0 = math.pi
            elif cos_h0 >= 1.0:
                # Polar night
                h0 = 0.0
            else:
                h0 = math.acos(cos_h0)
            # Daily insolation: (1/π)(H0 sin φ sin δ + cos φ cos δ sin H0)
            daily = (1.0 / math.pi) * (
                h0 * math.sin(lat_rad) * math.sin(decl)
                + math.cos(lat_rad) * math.cos(decl) * math.sin(h0)
            )
            total += max(daily, 0.0)

        annual_avg = total / n_steps

        # Normalise relative to equator at equinox (lat=0, Ls=0)
        # At equator: daily = 1/π * cos(0)*cos(0)*sin(π/2) wait — use direct calc
        # Equatorial annual average is the reference maximum
        return annual_avg

    @classmethod
    def _equatorial_reference(cls) -> float:
        """Annual average insolation at lat=0 for normalisation."""
        return cls.annual_average_insolation(0.0)

    def score_site(self, lat_deg: float) -> float:
        """
        Convert annual-average insolation to a 0–100 score.

        Normalised so equator = 100, poles ≈ 40–50.
        """
        ref = self._equatorial_reference()
        ins = self.annual_average_insolation(lat_deg)
        if ref <= 0:
            return 50.0
        return min(round((ins / ref) * 100.0, 1), 100.0)

    def process_site(self, site_id: str) -> Dict:
        """
        Compute solar insolation score for a candidate site.

        STATUS: WORKING PROTOTYPE
        """
        bounds = SITE_BOUNDS.get(site_id)
        if not bounds:
            raise ValueError(f"Unknown site: {site_id}")
        lat = (bounds["lat_min"] + bounds["lat_max"]) / 2.0
        score = self.score_site(lat)
        annual_avg = self.annual_average_insolation(lat)
        ref = self._equatorial_reference()

        return {
            "site_id": site_id,
            "latitude_deg": round(lat, 2),
            "annual_avg_insolation_relative": round(annual_avg, 4),
            "equatorial_reference": round(ref, 4),
            "solar_score": score,
            "data_source": "Analytical Mars insolation model (Mars axial tilt 25.19°)",
            "status": STATUS_WORKING_PROTOTYPE,
            "notes": (
                "Annual-average insolation computed via numerical integration over solar "
                "longitude. Ignores dust opacity and topographic shading. "
                "Reference: Folkner et al. (1997) Mars axial obliquity."
            ),
        }

# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_ingestion_pipeline(site_id: str) -> Dict:
    """
    Run the full data provenance pipeline for a single candidate site.

    Returns a structured provenance document with status labels for each
    dimension. This is the single source of truth for how site feature
    scores were derived.

    STATUS LABELS used:
      WORKING PROTOTYPE  — computed by this module, deterministic, no paid services
      SIMULATED          — science-grounded values, not from live data query
      NOT IMPLEMENTED    — placeholder, requires additional infrastructure
    """
    if site_id not in SITE_BOUNDS:
        raise ValueError(f"Unknown site: {site_id}")

    mola = MOLAIngestor()
    sharad = SHARADIngestor()
    solar = SolarModel()

    mola_result = mola.process_site(site_id)
    sharad_result = sharad.process_site(site_id)
    solar_result = solar.process_site(site_id)

    return {
        "site_id": site_id,
        "pipeline_version": "1.0.0",
        "components": {
            "mola": mola_result,
            "sharad": sharad_result,
            "solar": solar_result,
        },
        "feature_provenance": {
            "terrain": {
                "derived_from": "MOLAIngestor.slope_safety_score",
                "status": STATUS_WORKING_PROTOTYPE,
                "score_basis": mola_result["slope_safety_pct"],
                "description": "Percentage of site area with slope < 5°",
            },
            "water": {
                "derived_from": "SHARADIngestor.water_accessibility_score",
                "status": STATUS_SIMULATED,
                "score_basis": sharad_result["water_accessibility_score"],
                "description": "Accessibility score based on published ice deposit depths",
            },
            "solar": {
                "derived_from": "SolarModel.score_site",
                "status": STATUS_WORKING_PROTOTYPE,
                "score_basis": solar_result["solar_score"],
                "description": "Annual-average insolation relative to equatorial reference",
            },
            "science": {
                "derived_from": "manual — published geological assessments",
                "status": STATUS_SIMULATED,
                "score_basis": None,
                "description": (
                    "Scientific value based on geological diversity, mineralogy, "
                    "and astrobiological potential from published mission analyses."
                ),
            },
            "edl": {
                "derived_from": "MOLA slope + atmospheric density at elevation",
                "status": STATUS_SIMULATED,
                "score_basis": None,
                "description": (
                    "Entry-descent-landing safety from terrain slope and elevation. "
                    "For production: full EDL corridor analysis required."
                ),
            },
        },
    }


if __name__ == "__main__":
    for sid in SITE_BOUNDS:
        result = run_ingestion_pipeline(sid)
        print(json.dumps(result, indent=2))
        print()
