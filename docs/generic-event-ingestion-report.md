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
| MassChallenge | `https://masschallenge.org/events/` | No schema.org records with LLM disabled | **A** | The server-rendered page exposes dated event cards. Current generic HTML extraction requires opt-in LLM extraction; validate its detail-page links before auto-accepting. |
| Greentown Labs | `https://greentownlabs.com/events/` | 68 feed candidates; 3 accepted; 63 pending review | **C/D** | Linked RSS/ICS feeds are discoverable, but RSS publication timestamps are not reliable event start times. Keep feed records in review unless a calendar feed or adapter supplies event dates. |
| BIO | `https://www.bio.org/events` | No schema.org records with LLM disabled | **A** | The public listing renders conference names, dates, locations, and summaries. Registration may remain gated, but discovery metadata is public. |
| SBA | `https://www.sba.gov/events` | No schema.org records with LLM disabled | **A** | The public listing includes type, format, timezone, price, and title. Stable filter parameters should be discovered before scheduled ingestion. |
| mHUB | `https://www.mhubchicago.com/events` | Server response is source-sensitive | **A** | The public calendar and detail pages expose descriptions, dates, and venue. Generic HTML can work; filter recurring promotional content. |
| LabCentral | `https://www.labcentral.org/events-and-media` | Corrected source URL | **A** | The page exposes upcoming titles, date strings, venue labels, and detail pages. Separate adjacent media/news content. |
| Newlab | `https://www.newlab.com/events` | upstream HTTP 404 | **E** | The tested public URL is not a live events endpoint; identify a maintained calendar/feed before ingesting. |
| DOE | `https://www.energy.gov/search-calendar` | Search-shell response | **D** | No verified unified DOE event catalog/feed; build adapters by DOE office or defer. |

## LLM-enabled static HTML results — 2026-08-29

This sweep enabled DeepSeek only in the Cloud Agent's ignored local `.env`.
`EVENTS_GENERIC_LLM_ENABLED=true` and
`EVENTS_GENERIC_BROWSER_ENABLED=false`; tracked defaults remain disabled. Each
run used ephemeral SQLite persistence, so it did not alter a local Postgres
database. The generic pipeline, including its normal validation and review
decisions, was exercised without browser rendering.

| Source | HTTP/access outcome | Strategies | Found / accepted / pending / rejected / duplicates | Result and evidence review |
|---|---|---|---:|---|
| MassChallenge | 200; linked feeds also returned 200 after one redirect | JSON-LD, 3 RSS feeds, LLM | 14 / 4 / 0 / 10 / 0 | Four future dates (Sep. 1, Sep. 10, Oct. 21, and Oct. 29, 2026) had exact title/date/location text evidence. Six RSS news/post records and four dated but past listing records were rejected. |
| BIO | 200 | JSON-LD, LLM | 0 / 0 / 0 / 0 / 0 | The current static response yielded no dated upcoming event records. This is an empty extraction, not evidence that the source has no events. |
| SBA | 302 to `legacy.sba.gov`, then 200 | JSON-LD, LLM | 10 / 10 / 0 / 0 / 0 | Returned dated online/in-person listings, including title, date/time, timezone, and price evidence. The same Mississippi event title occurs in multiple explicitly dated timezone variants; without URL, organizer, or city the generic dedupe rule correctly does not collapse them. |
| LabCentral | 200 | JSON-LD, LLM | 3 / 3 / 0 / 0 / 0 | Returned BioMarin Golden Ticket, Thermo Fisher Mass Spectrometry Kick-Off, and Eppendorf Waffle Breakfast. Each has exact title, `MM.DD.YY` date, and `LabCentral 700` venue evidence. |

The sweep exposed two generic defects and both are covered by deterministic
tests:

- Low-confidence linked RSS records previously prevented a static-page LLM
  pass. ICS and JSON-LD remain terminal strategies, while RSS no longer
  suppresses a static LLM pass.
- An LLM date without an offset could mix naive and aware datetimes during
  duplicate checking. Generic extracted datetimes now normalize to UTC before
  persistence, and past events are rejected rather than entering canonical
  `events`.

This is a transparent source-evidence sample, not a manually labeled
ground-truth benchmark. It therefore makes no extraction-accuracy percentage
claim. In particular, BIO's empty result and SBA's repeated title should be
reviewed with a source-specific labeled set before automatic LLM acceptance is
enabled broadly.

## Known platform classification

| Source type | Representative public source / recommended strategy | Classification | Why |
|---|---|---|---|
| Eventbrite | Existing paginated JSON-LD adapter | **D** | Listing pages need pagination and Eventbrite's authenticated API does not provide general event discovery. |
| Startup Grind | Existing REST adapter | **C** | Public list/detail API is richer and more stable than page parsing. |
| Techstars | Existing Typesense adapter | **C** | Public search configuration/API is structured; the page is client-rendered. |
| Meetup | SF discovery; custom adapter | **D** | Public cards exist, but discovery is location-specific, personalized, and paginated with varying card fields. |
| Luma | Langfuse/Newlab calendars; custom adapter | **D** | Public calendars expose titles/hosts/locations, but platform-specific calendar and event routes need dedicated pagination/date handling. |
| LinkedIn Events | Do not scrape without an approved integration | **E** | Login, anti-bot controls, and dynamically loaded content make public extraction unreliable. |
| YC Events | `ycombinator.com/events`; static HTML | **A** | The public response exposes upcoming titles, dates, and locations. Detail-page metadata still needs validation. |
| University entrepreneurship | UIUC Entrepreneurship Calendar; static HTML | **A** | Public monthly lists expose dated entries and event titles, but calendar software differs by institution. |
| BioLabs | News & Events; custom adapter | **D** | Events and news are mixed on the listing; details have date/time/location but no clean catalog was observed. |
| JLABS | No dedicated public event calendar observed | **E** | The inspected navigator/residency response has no usable events catalog. |
| Newlab | Newlab Luma calendar; custom Luma adapter | **D** | The current response does not expose event cards; use platform calendar/detail routes and handle empty/client-rendered calendars. |
| HAX / SOSV | `sosv.com/events`; static HTML | **A** | The list exposes titles/dates. Preserve access restrictions such as investor-only showcases. |
| Greentown Labs | Calendar adapter | **D** | Category/month views and historical content require date-window filtering and stronger deduplication. |
| America’s SBDC | Training Events; static HTML | **A** | National training events are dated; local SBDC calendars are decentralized. |
| State innovation agencies | Massachusetts event-detail pages; static HTML | **A** | Detail pages provide time, fee, organizer, and description; organization pages can be empty/past-only. |
| Chambers | Greater Boston Chamber calendar; static HTML | **A** | Public listings expose time/location/categories, but calendar vendors and member gates vary. |
| Coworking / hubs | Venture Lane calendar; static HTML | **A** | Calendar entries are public; fetch adjacent month pages and deduplicate recurring entries. |
| VC events | General Catalyst one-off RSVP | **E** | Individual public invites exist, but no dependable public discovery calendar was observed. |
| Utility innovation | EPRI Europe events; static HTML + `?page=` | **A** | Public pagination and descriptions are available; preserve invitation-only restrictions. |

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
