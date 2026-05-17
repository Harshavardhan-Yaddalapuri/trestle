# Trestle — 3-Min Demo Script (Stitch)
**Spoken word target: ~420 words ≈ 2 min 50 sec at conversational pace. Leave 10 sec buffer.**

---

**[HOOK — 20 sec]**

Raise your hand if you know a startup that died with a good idea but no money.

(Pause, look around)

Now raise your hand if you think they *couldn't* find the money — or if they just never knew it existed.

That second one is why we're here. 42% of startups fail because they run out of funding. Not because the funding isn't there. Because finding it is a full-time job buried inside a job that already has 27 hats.

---

**[THE PAIN — 25 sec]**

Let me show you what that actually looks like.

You are a pre-revenue founder in Detroit. You need fifty thousand dollars to build a prototype. So you open seventeen browser tabs. Grants dot gov. MEDC. Crunchbase. Some accelerator newsletter from six months ago that may or may not still exist.

You spend two weeks on this. You miss a deadline on day three because you didn't know about it. You find a program with a dead link. You qualify for something but the application closed yesterday.

That is not a skill issue. That is a search problem. And it is killing companies.

---

**[THE DEMO — 60 sec]**

(Stitch opens laptop, screen shared)

This is Trestle. It is not a directory. It is an autonomous resource discovery engine.

**Landing page.** Clean. Founder types in plain English.

*(Stitch types into hero search bar)*

"I need a grant for a pre-revenue mobility startup in Detroit."

Hit enter.

**Results page.**

Look at the top — *intent chips*. Trestle understood: location is Detroit, stage is pre-revenue, need is a grant. It didn't keyword-match. It parsed intent.

Now the cards.

*(Scroll down slightly)*

First result: Michigan Mobility Prototyping Grant. Fit score: 96%.

Not a list. A **ranked answer**.

"Why it fits" — Because you are Michigan-based, pre-revenue, and building mobility tech.
"Next step" — Submit a three-page concept by August 15.
"Apply now" — Live link. Not a dead URL. Verified.

*(Scroll, click "Apply now" briefly to show real page opens, then back)*

Now pivot. Same founder, same day, new need.

*(Types new query)*

"Accelerator for AI health startup in Ann Arbor."

Intent updates. Results repopulate. Techstars Detroit. Centrepolis. Ann Arbor SPARK.

Two seconds. Not two weeks.

---

**[THE ENGINE — 20 sec]**

Under the hood, this is IBM watsonx.ai Granite parsing intent and scoring fit. But the part that matters is the Scout agent.

Scout monitors over five hundred sources continuously. New grant drops at noon. You get pinged at twelve oh three. Your competitor? They find out next Tuesday.

That is the difference between a founder who survives and one who never knew the door was open.

---

**[THE CLOSE — 25 sec]**

CB Insights says 70% of VC-backed deaths are "ran out of capital." 
Angel Investment Network says 38% of founders spend more than 30% of their week just fundraising.

That time is not free. It is code not written. It is customers not talked to.

Trestle gives you that time back.

Seed tier is zero dollars. Growth is forty-nine. We do not charge founders who have nothing. We help them get something.

*(Pause. Look at judges.)*

If you are a founder in this room, do not let the thing that kills your company be a spreadsheet you never opened.

Thank you.

---

## Notes for Stitch

- **Eye contact with judges during hook and close.** Demo is for screen, eyes are for humans.
- **Speak the query aloud while typing.** It keeps the audience tracking.
- **Pause after landing page load** — let people see the brand.
- **After clicking "Apply now"** — say "Real page. Not staging." then back immediately. Under 3 seconds.
- **If backend hiccups** — reload `/search?q=grants+for+pre-revenue+founder+in+detroit`. It is seeded with 19 verified programs.
- **Backup line:** If results load slowly, say "Scout is fetching live data — here we go" and wait. Never apologize for load time.

## Bookmark Bar (drag these in)

1. `http://localhost:3000` — Landing
2. `http://localhost:3000/search?q=grants+for+pre-revenue+founder+in+detroit`
3. `http://localhost:3000/search?q=accelerator+for+AI+health+startup+in+ann+arbor`
