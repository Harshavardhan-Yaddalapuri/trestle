"""Normalizer — maps raw API records → Supabase `grants` row shape.

Supabase `grants` schema:
  source, source_id, name, description,
  amount_min_usd, amount_max_usd, deadline,
  status, eligibility_rules, tags,
  source_url, url_is_live, url_status_code,
  metadata_json, last_synced_at

Each source (grants.gov, sbir.gov, etc.) may return different field names.
We inspect `_trestle_source` and `_trestle_via` tags injected by fetchers.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any


def _parse_date(s: str | None) -> date | None:
    if not s or not str(s).strip():
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _money(val: str | int | float | None) -> int | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


def _sanitize_text(val: str | None, max_len: int = 4000) -> str:
    if not val:
        return ""
    txt = str(val).strip()
    # Strip HTML-ish entities (lightweight)
    txt = re.sub(r"&[a-zA-Z]+;", "", txt)
    return txt[:max_len]


def _dedupe_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        low = t.lower().strip()
        if low and low not in seen:
            seen.add(low)
            out.append(low)
    return out


# ── Grants.gov specific ────────────────────────────────────────────────────

def _normalize_grants_gov(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a single Grants.gov oppHit record."""
    opp_id = str(raw.get("id") or raw.get("number") or "").strip()
    if not opp_id:
        return None

    title = _sanitize_text(raw.get("title"), 500)
    if not title:
        return None

    synopsis = raw.get("estimatedSynopsis", {}) or {}
    desc = _sanitize_text(
        synopsis.get("synopsisDesc") or synopsis.get("fundingDesc") or title,
        4000,
    )

    # Agency → source
    agency = raw.get("agency", "Grants.gov")

    # Money — Grants.gov search2 oppHits never contain money, but some seed data does
    est = raw.get("estimatedSynopsis", {}) or {}
    amount_max = _money(est.get("estimatedAwardMax"))
    amount_min = _money(est.get("estimatedAwardMin"))

    # Dates
    deadline = _parse_date(raw.get("closeDate"))

    # Status mapping
    gg_status = raw.get("oppStatus", "").lower()
    if gg_status == "posted":
        status = "open"
    elif gg_status == "forecasted":
        status = "upcoming"
    elif gg_status == "closed":
        status = "archived"
    else:
        status = "open"

    # Rolling detection
    rolling = False
    if "rolling" in title.lower() or "continuous" in title.lower():
        rolling = True
        status = "rolling"

    # URL
    opp_num = raw.get("number", opp_id)
    source_url = f"https://grants.gov/opportunities/{opp_num}"

    # Eligibility rules (best-effort from Grants.gov fields)
    eligibility: dict[str, Any] = {}
    elig = raw.get("eligibility", {})
    if elig:
        eligibility["applicant_eligibility"] = elig.get("applicantEligibility")
    if raw.get("cfdaList"):
        eligibility["cfda_numbers"] = raw.get("cfdaList")

    # Tags
    tags: list[str] = ["grants.gov"]
    fi_type = raw.get("fundingInstrumentType") or est.get("fundingInstrumentType")
    if fi_type:
        tags.append(str(fi_type).lower())
    if "SBIR" in title.upper() or "SBIR" in opp_num.upper():
        tags.append("sbir")
    if "STTR" in title.upper():
        tags.append("sttr")

    # Metadata
    metadata: dict[str, Any] = {
        "grants_gov_id": raw.get("id"),
        "grants_gov_number": opp_num,
        "agency_code": raw.get("agencyCode"),
        "doc_type": raw.get("docType"),
        "open_date": raw.get("openDate"),
        "cfda_list": raw.get("cfdaList"),
        "funding_instrument_type": fi_type,
    }
    if est:
        metadata["estimated_synopsis"] = est

    return {
        "source": agency,
        "source_id": opp_num,
        "name": title,
        "description": desc,
        "amount_min_usd": amount_min,
        "amount_max_usd": amount_max,
        "deadline": deadline.isoformat() if deadline else None,
        "status": status,
        "eligibility_rules": eligibility,
        "tags": _dedupe_tags(tags),
        "source_url": source_url,
        "url_is_live": True,
        "url_status_code": None,
        "metadata_json": metadata,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }


# ── SBIR.gov specific ──────────────────────────────────────────────────────

def _normalize_sbir_gov(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a raw SBIR.gov API record (if available)."""
    sol_num = str(raw.get("solicitation_number") or raw.get("number") or raw.get("id") or "").strip()
    if not sol_num:
        return None

    title = _sanitize_text(raw.get("title") or raw.get("name"), 500)
    if not title:
        return None

    agency = raw.get("agency", "SBIR.gov")
    desc = _sanitize_text(raw.get("description") or raw.get("abstract") or title, 4000)
    deadline = _parse_date(raw.get("close_date") or raw.get("deadline"))
    amount_max = _money(raw.get("award_max"))
    amount_min = _money(raw.get("award_min"))

    tags: list[str] = ["sbir.gov", "sbir"]
    if "STTR" in title.upper():
        tags.append("sttr")

    metadata: dict[str, Any] = {
        "sbir_gov_id": raw.get("id"),
        "solicitation_number": sol_num,
    }

    return {
        "source": agency,
        "source_id": sol_num,
        "name": title,
        "description": desc,
        "amount_min_usd": amount_min,
        "amount_max_usd": amount_max,
        "deadline": deadline.isoformat() if deadline else None,
        "status": "open",
        "eligibility_rules": {},
        "tags": _dedupe_tags(tags),
        "source_url": raw.get("url") or f"https://www.sbir.gov/topics/{sol_num}",
        "url_is_live": True,
        "url_status_code": None,
        "metadata_json": metadata,
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Router ─────────────────────────────────────────────────────────────────

NORMALIZERS: dict[str, Any] = {
    "Grants.gov": _normalize_grants_gov,
    "NSF": _normalize_grants_gov,
    "SBIR.gov": _normalize_sbir_gov,
}


def normalize_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch to the correct normalizer based on `_trestle_source` tag."""
    source = raw.get("_trestle_source", "Grants.gov")
    norm = NORMALIZERS.get(source, _normalize_grants_gov)
    return norm(raw)


def normalize_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a batch, skipping unparseable records, and dedupe by source_id."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in records:
        n = normalize_record(r)
        if not n:
            continue
        sid = n.get("source_id")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append(n)
    return out
