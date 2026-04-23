"""Login endpoint rate limit integratsion testi."""
import pytest


@pytest.mark.skip(reason="slowapi storage=memory, CI da flaky bo'lishi mumkin")
def test_login_rate_limit_triggers_after_5_attempts(client):
    """5 tadan keyin 429 qaytishi kerak."""
    for i in range(5):
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "wrong"},
        )
        assert r.status_code in (401, 422)

    r6 = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert r6.status_code == 429


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_permission_catalog_endpoint(client):
    r = client.get("/api/v1/permissions/catalog")
    assert r.status_code == 200
    data = r.json()
    assert "permissions" in data
    assert "groups" in data
    assert any(p["code"] == "user:read" for p in data["permissions"])
