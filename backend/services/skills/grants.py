from backend.services.skills_registry import SkillDescriptor, SkillInput, register

register(
    SkillDescriptor(
        id="grants",
        name="Grant Discovery",
        version="v1",
        status="active",
        description="Find non-dilutive grants, contests, and funding programs matched to your stage, industry, and location.",
        category="funding",
        inputs=[
            SkillInput(name="query", type="string", required=True, description="What you're looking for, e.g. 'AI safety grants for early-stage startups'"),
            SkillInput(name="stage", type="string", required=False, description="Company stage filter"),
            SkillInput(name="location", type="string", required=False),
            SkillInput(name="industry", type="array", required=False),
        ],
        example_prompts=[
            "Find grants for AI safety research",
            "What non-dilutive funding is available for pre-seed climate startups?",
            "Show me contests with deadlines in the next 60 days",
        ],
        tool_name="grants.search",
    )
)
