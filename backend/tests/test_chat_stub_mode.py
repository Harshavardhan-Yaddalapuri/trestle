from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from backend.core.config import get_settings
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis


async def collect_sse(response) -> list[dict]:
    events = []
    current_id = None
    current_event = "message"
    current_data = ""
    async for line in response.aiter_lines():
        if line.startswith("id: "):
            current_id = line[4:]
        elif line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data += line[6:]
        elif line == "":
            if current_data:
                import json

                try:
                    parsed = json.loads(current_data)
                except json.JSONDecodeError:
                    parsed = current_data
                events.append({"id": current_id, "event": current_event, "data": parsed})
            current_id = None
            current_event = "message"
            current_data = ""
    return events


async def test_chat_stub_mode_does_not_require_llm_dependency(
    monkeypatch,
    session_factory,
    redis_client,
):
    monkeypatch.setenv("CHAT_USE_ORCHESTRATOR", "false")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PRIMARY", raising=False)
    get_settings.cache_clear()

    app = create_app()

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = lambda: session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        res = await ac.post("/api/chat/message", json={"content": "hello"})
        assert res.status_code == 200
        events = await collect_sse(res)

    names = [event["event"] for event in events]
    assert "token" in names
    assert "done" in names
