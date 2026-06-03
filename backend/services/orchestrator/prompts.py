from __future__ import annotations

from typing import TYPE_CHECKING

from backend.schemas.memory import MemoryContext
from backend.schemas.profile import ProfileOut

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext

_PREAMBLE = (
    "You are trestle, an assistant that helps startup founders find grants, fellowships, "
    "and non-dilutive funding. Be concise, concrete, and useful. Don't hedge unnecessarily. "
    "When you don't know, say so."
)


def _profile_summary(profile: ProfileOut) -> str:
    lines: list[str] = []
    if profile.company_name:
        lines.append(f"- Company: {profile.company_name}")
    if profile.company_stage:
        lines.append(f"- Stage: {profile.company_stage}")
    if profile.industry:
        lines.append(f"- Industry: {', '.join(profile.industry)}")
    if profile.incorporation_country:
        loc = profile.incorporation_country
        if profile.incorporation_state:
            loc += f"-{profile.incorporation_state}"
        lines.append(f"- Incorporated: {loc}")
    elif profile.location:
        lines.append(f"- Location: {profile.location}")
    if profile.team_size:
        lines.append(f"- Team: {profile.team_size}")
    if profile.funding_raised_usd_cents:
        lines.append(f"- Funding raised: ${profile.funding_raised_usd_cents // 100:,}")
    if profile.one_liner:
        lines.append(f"- Description: {profile.one_liner}")
    return ("Profile:\n" + "\n".join(lines)) if lines else "Profile: (no profile data yet)"


def _memory_bullets(memory: MemoryContext) -> str:
    bullets: list[str] = []
    for p in memory.preferences:
        bullets.append(f"- (preference) {p}")
    for c in memory.constraints:
        bullets.append(f"- (constraint) {c}")
    for o in memory.recent_observations:
        bullets.append(f"- (recent) {o}")
    for corr in memory.corrections:
        bullets.append(f"- (correction) {corr}")
    if not bullets:
        return ""
    return "Things you remember about this founder:\n" + "\n".join(bullets)


def _context_block(ctx: TurnContext) -> str:
    parts = [_profile_summary(ctx.profile)]
    mb = _memory_bullets(ctx.memory)
    if mb:
        parts.append(mb)
    return "\n\n".join(parts)


def build_greet_system_prompt(ctx: TurnContext) -> str:
    return (
        f"{_PREAMBLE}\n\n"
        "Respond briefly and warmly to the user's greeting. Mention you help founders find "
        "grants and funding. One or two sentences max."
    )


def build_smalltalk_system_prompt(ctx: TurnContext) -> str:
    return (
        f"{_PREAMBLE}\n\n"
        "Acknowledge the user's message warmly and briefly. Under 2 sentences."
    )


def build_unknown_system_prompt(ctx: TurnContext) -> str:
    return (
        f"{_PREAMBLE}\n\n"
        "The user's message wasn't clear. Ask a short clarifying question to figure out "
        "what they need. Keep it under 20 words."
    )


def build_unknown_destructive_system_prompt(ctx: TurnContext) -> str:
    return (
        f"{_PREAMBLE}\n\n"
        "The user seems to want to update something, but you're not sure. Ask them to "
        "confirm what they'd like to change. Keep it under 20 words."
    )


def build_discover_system_prompt(ctx: TurnContext) -> str:
    ctx_block = _context_block(ctx)
    return (
        f"{_PREAMBLE}\n\n"
        f"{ctx_block}\n\n"
        "The user is exploring grant options. Help them understand what kinds of grants "
        "and funding might fit their situation. Reference their stage, location, or industry "
        "if you know it. Suggest 2-3 categories worth exploring. Don't run a full match."
    )


def build_match_request_system_prompt(ctx: TurnContext, match_results_text: str) -> str:
    ctx_block = _context_block(ctx)
    return (
        f"{_PREAMBLE}\n\n"
        f"{ctx_block}\n\n"
        f"Grant matches:\n{match_results_text}\n\n"
        "Present these matches conversationally. Lead with the strongest fit and explain why. "
        "If any have hard fails on profile fields, mention that without being prescriptive. "
        "Don't detail more than 3-4. Be specific and helpful."
    )


def build_deep_dive_system_prompt(
    ctx: TurnContext, grant_detail_text: str, eligibility_text: str
) -> str:
    ctx_block = _context_block(ctx)
    return (
        f"{_PREAMBLE}\n\n"
        f"{ctx_block}\n\n"
        f"Grant details:\n{grant_detail_text}\n\n"
        f"Eligibility:\n{eligibility_text}\n\n"
        "Give the founder a thorough rundown: what the grant is, whether they qualify, "
        "key requirements to watch, and any tips. Be specific and useful."
    )


def build_profile_update_system_prompt(ctx: TurnContext, fields_updated: list[str]) -> str:
    fields_str = ", ".join(fields_updated) if fields_updated else "nothing (already up to date)"
    return (
        f"{_PREAMBLE}\n\n"
        f"Updated fields: {fields_str}.\n\n"
        "Confirm what was updated in a short, human-sounding sentence. "
        "Example: 'Got it — I've noted you're incorporated in Delaware with 4 people.'"
    )


def build_profile_query_system_prompt(ctx: TurnContext) -> str:
    ctx_block = _context_block(ctx)
    return (
        f"{_PREAMBLE}\n\n"
        f"{ctx_block}\n\n"
        "Summarize what you know about this founder from their profile. Skip null/empty fields. "
        "Tell them they can update anything by just mentioning it. Keep it brief."
    )


def build_lifecycle_system_prompt(ctx: TurnContext, action: str, grant_name: str) -> str:
    return (
        f"{_PREAMBLE}\n\n"
        f"You just performed '{action}' on grant '{grant_name}'. "
        "Confirm briefly in a human-sounding way. 1-2 sentences."
    )


def build_correction_system_prompt(ctx: TurnContext) -> str:
    return (
        f"{_PREAMBLE}\n\n"
        "The user is correcting something. Acknowledge without being defensive. "
        "'Got it, I'll remember that.' or similar. 1 sentence."
    )
