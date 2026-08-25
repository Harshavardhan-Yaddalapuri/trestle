# Generic Event Ingestion Report

## Implementation

The generic pipeline is additive. Known providers still use their custom
adapters first; unknown sources proceed through:

1. ICS/iCalendar response or linked `.ics` feed
2. RSS/Atom response or linked feed
3. schema.org Event JSON-LD
4. Opt-in LLM extraction from static readable HTML
5. Opt-in Playwright rendering, followed by JSON-LD or LLM extraction

Every candidate is validated before persistence. Missing or implausible name/date
is rejected; candidates below the confidence threshold remain in
`event_candidates` for review. Accepted records have an `event_provenance` row
with source URL/identifier, extraction method, raw payload hash, evidence, field
confidence, extraction time, and last verification time.

## Classification legend

- **A** — Works with static generic extraction
- **B** — Works only after browser rendering
- **C** — Better handled by a public API/feed
- **D** — Custom adapter recommended for reliable coverage
- **E** — Cannot currently be reliably extracted

## Live smoke-test results

Tests ran on 2026-08-25 with LLM extraction disabled. That is deliberate: without
a configured model, the pipeline must preserve uncertain candidates for review
rather than fabricate structured records.

| Source | URL tested | Result | Classification | Evidence / limitation |
|---|---|---:|---|---|
| Techstars | `https://www.techstars.com/events/search` | 31 found; 27 accepted; 4 cross-source duplicates | **C** | Existing custom adapter uses Techstars' public Typesense search configuration/API. It is more reliable than rendered HTML. |
| MassChallenge | `https://masschallenge.org/events` | 0 static JSON-LD events | **D** | The page exposed no usable Event JSON-LD. Its WordPress feed produced dated posts, not reliable event records; a calendar/API adapter is needed. |
| Greentown Labs | `https://greentownlabs.com/events/` | 68 feed candidates; 3 accepted; 63 pending review | **C/D** | Linked RSS/ICS feeds are discoverable, but RSS publication timestamps are not reliable event start times. Keep feed records in review unless a calendar feed or adapter supplies event dates. |
| BIO | `https://www.bio.org/events` | 0 static JSON-LD events | **D** | No usable Event nodes in the static response; a site-specific calendar/API strategy is recommended. |
| SBA | `https://www.sba.gov/events` | 0 static JSON-LD events | **D** | Static response did not expose structured events. A government calendar feed/API or adapter is preferable. |
| mHUB | `https://mhubchicago.com/events` | upstream HTTP 500 | **E** | The source could not be fetched reliably during the test. |
| LabCentral | `https://www.labcentral.org/events` | upstream HTTP 404 | **E** | The tested public URL is not a live events endpoint; identify a maintained calendar/feed before ingesting. |
| Newlab | `https://www.newlab.com/events` | upstream HTTP 404 | **E** | The tested public URL is not a live events endpoint; identify a maintained calendar/feed before ingesting. |
| DOE | `https://www.energy.gov/events` | upstream HTTP 404 | **E** | The tested public URL is not a live events endpoint; identify a maintained calendar/feed before ingesting. |

## Known platform classification

| Source type | Recommended strategy | Classification | Why |
|---|---|---|---|
| Eventbrite | Existing paginated JSON-LD adapter | **D** | Listing pages need pagination and Eventbrite's authenticated API does not provide general event discovery. |
| Startup Grind | Existing REST adapter | **C** | Public list/detail API is richer and more stable than page parsing. |
| Techstars | Existing Typesense adapter | **C** | Public search configuration/API is structured; the page is client-rendered. |
| Meetup | Existing JSON-LD adapter, with source-specific pagination if needed | **D** | A single listing page works generically, but search/pagination and rate restrictions need provider handling. |
| Luma | Existing JSON-LD adapter | **A/D** | Individual/listing pages can expose JSON-LD; broader discovery and pagination may need an adapter. |
| LinkedIn Events | Do not scrape without an approved integration | **E** | Login, anti-bot controls, and dynamically loaded content make public extraction unreliable. |
| YC / accelerator calendars | JSON-LD/feed first, then review | **A/C** | Works when a calendar provides structured event data; otherwise source-specific implementation is needed. |
| University calendars | ICS/RSS preferred | **C** | Many institutions publish calendar feeds; generic HTML is inconsistent across vendors. |
| Biotech, hardware, government, VC, coworking, climate, and utility sites | Feed/JSON-LD first; review queue otherwise | **A–D** | Reliability depends on the specific calendar vendor. The pipeline intentionally does not auto-insert weak HTML/RSS inferences. |

## Accuracy and duplicate behavior

- Deterministic fields from API/ICS/JSON-LD use 0.92–0.99 confidence and can be
  auto-accepted after validation.
- RSS dates are 0.70 confidence, so candidates remain in review by default.
- LLM fields require source evidence and sufficient name/start-date confidence;
  otherwise they remain in review.
- Duplicates use exact normalized registration URL, or normalized name/date with
  matching organizer or city. The Techstars run found four likely duplicate
  listings and attached provenance instead of creating duplicate canonical events.

This is a smoke-test report, not a manually labeled accuracy benchmark. A
numerical extraction-accuracy claim requires source-specific ground-truth labels,
which should be collected before enabling automatic LLM acceptance at scale.
