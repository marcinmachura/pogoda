# Climate API & CLI

A learning project using FastAPI that exposes climate classification data for a place and year range. Data is synthetic & deterministic for demonstration/testing.

## Features
- FastAPI backend with versioned route `/api/v1/climate`
- Query parameters: `place`, `start_year`, `end_year`, `aggregate`
- Optional aggregate summary (mean temp, total precipitation, dominant classification)
- Deterministic pseudo-random data generation for consistency
- Simple CLI script producing same output as API
 - Pluggable binary climate model (full vs sample) with lazy loading

## Install
```bash
pip install -r requirements.txt
```

If you intend to use the large model (≈400MB) ensure you have enough disk space.

## Run API (development)
```bash
uvicorn app.main:app --reload
```
Navigate to: http://127.0.0.1:8000/docs

Example request:
```
GET /api/v1/climate?place=Berlin&start_year=2000&end_year=2005&aggregate=true
```

## Model Files

Directory layout:
```
data/models/
	climate_full.bin        # (ignored by git) full model (~400MB)
	climate_sample.bin      # small test model (~1MB) commit-friendly
	sample/                 # optional additional tiny artifacts
```

### Using the Sample Model
Set environment variable to force sample usage:
```bash
set USE_SAMPLE_MODEL=1   # Windows PowerShell: $env:USE_SAMPLE_MODEL=1
```
Or create a `.env` file:
```
USE_SAMPLE_MODEL=1
```

### Download & Convert Full Model
Run the helper script (replace URL):
```bash
python scripts/fetch_full_model.py --url https://example.com/climate_model_raw.gz --gz
```
Result will appear at `data/models/climate_full.bin`.

### Loader
`app/climate/model_loader.py` exposes `load_model()` which memory-maps the binary. Integrate it inside services when real model logic is added.

### Why Ignore Large File?
Keeping huge binaries out of git keeps repo lean. For shared distribution consider:
- Release assets
- Object storage (S3 / Azure Blob)
- Git LFS (less preferred for rapidly changing large models)

## Configuration
Environment-driven settings (see `app/core/config.py`). Key variables:
- `MODEL_DIR` (default: `data/models`)
- `MODEL_FILENAME` (default: `climate_full.bin`)
- `SAMPLE_MODEL_FILENAME` (default: `climate_sample.bin`)
- `USE_SAMPLE_MODEL` (toggle sample vs full)

## CLI Usage
```bash
python scripts/cli.py Berlin 2000 2005 --aggregate
```

## Tests
```bash
pytest -q
```

## Next Steps / Ideas
- Replace synthetic data with real dataset source
- Add caching layer (e.g., Redis) for computed aggregates
- Add authentication (API keys / OAuth2)
- Implement pagination or streaming for very large year ranges
- Add monthly breakdown and true Köppen classification
 - Integrate real model inference using loaded binary
 - Add checksum validation for model integrity
 - Async model fetch & warmup task

## License
MIT (adjust as needed)
