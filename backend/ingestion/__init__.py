"""Trestle Grant Ingestion Pipeline.

Modules:
- fetchers/   : source-specific API clients (Grants.gov, NSF, SBIR.gov)
- normalizer  : map arbitrary source records → Supabase `grants` row shape
- pipeline    : orchestrator: fetch → normalize → validate → dedup → upsert
- cli         : CLI entry point (`python -m backend.ingestion`)
"""
