import pytest


@pytest.mark.asyncio
async def test_root_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_api_health(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert "db" in body
    assert "redis" in body
    assert body["db"]["status"] == "ok"
    assert body["redis"]["status"] == "ok"
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_session_cookie_set(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert "trestle_anon_session" in res.cookies


@pytest.mark.asyncio
async def test_request_id_header(client):
    res = await client.get("/health")
    assert "x-request-id" in {k.lower() for k in res.headers.keys()}
