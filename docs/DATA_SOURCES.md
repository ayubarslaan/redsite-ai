# NASA Data Sources Guide — RedSite AI

This document catalogs all public data sources used by RedSite AI for Mars site intelligence.

---

## 1. MOLA DEM (Mars Orbiter Laser Altimeter Digital Elevation Model)

**What it provides:** Global topographic map of Mars at ~463m/px resolution (MEgDR) and higher resolution along tracks.

**How we use it:**
- Compute slope safety grids (percentage of area with slope < 5°)
- Determine elevation for EDL (entry-descent-landing) suitability
- Generate terrain roughness metrics

**Access:**
- **WUSTL Orbital Data Explorer:** https://ode.rsl.wustl.edu/mars/
- **NASA PDS Geosciences Node:** https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/
- **PGDA (Planetary Geospatial Data Archive):** https://pgda.gsfc.nasa.gov/products/62

**Products:**
- `megtXXnXXXhb.img` — MEgDR tiles (1/128° per pixel, ~463m)
- `medrXXnXXXhb.img` — MEdR reduced resolution (~2km/px)

**Citation:** Smith et al. (2001), "Mars Orbiter Laser Altimeter: Experiment summary after the first year of global mapping of Mars," JGR-Planets.

---

## 2. SHARAD (Shallow Radar)

**What it provides:** Subsurface radar sounding data detecting buried ice and layering.

**How we use it:**
- Map subsurface ice deposits and their depths
- Score water accessibility (shallow ice = higher score)
- Assess ice confidence levels

**Access:**
- **NASA PDS Geosciences Node:** https://pds-geosciences.wustl.edu/missions/mro/sharad.htm
- **USGS Astrogeology:** https://astrogeology.usgs.gov/search/map/Mars/MRO/SHARAD

**Key publications:**
- Plaut et al. (2009), "Radar evidence for ice in lobate debris aprons in the mid-northern latitudes of Mars," GRL.
- Stuurman et al. (2016), "SHARAD detection and characterization of subsurface water ice," JGR-Planets.

---

## 3. HiRISE (High Resolution Imaging Science Experiment)

**What it provides:** Ultra-high resolution imagery of Mars surface (~0.25-0.5m/px).

**How we use it:**
- Terrain classification via CNN (safe, rocky, dune, cratered)
- Rock abundance estimation for landing safety
- Visual validation of MOLA-derived slope calculations

**Access:**
- **USGS Astrogeology STAC:** https://stac.astrogeology.usgs.gov/docs/data/mars/uncontrolled_hirise/
- **HiRISE Catalog:** https://www.uahirise.org/catalog/
- **NASA PDS:** https://pds-imaging.jpl.nasa.gov/volumes/hirise.html

**Citation:** McEwen et al. (2007), "Mars Reconnaissance Orbiter's High Resolution Imaging Science Experiment (HiRISE)," JGR-Planets.

---

## 4. CRISM (Compact Reconnaissance Imaging Spectrometer for Mars)

**What it provides:** Visible-infrared spectral data for mineral identification.

**How we use it:**
- Mineralogy indices (olivine, pyroxene, hydrated minerals)
- Scientific value scoring (diverse mineralogy = higher science score)
- Water-related mineral detection (phyllosilicates, sulfates)

**Access:**
- **NASA PDS Geosciences Node:** https://pds-geosciences.wustl.edu/missions/mro/crism.htm
- **JMARS (Java Mission-planning and Analysis for Remote Sensing):** https://jmars.mars.asu.edu/

---

## 5. Solar Insolation Model

**What it provides:** Solar energy potential at Mars surface by latitude and season.

**How we use it:**
- Score solar potential for each candidate site
- Estimate solar panel requirements for human missions
- Account for seasonal dust storm effects

**Method:** Simplified orbital mechanics model using Mars axial tilt (25.19°) and orbital eccentricity. For production, would integrate:
- **Mars Climate Database:** https://www-mars.lmd.jussieu.fr/mars/access.html
- **AMES GCM outputs**

---

## 6. Mars Landing Site Engineering Constraints

**Source:** NASA Engineering and Safety Center, Mars Landing Site Selection Criteria

**Key constraints we enforce:**
- Elevation: < -2 km preferred (more atmosphere for EDL deceleration)
- Slope: < 5° over 10m length scale (human mission requirement)
- Rock abundance: < 5% coverage at 1m scale
- Latitude: ±30° preferred for solar; polar for ice

**References:**
- Golombek et al. (2012), "Selection of the Mars Science Laboratory landing site," Space Science Reviews.
- Steltzner et al. (2022), "Mars 2020 Entry, Descent, and Landing System," IEEE Aerospace.

---

## 7. SpaceX Starship Landing Site Studies

**Relevance:** Commercial Mars landing site evaluations inform our candidate selection.

**Key publications:**
- Paul et al. (2022), "SpaceX Starship landing sites on Mars," LPI Contribution No. 2548.
- Various LPSC abstracts on Starship EDL and site constraints.

---

## Data Pipeline Notes

### For Challenge Submission (MVP)

The current MVP uses **pre-computed site features** derived from the above sources. This allows the demo to run without:
- Downloading multi-GB planetary raster datasets
- Requiring GDAL/PostGIS installation for judges
- Long processing times

### For Production Deployment

The full pipeline (`backend/data_ingest.py`) would:
1. Fetch MOLA tiles via HTTP from WUSTL ODE
2. Process rasters with GDAL/rasterio
3. Query SHARAD track database for ice detections
4. Run HiRISE patches through the terrain CNN
5. Store results in PostGIS for spatial queries

---

## License & Attribution

All NASA planetary data is **public domain** (U.S. Government work). RedSite AI does not claim ownership of any NASA data. We provide this tool as a value-added analysis layer on top of publicly available scientific datasets.

**Suggested citation if using RedSite AI for research:**
> RedSite AI (2026). Mars Site Intelligence & Decision Engine. IBM AI Builders Challenge. https://github.com/your-org/redsite-ai
