#!/usr/bin/env python3
"""
Download an EDI/PASTA data package as a ZIP archive given its DOI.

Example:
  python scripts/download_edi_zip.py \
    --doi 10.6073/pasta/7ac5818bb45bb42c2d935ce7e3756c00 \
    --out data/edi_package.zip
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

PASTA_BASE = "https://pasta.lternet.edu"


def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = doi.removeprefix("https://doi.org/")
    doi = doi.removeprefix("doi:")
    return doi


def doi_to_pasta_segments(doi: str) -> tuple[str, str, str]:
    """
    PASTA 'read package from doi' expects:
      /package/doi/{shoulder}/{pasta}/{md5}

    For EDI DOIs of the form:
      10.6073/pasta/<32-hex-md5>
    """
    doi = normalize_doi(doi)

    m = re.fullmatch(r"10\.6073/pasta/([0-9a-f]{32})", doi)
    if not m:
        raise ValueError(
            "Expected DOI like 10.6073/pasta/<32-hex-md5>. "
            f"Got: {doi}"
        )

    shoulder = "doi:10.6073"
    pasta_literal = "pasta"
    md5 = m.group(1)
    return shoulder, pasta_literal, md5


def resolve_package_id(doi: str) -> tuple[str, str, str]:
    """
    GET /package/doi/... returns a resource map (plain text URLs).
    We extract the /package/eml/{scope}/{identifier}/{revision} URL.
    """
    shoulder, pasta_literal, md5 = doi_to_pasta_segments(doi)
    url = f"{PASTA_BASE}/package/doi/{shoulder}/{pasta_literal}/{md5}"

    r = requests.get(url, timeout=60)
    r.raise_for_status()

    lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]
    eml_url = next((ln for ln in lines if "/package/eml/" in ln), None)
    if not eml_url:
        raise RuntimeError(f"Could not find an EML URL in resource map:\n{r.text}")

    path = urlparse(eml_url).path.strip("/")
    parts = path.split("/")
    # expected: package/eml/<scope>/<identifier>/<revision>
    try:
        i = parts.index("eml")
        scope, identifier, revision = parts[i + 1], parts[i + 2], parts[i + 3]
    except Exception as e:
        raise RuntimeError(f"Unexpected EML URL format: {eml_url}") from e

    return scope, identifier, revision


def create_archive_transaction(scope: str, identifier: str, revision: str) -> str:
    """
    POST /package/archive/eml/{scope}/{identifier}/{revision} returns a transaction id (plain text).
    """
    url = f"{PASTA_BASE}/package/archive/eml/{scope}/{identifier}/{revision}"
    r = requests.post(url, timeout=60)
    r.raise_for_status()
    tx = r.text.strip()
    if not tx:
        raise RuntimeError("Archive transaction id was empty.")
    return tx


def download_archive(scope: str, identifier: str, revision: str, tx: str, out_path: Path) -> None:
    """
    GET /package/archive/eml/{scope}/{identifier}/{revision}/{tx} downloads the ZIP.
    """
    url = f"{PASTA_BASE}/package/archive/eml/{scope}/{identifier}/{revision}/{tx}"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doi", required=True, help="e.g., 10.6073/pasta/<md5> or https://doi.org/10.6073/pasta/<md5>")
    ap.add_argument("--out", default="data/edi_package.zip", help="Output ZIP path (default: data/edi_package.zip)")
    args = ap.parse_args()

    out_path = Path(args.out)

    scope, identifier, revision = resolve_package_id(args.doi)
    print(f"Resolved DOI -> package: {scope}.{identifier}.{revision}")

    tx = create_archive_transaction(scope, identifier, revision)
    print(f"Archive transaction: {tx}")

    download_archive(scope, identifier, revision, tx, out_path)
    print(f"Saved ZIP: {out_path.resolve()}")


if __name__ == "__main__":
    main()
