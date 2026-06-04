from __future__ import annotations

from backend.services.email.templates import RenderedEmail
from backend.services.email.templates.base import wrap_html, wrap_text

_BTN = 'style="display:inline-block;background:#4f46e5;color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;"'


def render(context: dict) -> RenderedEmail:
    grant_name: str = context["grant_name"]
    score: float = context["score"]
    tier: str = context["tier"]
    app_url: str = context["app_url"]
    unsubscribe_url: str = context["unsubscribe_url"]

    subject = f"New grant match: {grant_name}"

    body_html = (
        f"<h2>New grant match</h2>"
        f'<p>We found a new grant that matches your profile: <strong>{grant_name}</strong>.</p>'
        f"<p>Match strength: <strong>{tier}</strong> ({score:.0%})</p>"
        f'<p><a href="{app_url}" {_BTN}>View grant</a></p>'
    )
    body_text = (
        f"New grant match\n\n"
        f'We found a new grant that matches your profile: "{grant_name}".\n\n'
        f"Match strength: {tier} ({score:.0%})\n\n"
        f"View the grant on Trestle:\n{app_url}"
    )

    return RenderedEmail(
        subject=subject,
        html=wrap_html(body_html, unsubscribe_url=unsubscribe_url),
        text=wrap_text(body_text, unsubscribe_url=unsubscribe_url),
    )
