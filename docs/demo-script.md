# Trestle — Demo Script for Stitch
**Target duration: 3 minutes**

---

## Screen 1: Landing Page (15 seconds)
**URL:** `http://localhost:3000`

**Stitch says:**
> "Every founder starts with an idea. Most die in the weeds — buried under spreadsheets, dead links, and missed deadlines. Trestle is an autonomous resource discovery engine. We find what you need before you know you need it."

**Action:** Scroll down once to show Features section, then click the search bar in Hero.

---

## Screen 2: Live Search — Query 1 (45 seconds)
**URL:** `http://localhost:3000/search?q=grants+for+pre-revenue+founder+in+detroit`

**Stitch says:**
> "Let's say you're a pre-revenue founder in Detroit. You need capital. You'd spend weeks on Google, Crunchbase, and state websites. Trestle does it in 2 seconds."

**Action:** Show the parsed intent chips: **Location: Detroit**, **Stage: Pre-revenue**, **Need: Grant**

**Point out:**
- Fit scores (e.g., MEDC Mobility Grant — 95% fit)
- Confidence badges ("High" / "Medium")
- "Why it fits" explanation
- "Next step" — actionable
- Real URLs — click "Learn more" or "Apply now"

**Data drop:**
> "CB Insights says 42% of startups fail because they run out of funding. 38% of founders spend 30% of their week just searching for investors. We're cutting that to zero."

---

## Screen 3: Live Search — Query 2 (30 seconds)
**URL:** `http://localhost:3000/search?q=accelerator+for+AI+health+startup+in+ann+arbor`

**Stitch says:**
> "Now pivot — you're an AI health startup in Ann Arbor looking for an accelerator. Same engine, different need."

**Action:** Show intent chips changing. Highlight Techstars Detroit or Centrepolis Accelerator result.

**Data drop:**
> "Y Combinator's acceptance rate just hit 0.6% — lowest ever. The average founder applies to 12 programs before getting in. Trestle finds the ones where you actually fit."

---

## Screen 4: Scout Agent Mention (20 seconds)
**URL:** `http://localhost:3000` → scroll to Features → "Autonomous Discovery"

**Stitch says:**
> "This isn't just search. Our Scout agent continuously monitors 500+ sources — grants, accelerators, pitch competitions, government programs. When a new $50K MEDC grant drops, Trestle alerts you before your competitors even know it exists."

---

## Screen 5: Pricing / CTA (10 seconds)
**URL:** Scroll to Pricing

**Stitch says:**
> "Seed tier is free forever. Growth is $49. We're not charging founders who have nothing. We're charging the ones who now have something to protect."

**Action:** Click "Start Building" or "Contact" to end.

---

## The Data Slide (if judges ask "why now?")

| Stat | Source |
|------|--------|
| **42%** of startups fail due to lack of funding | CB Insights |
| **70%** of VC-backed shutdowns = "ran out of capital" | CB Insights |
| **38%** of founders spend **30%+** of their week fundraising | Angel Investment Network 2025 |
| **$9.2B** in government grants unclaimed by startups (India alone, 2025) | Ascendants / DPIIT |
| **€182B** in EU Recovery Fund allocated but not disbursed | Reuters |
| **0.6%** Y Combinator acceptance rate (Summer 2025) | Ellenox / WeAreFounders |
| **$2.5B → $8B** market for startup founder networking tools by 2035 | WiseGuyReports |
| **$12B** in EU Innovation Fund going unused | Table.Briefings |

---

## Backup Demo URLs (bookmark these)
- `http://localhost:3000` — Landing
- `http://localhost:3000/search?q=grants+for+pre-revenue+founder+in+detroit`
- `http://localhost:3000/search?q=accelerator+for+AI+health+startup+in+ann+arbor`
- `http://localhost:3000/search?q=michigan+SBDC+counseling+for+first+time+founder`

---

## What to do if the backend is down
1. Open terminal
2. `cd ~/trestle`
3. `make dev-be`
4. In another tab: `make dev-fe`
5. Refresh browser

If Supabase is empty, run: `make seed`
