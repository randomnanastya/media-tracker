async def test_full_register_and_login_flow(client_with_db, session_for_test, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-integration-secret-32chars!!")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")

    reg_resp = await client_with_db.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "testpass123"},
    )
    assert reg_resp.status_code == 201
    recovery_code = reg_resp.json()["recovery_code"]
    assert "-" in recovery_code

    login_resp = await client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client_with_db.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"


async def test_register_closed_after_first_user(client_with_db, session_for_test, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-integration-secret-32chars!!")

    resp1 = await client_with_db.post(
        "/api/v1/auth/register",
        json={"username": "first", "password": "testpass123"},
    )
    assert resp1.status_code == 201

    resp2 = await client_with_db.post(
        "/api/v1/auth/register",
        json={"username": "second", "password": "testpass123"},
    )
    assert resp2.status_code == 403


async def test_refresh_token_rotation(client_with_db, session_for_test, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-integration-secret-32chars!!")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")

    await client_with_db.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "testpass123"},
    )
    login_resp = await client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    old_refresh = login_resp.json()["refresh_token"]

    refresh_resp = await client_with_db.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != old_refresh

    old_refresh_resp = await client_with_db.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert old_refresh_resp.status_code == 401


async def test_logout_invalidates_token(authenticated_client, session_for_test, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-integration-secret-32chars!!")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")

    login_resp = await authenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpassword123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await authenticated_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200

    refresh_resp = await authenticated_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401


async def test_reset_password_with_recovery_code(client_with_db, session_for_test, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-integration-secret-32chars!!")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")

    reg_resp = await client_with_db.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "testpass123"},
    )
    recovery_code = reg_resp.json()["recovery_code"]

    reset_resp = await client_with_db.post(
        "/api/v1/auth/reset-password",
        json={"recovery_code": recovery_code, "new_password": "newpass123"},
    )
    assert reset_resp.status_code == 200
    assert "new_recovery_code" in reset_resp.json()

    login_resp = await client_with_db.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "newpass123"},
    )
    assert login_resp.status_code == 200


async def test_change_password(authenticated_client, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-integration-secret-32chars!!")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")

    resp = await authenticated_client.put(
        "/api/v1/auth/me/password",
        json={"current_password": "testpassword123", "new_password": "newpass456"},
    )
    assert resp.status_code == 200

    login_old = await authenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpassword123"},
    )
    assert login_old.status_code == 401

    login_new = await authenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "newpass456"},
    )
    assert login_new.status_code == 200


async def test_existing_endpoints_require_auth(client_with_db):
    response = await client_with_db.post("/api/v1/radarr/import")
    assert response.status_code == 403
