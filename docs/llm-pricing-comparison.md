# LLM API Pricing Comparison for Trestle Chat Assistant

**Date:** May 30, 2026  
**Context:** Trestle is a conversational AI assistant for startup founders. Chat is the core feature -- founders ask questions and get grant recommendations. Requires streaming responses. Harsha already has GCP Gemini access and Ollama Cloud (DeepSeek v4 Pro).

---

## Summary Table (All prices per 1M tokens, USD)

| Provider / Model | Input ($/1M) | Output ($/1M) | Context Window | Streaming | Free Tier? | Local? |
|---|---|---|---|---|---|---|
| **Gemini 2.5 Flash** (Google) | $0.15 (text) | $0.60 | 1M | Yes | Yes (1K req/day, 250K TPM) | No |
| **Gemini 2.5 Flash-Lite** (Google) | $0.10 | $0.40 | 1M | Yes | Yes (1K req/day, 250K TPM) | No |
| **Gemini 2.5 Pro** (Google) | $1.25 (≤200K) / $2.50 (>200K) | $10.00 (≤200K) / $15.00 (>200K) | 1M | Yes | Yes (limited RPM) | No |
| **Gemini 3 Flash** (Google) | $0.50 (text) | $3.00 | 1M | Yes | Yes (5K prompts/mo) | No |
| **Gemini 3 Pro** (Google) | $2.00 (≤200K) | $12.00 (≤200K) | 1M | Yes | No free tier | No |
| **Claude Haiku 4.5** (Anthropic) | $1.00 | $5.00 | 200K | Yes | No | No |
| **Claude Sonnet 4.6** (Anthropic) | $3.00 | $15.00 | 1M | Yes | No | No |
| **Claude Opus 4.7** (Anthropic) | $5.00 | $25.00 | 1M | Yes | No | No |
| **GPT-4o** (OpenAI) | $2.50 | $10.00 | 128K | Yes | No free API credits† | No |
| **GPT-4o-mini** (OpenAI) | $0.15 | $0.60 | 128K | Yes | No free API credits† | No |
| **DeepSeek V4 Flash** (DeepSeek) | $0.14 (miss) / $0.003 (hit) | $0.28 | 1M | Yes | No (top-up required) | No |
| **DeepSeek V4 Pro** (DeepSeek) | $0.435 (miss) / $0.004 (hit) | $0.87 | 1M | Yes | No (top-up required) | No |
| **Groq - Llama 3.1 8B** | $0.05 | $0.08 | 128K | Yes | Yes (100K tok/day) | No |
| **Groq - Llama 4 Scout** | $0.11 | $0.34 | 128K | Yes | Yes (100K tok/day) | No |
| **Groq - Llama 3.3 70B** | $0.59 | $0.79 | 128K | Yes | Yes (100K tok/day) | No |
| **Ollama - DeepSeek v4 Pro** | FREE (local) | FREE (local) | Model-dependent | Yes | N/A (free compute) | **YES** |
| **Mistral Small 3.2** | $0.10 | $0.30 | 128K | Yes | Yes (rate-limited) | No |
| **Mistral Medium 3.1** | $0.40 | $2.00 | 128K | Yes | Yes (rate-limited) | No |
| **Together AI - Qwen3.5 9B** | $0.10 | $0.15 | 262K | Yes | No | No |
| **Together AI - Llama 3.3 70B** | $0.88 | $0.88 | 131K | Yes | No | No |

† OpenAI discontinued free API credits for new signups. Minimum $5 prepaid credit required. A past data-sharing program (up to 11M free tokens/day) ended April 2025.

---

## Detailed Provider Analysis

### 1. Gemini (Google) — ALREADY AVAILABLE

**Status:** Harsha has GCP Gemini access via API key.

**Best models for Trestle:**
- **Gemini 2.5 Flash:** $0.15/$0.60 input/output — the sweet spot. 1M context window, fast responses, solid reasoning. Free tier gives 1,000 requests/day and 250K tokens per minute.
- **Gemini 2.5 Flash-Lite:** $0.10/$0.40 — even cheaper, good for simpler queries.

**Streaming:** Full streaming support via `streamGenerateContent`.

**Free tier limits (Google AI Studio):**
- 5-15 requests per minute (model-dependent)
- 250,000 tokens per minute
- ~1,000 requests per day
- No payment method required
- NOTE: Free tier data **may be used to improve Google's products**. Paid tier does NOT allow this.

**Context caching:** Gemini 2.5 Flash offers context caching at $0.025/1M tokens (text), dramatically reducing cost for repeated system prompts.

**Verdict:** Excellent default choice. Free tier covers development and light production. Flash is cheap enough that even paid usage at scale is minimal.

---

### 2. Anthropic Claude

**Best models for Trestle:**
- **Claude Haiku 4.5:** $1.00/$5.00 — cost-effective, 200K context. Good for chat.
- **Claude Sonnet 4.6:** $3.00/$15.00 — best quality for grant analysis, 1M context. Premium pricing for >200K input ($6/$22.50).

