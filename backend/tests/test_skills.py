from __future__ import annotations

import pytest

from backend.services.skills_registry import (
    SkillDescriptor,
    SkillInput,
    _REGISTRY,
    list_skills,
)


# ── HTTP tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_skills_returns_grants(client):
    res = await client.get("/api/skills")
    assert res.status_code == 200
    body = res.json()
    assert body["version"] == "v1"
    assert body["count"] == 1
    assert len(body["skills"]) == 1
    assert body["skills"][0]["id"] == "grants"


@pytest.mark.asyncio
async def test_list_skills_unknown_version_returns_empty(client):
    res = await client.get("/api/skills", params={"version": "v2"})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 0
    assert body["skills"] == []


@pytest.mark.asyncio
async def test_list_skills_status_all_returns_same(client):
    res = await client.get("/api/skills", params={"status": "all"})
    assert res.status_code == 200
    body = res.json()
    # No deprecated skills exist yet — count stays 1.
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_get_skill_returns_full_descriptor(client):
    res = await client.get("/api/skills/grants")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "grants"
    assert body["version"] == "v1"
    assert body["tool_name"] == "grants.search"
    assert len(body["inputs"]) == 4
    assert len(body["example_prompts"]) == 3


@pytest.mark.asyncio
async def test_get_skill_nonexistent_returns_404(client):
    res = await client.get("/api/skills/nonexistent")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_get_skill_wrong_version_returns_404(client):
    res = await client.get("/api/skills/grants", params={"version": "v2"})
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


# ── Registry unit test ────────────────────────────────────────────────────


def test_registry_order_by_category_then_id(monkeypatch):
    """Direct registry test: two skills ordered by (category, id)."""
    fake_key = ("v1", "research")
    fake_skill = SkillDescriptor(
        id="research",
        name="Market Research",
        version="v1",
        status="active",
        description="Research markets and competitors.",
        category="analysis",
        inputs=[SkillInput(name="topic", type="string", required=True)],
        example_prompts=["Research the fintech landscape"],
    )
    monkeypatch.setitem(_REGISTRY, fake_key, fake_skill)

    skills = list_skills("v1", "active")
    assert len(skills) == 2
    # "analysis" < "funding" → research comes before grants
    assert skills[0].id == "research"
    assert skills[0].category == "analysis"
    assert skills[1].id == "grants"
    assert skills[1].category == "funding"
