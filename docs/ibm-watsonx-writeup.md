# Trestle — IBM watsonx.ai and watsonx Orchestrate Usage

## How Trestle Uses IBM watsonx.ai

Trestle’s primary intelligence layer runs on **IBM watsonx.ai** using the **Granite 3.2 8B Instruct** model. The LLM client is the first stop in every search request and handles two critical tasks.

### 1. Semantic Intent Parsing

When a founder types a natural-language query such as "I need a grant for a pre-revenue mobility startup in Detroit," the query goes to the watsonx.ai text-generation endpoint via the `llm_client.py` client. IBM Granite extracts structured intent from unstructured text, returning JSON with: location, stage, need_type, industry, demographics, timeline, and funding_range. This eliminates the need for rigid form fields or dropdown menus.

### 2. Dynamic Fit Explanation Generation

After structured retrieval ranks candidate resources, the top results are sent back to Granite. The prompt includes the founder’s profile and the resource details. Granite returns a concise, plain-English explanation of why the resource fits and what the next action should be. This turns a dry search result into a personalized, actionable recommendation.

### Why watsonx.ai Specifically

Granite was chosen because it is open-source, auditable, and performs well on structured extraction tasks with greedy decoding at low temperature. The `llm_client.py` class authenticates via IBM Cloud IAM (API key → access-token exchange) and uses the `/ml/v1/text/generation` endpoint. OpenAI is wired as a fallback, but watsonx.ai is the primary path.

## How Trestle Maps to IBM watsonx Orchestrate

**watsonx Orchestrate** is designed for multi-step, agentic workflows that chain tools, validate state, and compose outputs. Trestle’s **Scout Agent** runs a four-step pipeline that matches the Orchestrate architecture exactly.

### Scout Agent Pipeline (Orchestrate Pattern)

| Step | Scout Action | Equivalent Orchestrate Capability |
|------|--------------|-----------------------------------|
| **VERIFY** | Check existing resources for staleness (dead links, deadline changes) | Trigger web-verification tools on a schedule |
| **FETCH** | Pull new data from monitored feeds (RSS, grant portals, accelerator sites) | Invoke external API and web-scraping skills |
| **MATCH** | Compare new resources against founder profiles using Granite intent parsing | Pass structured output into conditional branching logic |
| **COMPOSE** | Generate a plain-English digest of what changed and what to do | Assemble LLM-generated summaries into a notification payload |

### Implementation for Demo

For the HackMI demo, the Scout pipeline is implemented in **FastAPI** (`routers/scout.py`) so the logic is transparent and the endpoints are live. The architecture is intentionally designed so that each step can be promoted into a **watsonx Orchestrate** workflow node in production. The transition would mean:

- **No code changes** to the intent-parsing prompt or the data schema.
- **Orchestrate** would replace the custom Python scheduler with its built-in trigger system.
- **Skills** would wrap the Tavily search, Firecrawl scraping, and Granite generation steps into reusable, visual workflow nodes.
- **Monitoring** and retry logic would move from custom `asyncio` code to Orchestrate’s native execution graph.

### Why This Design

Using watsonx.ai for the LLM layer and designing the Scout pipeline to port into watsonx Orchestrate gives Trestle a credible, enterprise-ready AI architecture even at the MVP stage. It also aligns with IBM’s go-to-market for mid-market and government-sector customers who require on-premises or hybrid deployments.

## Summary

- **watsonx.ai** (Granite 3.2 8B): Live. Powers intent parsing and personalized fit explanations.
- **watsonx Orchestrate**: Architecturally mapped. The Scout agent’s VERIFY→FETCH→MATCH→COMPOSE pipeline mirrors Orchestrate’s multi-step workflow model and is designed to port directly once a production instance is available.
