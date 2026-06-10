from __future__ import annotations
import json
import os
import time
from typing import Dict, List

CACHE_META_VERSION = 1

def _cache_filename(lat: float, lon: float, year: int) -> str:
    # Use 4 decimal places; include signs; replace minus with 'm' to keep filename simple
    def fmt(v: float) -> str:
        s = f"{v:+.4f}"  # + sign always
        return s.replace('-', 'm').replace('+','p')
    return f"{fmt(lat)}_{fmt(lon)}_{year}.json"

def load_cached(lat: float, lon: float, year: int, cache_dir: str) -> Dict[str, List[float]] | None:
    path = os.path.join(cache_dir, _cache_filename(lat, lon, year))
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('version') != CACHE_META_VERSION:
            return None
        if 'payload' not in data:
            return None
        return data['payload']
    except (OSError, json.JSONDecodeError):
        return None

def store_cache(lat: float, lon: float, year: int, cache_dir: str, payload: Dict[str, List[float]]) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, _cache_filename(lat, lon, year))
    meta = {
        'version': CACHE_META_VERSION,
        'lat': lat,
        'lon': lon,
        'year': year,
        'timestamp': time.time(),
        'payload': payload,
    }
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    os.replace(tmp_path, path)
