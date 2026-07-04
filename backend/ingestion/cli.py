"""CLI entry point for the Trestle grant ingestion pipeline.

Usage:
    cd backend
    source .venv/bin/activate
    python -m backend.ingestion

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY (from .env)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure backend is on path when run as __main__
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.ingestion.fetchers.grants_gov import GrantsGovFetcher
from backend.ingestion.fetchers.nsf import NSFFetcher
from backend.ingestion.fetchers.sbir_gov import SBIRGovFetcher
from backend.ingestion.pipeline import IngestionPipeline


def _load_env() -> None:
    env_file = BACKEND_ROOT.parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)


def _required_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        sys.exit(1)
    return url, key


async def main() -> int:
    _load_env()
    url, key = _required_env()

    pipeline = IngestionPipeline(url, key)

    fetchers = [
        GrantsGovFetcher(),
        NSFFetcher(),
    ]

    result = await pipeline.run(fetchers)

    print("\n═ TRESTLE GRANT INGESTION RESULT ═\n")
    print(f"  Raw fetched      : {result['raw_fetched']}")
    print(f"  Normalized       : {result['normalized']}")
    print(f"  Valid rows       : {result['valid']}")
    print(f"  Invalid rows     : {len(result['invalid'])}")
    print(f"  Inserted         : {result['inserted']}")
    print(f"  Updated          : {result['updated']}")
    print(f"  Errors           : {result['errors']}")
    print(f"  Duration         : {result['duration_seconds']:.1f}s")
    print(f"  Finished at      : {result['finished_at']}")

    if result["invalid"]:
        print("\n  ⚠ Invalid rows (first 5):")
        for inv in result["invalid"][:5]:
            print(f"    - {inv['source_id']}: {inv['reason']}")

    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
