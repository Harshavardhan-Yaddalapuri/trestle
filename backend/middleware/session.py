import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.config import get_settings

SESSION_HEADER = "X-Session-Id"


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        cookie_name = settings.SESSION_COOKIE_NAME

        session_id = request.cookies.get(cookie_name) or request.headers.get(
            SESSION_HEADER
        )
        set_cookie = False
        if not session_id:
            session_id = str(uuid.uuid4())
            set_cookie = True

        request.state.session_id = session_id
        structlog.contextvars.bind_contextvars(session_id=session_id)

        response = await call_next(request)

        if set_cookie:
            response.set_cookie(
                key=cookie_name,
                value=session_id,
                max_age=settings.SESSION_COOKIE_MAX_AGE,
                path="/",
                samesite="lax",
                httponly=False,
                secure=not settings.is_dev,
            )
        return response
