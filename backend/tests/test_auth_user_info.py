from pathlib import Path
import sys
import json

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.auth.menus import login_get_user


class DummyUser:
    id = 1


@pytest.mark.asyncio
async def test_auth_user_info_allows_empty_body(monkeypatch):
    calls = {}

    def fake_get_user_role_info(db, user, team_id):
        calls["db"] = db
        calls["user"] = user
        calls["team_id"] = team_id
        return {"userinfo": {"id": user.id}}

    monkeypatch.setattr(
        "apps.auth.menus.rbd_service.get_user_role_info",
        fake_get_user_role_info,
    )

    response = await login_get_user(request_data=None, db=object(), user=DummyUser())
    payload = json.loads(response.body)

    assert payload["code"] == 2000
    assert payload["data"]["userinfo"]["id"] == 1
    assert calls["team_id"] is None
