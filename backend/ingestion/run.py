#!/usr/bin/env python3
import asyncio, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
env_path = Path('/Users/harshavardhan/trestle') / '.env'
load_dotenv(dotenv_path=env_path)

from backend.ingestion.fetchers.grants_gov import GrantsGovFetcher
from backend.ingestion.fetchers.nsf import NSFFetcher
from backend.ingestion.fetchers.sbir_gov import SBIRGovFetcher
from backend.ingestion.pipeline import IngestionPipeline

async def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Missing SUPABASE env vars")
        return 1

    pipeline = IngestionPipeline(url, key)
    result = await pipeline.run([
        GrantsGovFetcher(),
        NSFFetcher(),
    ])

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
        print("\n  Invalid rows (first 5):")
        for inv in result["invalid"][:5]:
            print(f"    - {inv.get('source_id')}: {inv.get('reason')}")
    return 0 if result["errors"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
