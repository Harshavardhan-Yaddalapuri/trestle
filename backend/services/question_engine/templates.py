from __future__ import annotations

QUESTION_TEMPLATES: dict[str, str] = {
    "company_stage": "What stage is your company at?",
    "incorporation_country": "Where is your company incorporated?",
    "incorporation_state": "Which US state are you incorporated in?",
    "industry": "What industries does your company work in? You can list a few.",
    "team_size": "How many full-time people are on the team?",
    "has_technical_cofounder": "Do you have a technical cofounder?",
    "funding_raised": "How much have you raised to date?",
    "funding_target": "How much are you looking to raise next?",
    "one_liner": "In one sentence, what does your company do?",
    "company_name": "What's your company called?",
    "founder_name": "What should I call you?",
}

FIELD_REASONS: dict[str, str] = {
    "company_stage": "needed to evaluate stage-based grant eligibility",
    "incorporation_country": "needed to evaluate location-based grant eligibility",
    "incorporation_state": "needed for US state-specific grant requirements",
    "industry": "needed to match grants by industry focus",
    "team_size": "needed to evaluate team size requirements",
    "has_technical_cofounder": "needed for grants requiring a technical cofounder",
    "funding_raised_usd_cents": "needed to evaluate funding cap requirements",
    "funding_target_usd_cents": "needed to evaluate minimum funding target requirements",
    "one_liner": "helps personalize your grant matches",
    "company_name": "helps identify your company in grant applications",
    "founder_name": "helps personalize our conversation",
}
