import importlib

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.config import get_settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database_path = (tmp_path / "test.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ADMIN_USERNAME", "tester")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")
    monkeypatch.setenv("ADMIN_DISPLAY_NAME", "测试用户")
    get_settings.cache_clear()

    import app.main as main

    main = importlib.reload(main)
    with TestClient(main.app) as test_client:
        yield test_client
    db_module.dispose_engine()
    get_settings.cache_clear()


def login(client: TestClient, password: str = "secret123"):
    return client.post(
        "/api/v1/auth/login",
        json={"username": "tester", "password": password},
    )


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_token_and_user(client: TestClient):
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {"id": 1, "username": "tester", "display_name": "测试用户"}


def test_login_is_case_insensitive_for_username(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "TESTER", "password": "secret123"},
    )
    assert response.status_code == 200


def test_login_rejects_wrong_password(client: TestClient):
    response = login(client, "wrong-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_me_requires_token(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_current_user(client: TestClient):
    token = login(client).json()["access_token"]
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "tester"


def test_logout_accepts_valid_token(client: TestClient):
    token = login(client).json()["access_token"]
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
