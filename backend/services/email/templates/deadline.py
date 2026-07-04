from __future__ import annotations

from backend.services.email.templates import RenderedEmail
from backend.services.email.templates.base import wrap_html, wrap_text

_BTN = 'style="display:inline-block;background:#4f46e5;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;"'


def render(context: dict) -> RenderedEmail:
    grant_name: str = context["grant_name"]
    window_days: int = context["window_days"]
    deadline_str: str = context["deadline_str"]
    app_url: str = context["app_url"]
    unsubscribe_url: str = context["unsubscribe_url"]

    subject = f"{window_days} days: {grant_name} deadline"

    body_html = (
        f"<h2>Grant deadline approaching</h2>"
        f"<p>The deadline for <strong>{grant_name}</strong> is in "
        f"<strong>{window_days} days</strong> ({deadline_str}).</p>"
        f"<p>Log in to Trestle to update your application status.</p>"
        f'<p><a href="{app_url}" {_BTN}>Update application</a></p>'
    )
    body_text = (
        f"Grant deadline approaching\n\n"
        f'The deadline for "{grant_name}" is in {window_days} days ({deadline_str}).\n\n'
        f"Log in to update your application status:\n{app_url}"
    )

    return RenderedEmail(
        subject=subject,
        html=wrap_html(body_html, unsubscribe_url=unsubscribe_url),
        text=wrap_text(body_text, unsubscribe_url=unsubscribe_url),
    )