**Streaming:** First-class streaming via SSE. Claude SDK has excellent streaming ergonomics.

**Prompt caching:** 90% cost reduction on cached reads. System prompts and reusable grant templates can be cached at $0.10/1M tokens.

**Verdict:** Best response quality for nuanced grant matching conversations, but 10-20x more expensive than Gemini Flash. Use as a premium fallback tier. Haiku 4.5 is reasonable for production at $1/$5.

---

### 3. OpenAI GPT-4o

**Best models for Trestle:**
- **GPT-4o-mini:** $0.15/$0.60 — competitive with Gemini Flash. 128K context.
- **GPT-4o:** $2.50/$10.00 — flagship quality, 128K context, 16K max output.

**Streaming:** Full streaming via server-sent events. Mature SDK ecosystem.

**Free tier:** Effectively NONE. OpenAI requires prepaid credits (minimum $5). No free trial credits for new accounts. The data-sharing program that offered up to 11M free tokens/day ended in April 2025.

**Verdict:** Strong model quality but no free tier and requires prepaid billing. GPT-4o-mini is cost-competitive with Gemini Flash. Not recommended as primary due to lack of free tier.

---

### 4. Groq (LPU Inference)

**Best models for Trestle:**
- **Llama 3.1 8B Instant:** $0.05/$0.08 — cheapest cloud option. 840 tokens/sec.
- **Llama 4 Scout (17Bx16E MoE):** $0.11/$0.34 — good balance of quality/cost. 594 tok/sec.
- **Llama 3.3 70B:** $0.59/$0.79 — highest quality on Groq. 394 tok/sec.

**Streaming:** Yes. Groq's LPUs are the fastest inference hardware on the market — near-instant streaming.

**Free tier:**
- 1,000 requests per day
- 100K tokens per day (total input+output)
- 30 requests per minute
- No credit card required

**Verdict:** Insanely fast streaming with a real free tier. Llama 3.3 70B quality is solid for grant conversations. Best latency of any option. Free tier covers development, but 100K tokens/day is tight for production.

---

### 5. Ollama (Local) — ALREADY DEPLOYED

**Status:** Running DeepSeek v4 Pro via Ollama Cloud. `OLLAMA_MODEL=deepseek-v4-pro` configured in `.env`.

**Cost:** $0 (just electricity/compute). No API costs, no rate limits.

**Streaming:** Yes, Ollama supports streaming responses natively via `/api/chat` with `stream: true`.

**Quality vs. Speed tradeoff:**
- DeepSeek v4 Pro is a strong model for reasoning
- Dependent on local hardware (GPU RAM, CPU speed)
- No rate limits — unlimited usage
- Responses may be slower than Groq/API providers

**Alternative Ollama models to consider:**
- `llama3.3:70b` — strong all-rounder (needs ~40GB RAM)
- `gemma3:27b` — Google's latest open model, excellent for chat
- `mistral:7b` — lightweight, fast responses
- `qwen3:32b` — strong reasoning, good chat quality

**Verdict:** Best option for cost-sensitive deployment. Already running. No API bills ever. Main limitation is inference speed on local hardware. Ideal as the default/fallback tier.

---

### 6. DeepSeek API (Cloud)

**Best models for Trestle:**
- **DeepSeek V4 Flash:** $0.14/$0.28 — absurdly cheap, 1M context. Cache hits at $0.003/1M.
- **DeepSeek V4 Pro:** $0.435/$0.87 — full quality, 1M context. Cache hits at $0.0036/1M.

**Streaming:** Yes, supports SSE streaming in both OpenAI-compatible and Anthropic-compatible formats.

**Context caching:** Up to 75% discount on cached input. System prompts that repeat across users are nearly free.

**Free tier:** None. Requires topped-up balance (prepaid credits). However, pricing is so low that $5 covers millions of tokens.

**Verdict:** Cheapest cloud API by far. V4 Flash at $0.14/$0.28 is 10-100x cheaper than GPT-4o/Claude. The catch: prepaid balance required, no free trial. Ideal scaling path when Ollama can't handle load.

---

### 7. Mistral (La Plateforme)

**Best models for Trestle:**
- **Mistral Small 3.2:** $0.10/$0.30 (some sources show even lower at $0.02 input for Nemo)
- **Mistral Medium 3.1:** $0.40/$2.00

**Streaming:** Yes, SSE streaming supported.

**Free tier:** Yes — limited rate limits for evaluation and prototyping. Must upgrade to Scale plan ($0 minimum) for higher limits.

**Verdict:** Solid European alternative. Small is cost-competitive. Free tier exists but is rate-limited. Not as compelling as Gemini's free tier or Groq's speed.

---

### 8. Together AI

**Best models for Trestle:**
- **Qwen3.5 9B:** $0.10/$0.15 — ultra-cheap, 262K context
- **Llama 3.3 70B:** $0.88/$0.88 — same price input/output
- **Gemma 4 31B:** $0.20/$0.50 — Google's open model, good for chat

