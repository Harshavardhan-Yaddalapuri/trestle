# Trestle — Source Citation & Link Integrity Spec

**Date:** 2026-05-23  
**Owner:** Sam (Product)  
**Status:** Spec — team review needed before v1 build  

---

## 1. The Rule

**Every grant presented to a user MUST include a clickable URL to the official listing.**

| What we do | What we DON'T do |
|---|---|
| Link to `https://grants.gov/search-guide.html` | Say "from the SBA" |
| Link to `https://sbir.gov/award` | Say "this is from NIH" |
| Link to `https://ec.europa.eu/info/funding-tenders/opportunities` | Say "an EU listing" |

If the URL isn't verified live within the last 7 days, the agent says so: "Link last verified 6 days ago — if it's broken, tell me and I'll flag it."

---

## 2. URL Sources by Grant Type

| Source | Typical URL Pattern | Is there a permalink? |
|---|---|---|
| **Grants.gov (US federal)** | `grants.gov/search-results-detail/<FON>` | Yes — FON is stable per solicitation |
| **SBIR.gov** | `sbir.gov/awards/<award-id>` or `sbir.gov/topics` | Yes — award ID stable |
| **NIH ASSIST** | `grants.nih.gov/...` | Yes — NIH uses FON |
| **NSF SBIR** | `nsf.gov/funding/...` | Partial — program pages stable, specific calls change |
| **EIC Accelerator** | `ec.europa.eu/info/funding-tenders/opportunities/...` | Partial — calls have stable IDs but URLs can redirect |
| **Innovate UK** | `apply-for-innovation-funding.service.gov.uk/competition/...` | Yes — competition ID stable |
| **TEXAS Enterprise Fund** | `gov.texas.gov/business/texas-enterprise-fund` | Yes |
| **State/local grants** | Varies widely | Rarely — often PDFs or annual pages |

---

## 3. Link Verification Strategy (v1 — Minimum Viable)

### What we DO in v1
- Store `source_url` alongside every grant record in the database
- Agent presents the raw URL in chat. Telegram auto-links it. Web widget renders as `<a href="...">Source</a>`.
- **URL field is non-nullable.** If we don't have a URL, we don't present the grant.
- Weekly batch job: HEAD request every stored URL, flag 404s. Flagged grants are suppressed until a human updates the URL.

### What we DON'T do in v1
- Real-time link verification on every chat response (adds latency, unnecessary)
- Complex redirect chain following (301s are fine, 404s are not)
- URL archival / Wayback fallback (descoped — see PRD Out of Scope)

### v2 considerations (NOT approved)
- Real-time fetch-before-present with cached last-checked timestamp
- Automatic Wayback Machine fallback
- URL change detection + auto-update via scraping

---

## 4. Database Schema — Grant Table (addition)

```sql
ALTER TABLE grants ADD COLUMN source_url TEXT NOT NULL;
ALTER TABLE grants ADD COLUMN url_last_verified TIMESTAMP;
ALTER TABLE grants ADD COLUMN url_is_live BOOLEAN DEFAULT TRUE;
ALTER TABLE grants ADD COLUMN url_status_code INTEGER; -- store actual HTTP status
```

**Rationale:** `NOT NULL` enforces the rule — no URL, no grant. `url_is_live` lets us suppress broken links without deleting data. `url_last_verified` lets us show users freshness.

---

## 5. Agent Presentation Format

### In chat (Telegram / web widget)

```
3 grants match your profile:

1. NIH SBIR Phase I — $400K | Due June 30
   → https://grants.gov/search-results-detail/PA-FY26-123  
   [Live link — verified 2 days ago]

2. Texas Enterprise Fund — up to $50K match
   → https://gov.texas.gov/business/texas-enterprise-fund  
   [⚠️ Partial match — requires 10+ jobs]

3. NSF SBIR — $256K | Rolling
   → https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=5366  
   [⚠️ Link last verified 6 days ago]
```

### Rules
- URL must be visible, not hidden behind text.
- If `url_is_live = false`, agent says: "The link for this grant was broken as of [date]. Here's the best alternative I found: [search URL]."
- Never silently drop a URL present in our database.

---

## 6. Edge Cases

| Scenario | Agent Behavior |
|---|---|
| URL returns 404 in weekly check | Suppress from all future matches until fixed. Log to `#broken-links` channel. |
| URL returns 301 redirect | Accept as valid. Update stored URL to final destination in weekly job. |
| User says "your link is broken" | Agent flags immediately, asks user for corrected URL if they have it. |
| Grant source has no stable URL (e.g., PDF-only state program) | Agent says: "No public listing URL available. Here's the PDF: [link]. Last checked [date]." |
| Official URL changes between scraping cycles | Weekly job catches it. If new URL is available via redirect, auto-update. If not, suppress + alert human. |

---

## 7. Open Questions for Team Review

| Question | Who should answer |
|---|---|
| What's the latency hit of weekly batch HEAD checks? | Jason (Backend) |
| Do we need a separate `grant_sources` table (one-to-many URLs per grant)? | Jason (Backend) |
| How does Telegram render raw URLs? Auto-link or do we need markdown? | Floyd (Frontend) |
| Should we cache URL verification results in Redis vs. DB? | Aurthur (Architect) |
| What's the fallback if ALL URLs for a user's matches are broken? | Sam (Product) — default: honest "I can't find live listings right now, check directly at [portal]." |

---

*No URL = no trust. No trust = dead product.*
