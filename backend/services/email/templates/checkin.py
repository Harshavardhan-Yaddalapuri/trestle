from __future__ import annotations

from backend.services.email.templates import RenderedEmail
from backend.services.email.templates.base import wrap_html, wrap_text

_BTN = 'style="display:inline-block;background:#4f46e5;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;"'


def render(context: dict) -> RenderedEmail:
    track_count: int = context["track_count"]
    oldest_age_days: int = context["oldest_age_days"]
    top_grant_names: list[str] = context.get("top_grant_names", [])
    app_url: str = context["app_url"]
    unsubscribe_url: str = context["unsubscribe_url"]

    subject = "Still working on those grants?"

    grants_word = "grant" if track_count == 1 else "grants"
    grants_list_html = ""
    grants_list_text = ""
    if top_grant_names:
        items = "".join(f"<li>{name}</li>" for name in top_grant_names)
        grants_list_html = f"<ul>{items}</ul>"
        grants_list_text = "\n".join(f"- {name}" for name in top_grant_names) + "\n\n"

    body_html = (
        f"<h2>Check in on your grants</h2>"
        f"<p>You have <strong>{track_count} {grants_word}</strong> that "
        f"{'hasn\'t' if track_count == 1 else 'haven\'t'} been updated in {oldest_age_days} days.</p>"
        f"{grants_list_html}"
        f"<p>Still working on these? Log in to update your progress.</p>"
        f'<p><a href="{app_url}" {_BTN}>Update progress</a></p>'
    )
    body_text = (
        f"Check in on your grants\n\n"
        f"You have {track_count} grant application(s) that "
        f"haven't been updated in {oldest_age_days} days.\n\n"
        f"{grants_list_text}"
        f"Still working on these? Log in to update your progress:\n{app_url}"
    )

    return RenderedEmail(
        subject=subject,
        html=wrap_html(body_html, unsubscribe_url=unsubscribe_url),
        text=wrap_text(body_text, unsubscribe_url=unsubscribe_url),
    )
