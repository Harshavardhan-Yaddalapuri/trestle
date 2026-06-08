"""Email management endpoints — unsubscribe flow."""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.user import User
from backend.db.session import get_db

router = APIRouter(prefix="/email", tags=["email"])

_VALID_KINDS = frozenset({"deadline_reminders", "new_grant_matches", "check_ins", "all"})


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(
    token: str = "",
    kind: str = "",
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    if not token or kind not in _VALID_KINDS:
        return HTMLResponse(
            _page("Invalid link", "<p>This unsubscribe link is invalid.</p>"),
            status_code=400,
        )

    result = await db.execute(
        sa.select(User).where(User.alert_unsubscribe_token == token)
    )
    user = result.scalar_one_or_none()

    if user is None:
        return HTMLResponse(
            _page("Link not found", "<p>This unsubscribe link was not found.</p>"),
            status_code=404,
        )

    prefs = dict(user.alert_preferences or {})
    if kind == "all":
        prefs["deadline_reminders"] = False
        prefs["new_grant_matches"] = False
        prefs["check_ins"] = False
        description = "all email notifications"
    else:
        prefs[kind] = False
        description = kind.replace("_", " ")

    user.alert_preferences = prefs
    await db.commit()

    return HTMLResponse(
        _page(
            "Unsubscribed",
            f"<p>You've been unsubscribed from <strong>{description}</strong>.</p>"
            "<p>You can re-enable notifications from your account settings.</p>",
        )
    )


def _page(title: str, body_html: str) -> str:
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{title}</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;max-width:600px;margin:80px auto;padding:0 20px;color:#333;}"
        "h1{color:#111;}"
        "</style>"
        "</head><body>"
        f"<h1>{title}</h1>"
        f"{body_html}"
        "</body></html>"
    )
