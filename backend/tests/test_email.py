"""Tests for Step 18: ResendEmailClient, email templates, unsubscribe flow, dev safety."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
import pytest
import respx
import sqlalchemy as sa

from backend.core.errors import UpstreamError
from backend.services.email.dependency import DevSafeEmailClient
from backend.services.email.log import LogEmailClient
from backend.services.email.resend import ResendEmailClient
from backend.services.email.templates import RenderedEmail, render_email
from backend.services.email.types import EmailSendResult

# ── ResendEmailClient tests (1–6) ─────────────────────────────────────────────


def _resend_client(**kwargs) -> ResendEmailClient:
    return ResendEmailClient(
        api_key=kwargs.get("api_key", "re_test_key"),
        from_address=kwargs.get("from_address", "no-reply@example.com"),
        from_name=kwargs.get("from_name", "Trestle Test"),
        reply_to=kwargs.get("reply_to"),
    )


@pytest.mark.asyncio
async def test_resend_client_success():
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "msg-abc123"})
        )
        client = _resend_client()
        result = await client.send(
            to="user@example.com",
            subject="Hello",
            html="<p>Hello</p>",
            text="Hello",
        )
    assert result.success is True
    assert result.message_id == "msg-abc123"


@pytest.mark.asyncio
async def test_resend_client_201_accepted():
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(201, json={"id": "msg-def456"})
        )
        client = _resend_client()
        result = await client.send(to="u@x.com", subject="Hi", html="<p>Hi</p>", text="Hi")
    assert result.success is True
    assert result.message_id == "msg-def456"


@pytest.mark.asyncio
async def test_resend_client_tags_formatted_correctly():
    with respx.mock:
        route = respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "x"})
        )
        client = _resend_client()
        await client.send(
            to="u@x.com", subject="Hi", html="<p>Hi</p>", text="Hi",
            tags=["magic_link", "transactional"],
        )
    sent_body = route.calls[0].request.content
    import json
    payload = json.loads(sent_body)
    assert payload["tags"] == [
        {"name": "category", "value": "magic_link"},
        {"name": "category", "value": "transactional"},
    ]


@pytest.mark.asyncio
async def test_resend_client_401_raises_invalid_credentials():
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )
        client = _resend_client()
        with pytest.raises(UpstreamError) as exc_info:
            await client.send(to="u@x.com", subject="Hi", html="<p>Hi</p>", text="Hi")
    assert exc_info.value.code == "invalid_credentials"


@pytest.mark.asyncio
async def test_resend_client_422_raises_invalid_recipient():
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(422, json={"message": "Invalid email"})
        )
        client = _resend_client()
        with pytest.raises(UpstreamError) as exc_info:
            await client.send(to="bad@bad", subject="Hi", html="<p>Hi</p>", text="Hi")
    assert exc_info.value.code == "invalid_recipient"


@pytest.mark.asyncio
async def test_resend_client_429_raises_rate_limited():
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(
                429,
                json={"message": "Rate limited"},
                headers={"Retry-After": "30"},
            )
        )
        client = _resend_client()
        with pytest.raises(UpstreamError) as exc_info:
            await client.send(to="u@x.com", subject="Hi", html="<p>Hi</p>", text="Hi")
    assert exc_info.value.code == "rate_limited"
    assert "30" in exc_info.value.detail


@pytest.mark.asyncio
async def test_resend_client_500_raises_upstream_unavailable():
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(500, json={"message": "Internal Server Error"})
        )
        client = _resend_client()
        with pytest.raises(UpstreamError) as exc_info:
            await client.send(to="u@x.com", subject="Hi", html="<p>Hi</p>", text="Hi")
    assert exc_info.value.code == "upstream_unavailable"


# ── Template tests (8–14) ─────────────────────────────────────────────────────


def test_magic_link_template_renders():
    rendered = render_email("magic_link", {
        "magic_url": "http://localhost:3000/auth/verify?token=abc123",
        "app_name": "Trestle",
        "ttl_minutes": 15,
    })
    assert isinstance(rendered, RenderedEmail)
    assert "Sign in to Trestle" in rendered.subject
    assert "http://localhost:3000/auth/verify?token=abc123" in rendered.html
    assert "http://localhost:3000/auth/verify?token=abc123" in rendered.text


def test_magic_link_no_unsubscribe_footer():
    rendered = render_email("magic_link", {
        "magic_url": "http://localhost:3000/auth/verify?token=abc",
        "app_name": "Trestle",
        "ttl_minutes": 15,
    })
    assert "Unsubscribe" not in rendered.html
    assert "unsubscribe" not in rendered.text.lower()


def test_deadline_template_subject_includes_days_and_name():
    rendered = render_email("deadline_reminder", {
        "grant_name": "NSF SBIR Phase I",
        "window_days": 14,
        "deadline_str": "2026-07-01",
        "app_url": "http://localhost:3000",
        "unsubscribe_url": "http://localhost:3000/api/email/unsubscribe?token=tok&kind=deadline_reminders",
    })
    assert "14 days" in rendered.subject
    assert "NSF SBIR Phase I" in rendered.subject
    assert "NSF SBIR Phase I" in rendered.html
    assert "2026-07-01" in rendered.html
    assert "Unsubscribe" in rendered.html
    assert "unsubscribe" in rendered.text.lower()


def test_new_grant_template_includes_score_and_name():
    rendered = render_email("new_grant_match", {
        "grant_name": "DOE Clean Energy",
        "score": 0.82,
        "tier": "strong",
        "app_url": "http://localhost:3000",
        "unsubscribe_url": "http://localhost:3000/api/email/unsubscribe?token=tok&kind=new_grant_matches",
    })
    assert "DOE Clean Energy" in rendered.subject
    assert "DOE Clean Energy" in rendered.html
    assert "strong" in rendered.html
    assert "82%" in rendered.html
    assert "Unsubscribe" in rendered.html


def test_checkin_template_includes_count_and_days():
    rendered = render_email("check_in", {
        "track_count": 3,
        "oldest_age_days": 21,
        "top_grant_names": ["Grant A", "Grant B"],
        "app_url": "http://localhost:3000",
        "unsubscribe_url": "http://localhost:3000/api/email/unsubscribe?token=tok&kind=check_ins",
    })
    assert "still working" in rendered.subject.lower()
    assert "3" in rendered.html
    assert "21" in rendered.html
    assert "Grant A" in rendered.html
    assert "Unsubscribe" in rendered.html


def test_render_email_unknown_template_raises():
    with pytest.raises(ValueError, match="Unknown email template"):
        render_email("does_not_exist", {})


def test_wrap_html_includes_unsubscribe_when_url_provided():
    from backend.services.email.templates.base import wrap_html
    html = wrap_html("<p>Body</p>", unsubscribe_url="https://example.com/unsub")
    assert "https://example.com/unsub" in html
    assert "Unsubscribe" in html


def test_wrap_html_no_unsubscribe_when_url_omitted():
    from backend.services.email.templates.base import wrap_html
    html = wrap_html("<p>Body</p>")
    assert "Unsubscribe" not in html


def test_wrap_text_appends_unsubscribe():
    from backend.services.email.templates.base import wrap_text
    text = wrap_text("Hello world", unsubscribe_url="https://example.com/unsub")
    assert "https://example.com/unsub" in text
    assert "unsubscribe" in text.lower()


# ── DevSafeEmailClient tests (18–20) ──────────────────────────────────────────


class _CapturingClient:
    def __init__(self):
        self.calls: list[str] = []

    async def send(self, to, subject, html, text, tags=None, template_id=None):
        self.calls.append(to)
        return EmailSendResult(success=True)


@pytest.mark.asyncio
async def test_dev_safe_sends_to_allowed_domain():
    inner = _CapturingClient()
    log = LogEmailClient()
    safe = DevSafeEmailClient(inner, "example.com", log)

    result = await safe.send(
        to="dev@example.com", subject="Test", html="<p>T</p>", text="T"
    )
    assert result.success is True
    assert "dev@example.com" in inner.calls


@pytest.mark.asyncio
async def test_dev_safe_blocks_other_domain(capfd):
    inner = _CapturingClient()
    fallback = _CapturingClient()
    safe = DevSafeEmailClient(inner, "example.com", fallback)

    await safe.send(to="user@other.com", subject="Test", html="<p>T</p>", text="T")
    assert len(inner.calls) == 0
    assert "user@other.com" in fallback.calls


@pytest.mark.asyncio
async def test_dev_safe_strips_at_sign_from_domain():
    inner = _CapturingClient()
    fallback = _CapturingClient()
    safe = DevSafeEmailClient(inner, "@example.com", fallback)  # leading @

    await safe.send(to="dev@example.com", subject="Test", html="<p>T</p>", text="T")
    assert "dev@example.com" in inner.calls


# ── Unsubscribe endpoint tests (21–25) ────────────────────────────────────────


async def _make_user_with_token(session_factory, *, email: str, token: str, prefs: dict | None = None):
    from backend.db.models.user import User
    async with session_factory() as db:
        async with db.begin():
            user = User(
                email=email,
                email_normalized=email.lower(),
                email_verified_at=datetime.now(timezone.utc),
                alert_unsubscribe_token=token,
                alert_preferences=prefs or {},
            )
            db.add(user)
            await db.flush()
            uid = user.id
    async with session_factory() as db:
        result = await db.execute(sa.select(User).where(User.id == uid))
        return result.scalar_one()


@pytest.mark.asyncio
async def test_unsubscribe_deadline_reminders(client, session_factory):
    token = f"tok-{uuid.uuid4().hex[:16]}"
    user = await _make_user_with_token(
        session_factory, email="unsub1@example.com", token=token
    )
    resp = await client.get(f"/api/email/unsubscribe?token={token}&kind=deadline_reminders")
    assert resp.status_code == 200
    assert "Unsubscribed" in resp.text

    from backend.db.models.user import User
    async with session_factory() as db:
        result = await db.execute(sa.select(User).where(User.id == user.id))
        updated = result.scalar_one()
    assert updated.alert_preferences.get("deadline_reminders") is False


@pytest.mark.asyncio
async def test_unsubscribe_all_kinds(client, session_factory):
    token = f"tok-{uuid.uuid4().hex[:16]}"
    await _make_user_with_token(session_factory, email="unsub2@example.com", token=token)
    resp = await client.get(f"/api/email/unsubscribe?token={token}&kind=all")
    assert resp.status_code == 200

    from backend.db.models.user import User
    async with session_factory() as db:
        result = await db.execute(
            sa.select(User).where(User.alert_unsubscribe_token == token)
        )
        updated = result.scalar_one()
    prefs = updated.alert_preferences
    assert prefs.get("deadline_reminders") is False
    assert prefs.get("new_grant_matches") is False
    assert prefs.get("check_ins") is False


@pytest.mark.asyncio
async def test_unsubscribe_invalid_token_returns_404(client):
    resp = await client.get("/api/email/unsubscribe?token=notavalidtoken&kind=check_ins")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unsubscribe_missing_kind_returns_400(client):
    resp = await client.get("/api/email/unsubscribe?token=sometoken&kind=")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unsubscribe_invalid_kind_returns_400(client):
    resp = await client.get("/api/email/unsubscribe?token=sometoken&kind=nonexistent_kind")
    assert resp.status_code == 400


# ── build_unsubscribe_url helper ──────────────────────────────────────────────


def test_build_unsubscribe_url_format():
    from backend.services.email import build_unsubscribe_url
    from backend.core.config import get_settings

    settings = get_settings()

    class _FakeUser:
        alert_unsubscribe_token = "mytoken123"

    url = build_unsubscribe_url(settings, _FakeUser(), "deadline_reminders")
    assert url.startswith(settings.AUTH_BASE_URL)
    assert "token=mytoken123" in url
    assert "kind=deadline_reminders" in url
