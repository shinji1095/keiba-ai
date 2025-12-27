from __future__ import annotations


def _login_admin(client):
    r = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpass"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token_type"] == "Bearer"
    assert (
        isinstance(data["access_token"], str)
        and len(data["access_token"]) > 20
    )
    assert data["expires_in"] > 0
    assert any(k.lower() == "set-cookie" for k in r.headers.keys())
    return data["access_token"]


def test_login_refresh_logout(client):
    _login_admin(client)

    old_cookie = client.cookies.get("refresh_token")
    assert old_cookie is not None

    r2 = client.post("/auth/refresh")
    assert r2.status_code == 200, r2.text
    new_cookie = client.cookies.get("refresh_token")
    assert new_cookie is not None
    assert new_cookie != old_cookie

    r3 = client.post("/auth/logout")
    assert r3.status_code in (200, 204), r3.text
    set_cookie = r3.headers.get("set-cookie", "")
    assert "max-age=0" in set_cookie.lower()
