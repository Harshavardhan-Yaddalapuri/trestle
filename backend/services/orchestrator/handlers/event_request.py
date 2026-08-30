from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.orchestrator.events import FinishEvent, LLMTokenEvent, OrchestratorEvent

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


def _profile_is_ready_for_events(ctx: TurnContext) -> bool:
    """Return whether the profile has the fields used by event recommendations."""
    profile = ctx.profile
    return bool(
        profile.company_stage
        and profile.industry
        and profile.location and profile.location.strip()
        and profile.goals and profile.goals.strip()
    )


async def handle_event_request(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    """Direct founders to complete their profile before requesting event matches."""
    if not _profile_is_ready_for_events(ctx):
        yield LLMTokenEvent(
            delta=(
                "To recommend events, first add your company stage, industry, location, "
                "and goals to your profile. Complete it at /profile, then visit /events "
                "to see events matched to your company."
            )
        )
    else:
        yield LLMTokenEvent(
            delta="Your profile is ready for event recommendations. Visit /events to see your matches."
        )
    yield FinishEvent(reason="stop")
