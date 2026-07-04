"""Pipeline orchestrator: fetch → normalize → validate → dedup → upsert.

All operations are idempotent — re-running the pipeline with the same data
produces zero net inserts and only updates changed fields.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from supabase import Client, create_client

from backend.ingestion.normalizer import normalize_batch

logger = structlog.get_logger(__name__)

# Fields required by the Supabase grants table (must be non-null)
_REQUIRED_FIELDS = ("source", "source_id", "name", "description", "source_url")


def _validate(row: dict[str, Any]) -> tuple[bool, str]:
    for f in _REQUIRED_FIELDS:
        if not row.get(f):
            return False, f"missing {f}"
    return True, ""


class IngestionPipeline:
    """Orchestrates one or more fetchers and writes results to Supabase."""

    def __init__(
        self,
        supabase_url: str,
        supabase_service_key: str,
        max_concurrent_fetchers: int = 3,
    ):
        self.supabase_url = supabase_url
        self.supabase_service_key = supabase_service_key
        self.client: Client | None = None
        self.max_concurrent = max_concurrent_fetchers

    async def _init_client(self) -> Client:
        if self.client is None:
            self.client = create_client(self.supabase_url, self.supabase_service_key)
        return self.client

    # ── Fetch ──────────────────────────────────────────────────────────────────

    async def _run_fetcher(self, fetcher: Any) -> list[dict[str, Any]]:
        """Execute a single fetcher and return raw records."""
        try:
            async with fetcher:
                records = await fetcher.fetch_all()
                logger.info(
                    "fetcher_done",
                    fetcher=fetcher.__class__.__name__,
                    count=len(records),
                )
                return records
        except Exception as exc:
            logger.error(
                "fetcher_failed",
                fetcher=fetcher.__class__.__name__,
                error=str(exc),
            )
            return []

    async def fetch(self, fetchers: list[Any]) -> list[dict[str, Any]]:
        """Run all fetchers concurrently (bounded)."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _bounded(f: Any) -> list[dict[str, Any]]:
            async with semaphore:
                return await self._run_fetcher(f)

        tasks = [asyncio.create_task(_bounded(f)) for f in fetchers]
        results = await asyncio.gather(*tasks)
        flat: list[dict[str, Any]] = []
        for r in results:
            flat.extend(r)
        logger.info("fetch_total", total=len(flat))
        return flat

    # ── Normalize ──────────────────────────────────────────────────────────────

    @staticmethod
    def normalize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = normalize_batch(records)
        logger.info("normalize_done", in_count=len(records), out_count=len(normalized))
        return normalized

    # ── Validate ───────────────────────────────────────────────────────────────

    @staticmethod
    def validate(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid: list[dict[str, Any]] = []
        invalid: list[dict[str, Any]] = []
        for row in rows:
            ok, reason = _validate(row)
            if ok:
                valid.append(row)
            else:
                invalid.append({"source_id": row.get("source_id"), "reason": reason})
        logger.info("validate_done", valid=len(valid), invalid=len(invalid))
        return valid, invalid

    # ── Upsert ─────────────────────────────────────────────────────────────────

    async def upsert(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        """Idempotent batch upsert into Supabase `grants` table.
        Uses service role key so RLS doesn't block.
        Deduplicates by (source, source_id).
        Strategy:
          1. In-memory dedupe by (source, source_id).
          2. Fetch all existing (source, source_id) → id mappings in one query.
          3. Batch insert new rows, batch update existing rows.
        """
        client = await self._init_client()

        # ── 1. In-memory dedupe ──────────────────────────────────────────────
        deduped: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = f"{row['source']}:{row['source_id']}"
            if key not in deduped:
                deduped[key] = row
            else:
                existing = deduped[key]
                if (row.get("last_synced_at") or "") > (existing.get("last_synced_at") or ""):
                    deduped[key] = row

        items = list(deduped.values())
        if not items:
            return {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0, "total_processed": 0}

        # ── 2. Bulk fetch existing IDs ───────────────────────────────────────
        # Supabase REST has a URL length cap; paginate source_id filter in batches
        batch_size = 20
        existing_map: dict[str, str] = {}  # "source:source_id" → id
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            try:
                source_ids = [r["source_id"] for r in batch]
                resp = (
                    client.table("grants")
                    .select("id,source,source_id")
                    .in_("source_id", source_ids)
                    .is_("deleted_at", "null")
                    .execute()
                )
                for rec in resp.data:
                    key = f"{rec['source']}:{rec['source_id']}"  # type: ignore[index]
                    existing_map[key] = rec["id"]  # type: ignore[index]
            except Exception as exc:
                logger.error("bulk_lookup_error", batch=i, error=str(exc))

        to_insert: list[dict[str, Any]] = []
        to_update: list[tuple[str, dict[str, Any]]] = []  # (id, payload)
        now_iso = datetime.now(timezone.utc).isoformat()

        for row in items:
            key = f"{row['source']}:{row['source_id']}"
            payload = dict(row)
            payload.pop("id", None)
            payload.pop("created_at", None)
            payload["updated_at"] = now_iso
            if key in existing_map:
                to_update.append((existing_map[key], payload))
            else:
                to_insert.append(payload)

        inserted = 0
        updated = 0
        errors = 0

        # ── 3. Batch insert ──────────────────────────────────────────────────
        for i in range(0, len(to_insert), batch_size):
            batch = to_insert[i : i + batch_size]
            try:
                resp = client.table("grants").insert(batch).execute()
                inserted += len(resp.data)
            except Exception as exc:
                errors += len(batch)
                logger.error("batch_insert_error", batch=i, error=str(exc))

        # ── 4. Batch update (REST client is row-by-row; one call per row) ──
        for rec_id, payload in to_update:
            try:
                client.table("grants").update(payload).eq("id", rec_id).execute()
                updated += 1
            except Exception as exc:
                errors += 1
                logger.error("update_error", id=rec_id, error=str(exc))

        stats = {
            "inserted": inserted,
            "updated": updated,
            "skipped": 0,
            "errors": errors,
            "total_processed": len(items),
        }
        logger.info("upsert_done", **stats)
        return stats

    # ── Full run ─────────────────────────────────────────────────────────────

    async def run(self, fetchers: list[Any]) -> dict[str, Any]:
        """End-to-end pipeline."""
        t0 = datetime.now(timezone.utc)
        raw = await self.fetch(fetchers)
        normalized = self.normalize(raw)
        valid, invalid = self.validate(normalized)
        stats = await self.upsert(valid)
        t1 = datetime.now(timezone.utc)
        return {
            "started_at": t0.isoformat(),
            "finished_at": t1.isoformat(),
            "duration_seconds": (t1 - t0).total_seconds(),
            "raw_fetched": len(raw),
            "normalized": len(normalized),
            "valid": len(valid),
            "invalid": invalid,
            **stats,
        }
