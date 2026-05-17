"""Seed Michigan baseline resources into Supabase.

Usage:
    python scripts/seed_michigan.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from supabase import create_client, Client

# Load env from backend/.env
env_path = Path(__file__).parent.parent / "backend" / ".env"
if env_path.exists():
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key, val)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

TABLE = "resources"
DATA_FILE = Path(__file__).parent / "data" / "michigan_baseline.json"


def seed():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    with DATA_FILE.open() as f:
        resources = json.load(f)

    # Check existing count
    existing = supabase.table(TABLE).select("id", count="exact").execute()
    print(f"Existing resources: {existing.count}")

    inserted = 0
    skipped = 0

    for res in resources:
        # Check if already exists by name + url
        name = res.get("name", "")
        url = res.get("url", "")
        check = (
            supabase.table(TABLE)
            .select("id")
            .eq("name", name)
            .eq("url", url)
            .execute()
        )
        if check.data:
            skipped += 1
            continue

        result = supabase.table(TABLE).insert(res).execute()
        if result.data:
            inserted += 1
            print(f"  + {name}")
        else:
            print(f"  ✗ Failed: {name} — {result}")

    print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}, Total in DB: {existing.count + inserted}")


if __name__ == "__main__":
    seed()
