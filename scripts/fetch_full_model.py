"""Download and convert the full climate model to binary format.

Usage (PowerShell):
  python scripts/fetch_full_model.py --url https://example.com/model-source.dat

This script:
1. Downloads the raw model (could be compressed)
2. Performs a placeholder conversion step
3. Writes binary file to data/models/climate_full.bin

Customize conversion logic according to real model structure.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import sys
from pathlib import Path
import urllib.request
from app.core.config import get_settings


def download(url: str) -> bytes:
    with urllib.request.urlopen(url) as resp:  # nosec - instructional
        return resp.read()


def maybe_decompress(data: bytes, decompress: bool) -> bytes:
    if decompress:
        return gzip.decompress(data)
    return data


def convert_to_binary(raw: bytes) -> bytes:
    # Placeholder: in real case parse/serialize structured parameters
    header = b"CLIMODEL\x00"
    digest = hashlib.sha256(raw).digest()
    return header + digest + raw


def main():
    parser = argparse.ArgumentParser(description="Fetch full climate model")
    parser.add_argument("--url", required=True, help="Source URL of model (raw or gz)")
    parser.add_argument("--gz", action="store_true", help="Indicates input is gzipped")
    parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()

    settings = get_settings()
    out_path = settings.model_dir / settings.model_filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not args.force:
        print(f"File already exists: {out_path} (use --force to overwrite)")
        sys.exit(0)

    print(f"Downloading {args.url} ...")
    raw = download(args.url)
    raw = maybe_decompress(raw, args.gz)
    print(f"Downloaded {len(raw)} bytes.")
    binary = convert_to_binary(raw)
    with open(out_path, "wb") as f:
        f.write(binary)
    print(f"Wrote model binary: {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
