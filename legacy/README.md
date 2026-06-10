# pogoda

Köppen climate classifier using NASA POWER data.

## Features
- Geocode a city name to coordinates (OpenStreetMap Nominatim via geopy)
- Fetch monthly meteorological data (temperature & precipitation) from NASA POWER
- Compute Köppen climate classification (baseline implementation)
- Simple CLI

## Install (editable)

### Using Conda
```bash
conda env create -f environment.yml
conda activate pogoda
pip install -e .
```

### Using venv / pip
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .
```

## Usage
```bash
pogoda classify "Szczecin" --year 2024 --scheme both

# Multiple years (range) aggregate (default)
pogoda classify "Szczecin" --year 2000-2005 --scheme koppen

# Both aggregate and per-year
pogoda classify "Szczecin" --year 2000-2005 --scheme both --multi-mode both

# Multiple disjoint years / ranges
pogoda classify "Szczecin" --year 1995,2000-2002,2024 --scheme both
```

### Example (Szczecin)
Expected Köppen code is typically Cfb (temperate oceanic) for modern normals. Yearly variation can shift third letter rarely; if you see a different code, inspect annual mean temperature, warmest month, and precipitation distribution. Multi-year output lists a line per year with summary stats.

### Trewartha Support
### Caching
By default, fetched yearly data can be cached. Use:

```
pogoda classify "Warsaw" --year 2000-2005 --scheme both --cache-dir .cache
```

Disable cache:
```
pogoda classify "Warsaw" --year 2000-2005 --no-cache
```

Force refresh ignoring existing cached files:
```
pogoda classify "Warsaw" --year 2000-2005 --force-refresh
```

You can choose `--scheme trewartha` or `--scheme both` to also compute the simplified Trewartha classification. This implementation:
- Uses Köppen-style dryness threshold
- Groups by count of months ≥10°C (A: ≥8, C: 4–7, D: 1–3, E: 0) with dry (B) overriding
- Adds seasonality letters (f,s,w) with stricter ratio-based rule
- Subdivides dry climates into BW/BS and temperature qualifier h/k

Output example:
```
City: Szczecin (53.4285, 14.5528) Year: 2024
Koppen: Cfb
Details: {...}
```

## Köppen Logic Implemented
- Main groups A, B, C, D, E
- Second letter for precipitation (f, s, w) using seasonal precipitation distribution
- Third letter for temperature where applicable (a, b, c, d), basic oceanic distinctions

Edge cases and alpine (H) not yet implemented. Arctic/ice ET/EF based on warmest month thresholds (10°C / 0°C).

## NASA POWER Notes
- Monthly data is available (Yes) and used here.
- API base: https://power.larc.nasa.gov/

## Roadmap
- Add Trewartha classification
- Add caching & retry logic
- Add unit tests for more boundary cases
- Add optional alternate data source fallback
- Year-over-year comparison tool

## License
MIT
