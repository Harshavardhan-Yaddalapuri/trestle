from __future__ import annotations


async def test_anonymous_alert_preferences_persist_by_session(client):
    initial = await client.get("/api/users/alert-preferences")
    assert initial.status_code == 200
    assert initial.json() == {
        "deadline_reminders": True,
        "new_grant_matches": True,
        "check_ins": True,
    }

    updated = await client.put(
        "/api/users/alert-preferences",
        json={"deadline_reminders": False, "check_ins": False},
    )
    assert updated.status_code == 200
    assert updated.json() == {
        "deadline_reminders": False,
        "new_grant_matches": True,
        "check_ins": False,
    }

    reloaded = await client.get("/api/users/alert-preferences")
    assert reloaded.status_code == 200
    assert reloaded.json() == updated.json()