**Streaming:** Yes.

**Free tier:** No permanent free tier. Pay-as-you-go with no minimums.

**Verdict:** Great for open-source model diversity. 200+ models available. 50% batch discount. No free tier means it's less compelling than Groq for cost-sensitive projects.

---

## Monthly Cost Projections

Assuming a moderately popular app: **1,000 conversations/day, avg 2K input + 1K output tokens per message, 3 messages per conversation.**

**Total tokens:**
- Input: 1,000 × 3 × 2,000 = 6M tokens/day = 180M tokens/month
- Output: 1,000 × 3 × 1,000 = 3M tokens/day = 90M tokens/month

| Provider / Model | Monthly Input Cost | Monthly Output Cost | **Total/Month** |
|---|---|---|---|
| **Ollama (local)** | $0 | $0 | **$0** |
| **Gemini 2.5 Flash (free tier)** | $0 (within limits) | $0 (within limits) | **$0** |
| **Groq Llama 3.1 8B** | $9.00 | $7.20 | **$16.20** |
| **DeepSeek V4 Flash** | $25.20 | $25.20 | **$50.40** |
| **Gemini 2.5 Flash (paid)** | $27.00 | $54.00 | **$81.00** |
| **GPT-4o-mini** | $27.00 | $54.00 | **$81.00** |
| **DeepSeek V4 Pro** | $78.30 | $78.30 | **$156.60** |
| **Claude Haiku 4.5** | $180.00 | $450.00 | **$630.00** |
| **GPT-4o** | $450.00 | $900.00 | **$1,350.00** |
| **Claude Sonnet 4.6** | $540.00 | $1,350.00 | **$1,890.00** |

---

## Recommendations

### Tiered Strategy for Trestle

```
┌─────────────────────────────────────────────────────┐
│                    TIER 1: PRIMARY                   │
│  Ollama (DeepSeek v4 Pro) — local, free, unlimited  │
│  + Gemini 2.5 Flash free tier as backup             │
│                                                     │
│              TIER 2: PAID SCALE-OUT                  │
│  DeepSeek V4 Flash API ($50/mo at 1K convos/day)   │
│  or Groq Llama 3.3 70B for blazing speed            │
│                                                     │
│              TIER 3: PREMIUM QUALITY                 │
│  Claude Sonnet 4.6 — for complex grant analysis     │
│  (triggered on-demand, not every message)           │
└─────────────────────────────────────────────────────┘
```

### Specific Recommendations

1. **Keep Ollama as primary.** It's already running with DeepSeek v4 Pro. Zero cost. No rate limits. The project is local-first by design. Add a health check that falls back when Ollama is overloaded.

2. **Gemini 2.5 Flash as first cloud fallback.** Harsha already has GCP access. Free tier covers development and moderate production. Paid tier at $81/month for 1K conversations/day is reasonable. Quality is strong for chat. The 1M context window can hold entire grant databases.

3. **DeepSeek V4 Flash as scale-out option.** If Ollama can't handle concurrency and Gemini free tier is exhausted, DeepSeek V4 Flash at $50/month is the cheapest paid cloud API. 1M context window. Cache hits make repeated system prompts nearly free.

4. **Groq for speed-critical paths.** If streaming latency is the #1 UX concern, Groq's LPU hardware delivers 394-840 tokens/sec (vs 35-50 for most providers). Llama 3.3 70B at $0.59/$0.79 is fast AND affordable. Free tier provides 100K tokens/day for testing.

5. **Claude Sonnet 4.6 as premium tier.** Only for complex grant eligibility analysis where nuanced reasoning matters. At $1,890/month for full traffic, it should be used selectively — maybe only when the user explicitly requests "deep analysis" or the initial match confidence is low.

6. **Skip OpenAI.** No free tier, prepaid billing friction, and GPT-4o-mini is cost-equivalent to Gemini Flash but without the free cushion. GPT-4o is 17x more expensive than DeepSeek V4 Flash for comparable output quality.

### Implementation Priority

| Priority | Action | Cost |
|---|---|---|
| P0 | Confirm Ollama DeepSeek v4 Pro streaming works reliably | $0 |
| P0 | Add Gemini 2.5 Flash as fallback provider | $0 (free tier) |
| P1 | Set up provider router with health checks + auto-fallback | Dev time |
| P1 | Add DeepSeek V4 Flash API key ($5 top-up for testing) | ~$5 |
| P2 | Add Groq Llama 3.3 70B for speed optimization | $0 (free tier for dev) |
| P3 | Add Claude Sonnet 4.6 for premium analysis tier | On-demand |

### Key Takeaway

The Trestle chat assistant can run at **$0/month** using the existing Ollama setup plus Gemini free tier as backup. Even at production scale (1,000 conversations/day), the cost is under $100/month using DeepSeek V4 Flash or Gemini Flash. There is no scenario where this chat feature needs to cost more than $200/month unless every message goes through Claude Sonnet.
