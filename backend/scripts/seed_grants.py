#!/usr/bin/env python3
"""
Seed script for Trestle v1 — Populates the grants, eligibility_rules, skills,
and other reference data into Supabase.

Usage:
    cd /Users/harshavardhan/trestle/backend
    python scripts/seed_grants.py

Requirements:
    - .env file with SUPABASE_URL, SUPABASE_SERVICE_KEY
    - supabase Python client (in requirements.txt)
    - seed_grants.json, seed_rules.json, seed_skills.json in app/data/
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Add backend to path so we can import app.config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client, Client


# ── Configuration ──────────────────────────────────────────────────────────

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"
GRANTS_FILE = DATA_DIR / "seed_grants.json"
RULES_FILE = DATA_DIR / "seed_rules.json"
SKILLS_FILE = DATA_DIR / "seed_skills.json"

# ── Helper ─────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_date(val: str | None) -> str | None:
    """Parse ISO date string or return None."""
    if val is None or not str(val).strip():
        return None
    return str(val).strip()


# ── Seed: skills ───────────────────────────────────────────────────────────

def seed_skills(client: Client) -> dict[str, str]:
    """Insert skills idempotently by slug. Returns {slug: id} map."""
    print("── Seeding skills ──")
    with open(SKILLS_FILE) as fh:
        skills = json.load(fh)

    slug_id: dict[str, str] = {}
    inserted = 0
    skipped = 0

    for skill in skills:
        slug = skill["slug"]
        # Check existing
        existing = (
            client.table("skills")
            .select("id")
            .eq("slug", slug)
            .is_("deleted_at", "null")
            .execute()
        )
        if existing.data:
            sid = existing.data[0]["id"]
            slug_id[slug] = sid
            skipped += 1
            print(f"  ✓ Skill '{slug}' already exists (id={sid})")
            continue

        payload = {
            "slug": slug,
            "name": skill["name"],
            "description": skill.get("description"),
            "status": skill["status"],
            "required_profile_fields": skill.get("required_profile_fields", []),
            "config_json": skill.get("config_json", {}),
        }
        result = client.table("skills").insert(payload).execute()
        sid = result.data[0]["id"]
        slug_id[slug] = sid
        inserted += 1
        print(f"  + Inserted skill '{slug}' (id={sid})")

    print(f"  Skills: {inserted} inserted, {skipped} skipped\n")
    return slug_id


# ── Seed: eligibility_rules ────────────────────────────────────────────────

def seed_rules(client: Client) -> None:
    """Upsert eligibility matching rules into a metadata/settings table or
    just validate they parse correctly. (Rules are engine config — logged.)"""
    print("── Seeding eligibility rules ──")
    with open(RULES_FILE) as fh:
        rules = json.load(fh)

    print(f"  Loaded {len(rules)} eligibility matching rules")
    for rule in rules:
        print(f"    • {rule['slug']}: {rule['name']} (weight={rule.get('weight', 1.0)})")

    # Rules are consumed by the matching engine at runtime from the JSON file.
    # If you add a `matching_rules` table later, upsert here by slug.
    print("  Rules validated (engine loads from file at runtime)\n")


# ── Seed: grants ───────────────────────────────────────────────────────────

def seed_grants(client: Client) -> int:
    """Insert grants idempotently by (source, source_id)."""
    print("── Seeding grants ──")
    with open(GRANTS_FILE) as fh:
        grants = json.load(fh)

    inserted = 0
    skipped = 0
    errors = 0

    for grant in grants:
        source = grant["source"]
        source_id = grant.get("source_id")
        name = grant["name"]

        # Build lookup: source + source_id
        if source_id:
            existing = (
                client.table("grants")
                .select("id,name")
                .eq("source", source)
                .eq("source_id", source_id)
                .is_("deleted_at", "null")
                .execute()
            )
        else:
            # Fall back to name match for grants without source_id
            existing = (
                client.table("grants")
                .select("id,name")
                .eq("source", source)
                .eq("name", name)
                .is_("deleted_at", "null")
                .execute()
            )

        if existing.data:
            skipped += 1
            gid = existing.data[0]["id"]
            gname = existing.data[0]["name"]
            print(f"  ✓ [{source}] {gname} already exists (id={gid})")
            continue

        # Parse deadline
        deadline_val = _parse_date(grant.get("deadline"))

        payload = {
            "source": source,
            "source_id": source_id,
            "name": name,
            "description": grant.get("description"),
            "amount_min_usd": grant.get("amount_min_usd"),
            "amount_max_usd": grant.get("amount_max_usd"),
            "deadline": deadline_val,
            "status": grant.get("status", "open"),
            "eligibility_rules": grant.get("eligibility_rules", {}),
            "tags": grant.get("tags", []),
            "source_url": grant["source_url"],
            "url_is_live": grant.get("url_is_live", True),
            "metadata_json": grant.get("metadata_json", {}),
        }

        try:
            result = client.table("grants").insert(payload).execute()
            gid = result.data[0]["id"]
            inserted += 1
            print(f"  + [{source}] {name} inserted (id={gid})")
        except Exception as exc:
            errors += 1
            print(f"  ✗ [{source}] {name} FAILED: {exc}")

    print(f"  Grants: {inserted} inserted, {skipped} skipped, {errors} errors\n")
    return inserted


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 72)
    print("  Trestle v1 — Seed Grants Database")
    print(f"  Supabase URL: {SUPABASE_URL}")
    print(f"  Timestamp:    {_now_iso()}")
    print("=" * 72)
    print()

    # Validate data files exist
    for path in [GRANTS_FILE, RULES_FILE, SKILLS_FILE]:
        if not path.exists():
            print(f"✗ Missing data file: {path}")
            sys.exit(1)
    print("✓ All data files found\n")

    client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    try:
        seed_skills(client)
        seed_rules(client)
        seed_grants(client)
        print("=" * 72)
        print("  Seed complete.")
        print("=" * 72)
    except Exception as exc:
        print(f"\n✗ Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
