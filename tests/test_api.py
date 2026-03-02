"""Tests for FastAPI API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create test app with auth disabled."""
    from prism.api import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Test client with API key header."""
    client = TestClient(app)
    client.headers["X-API-Key"] = "test-key"
    return client


@pytest.fixture(autouse=True)
def mock_api_keys():
    """Allow test API key."""
    with patch("prism.api.deps.API_KEYS", ["test-key"]):
        yield


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestAccountEndpoints:
    def test_list_accounts(self, client):
        resp = client.get("/accounts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_account_not_found(self, client):
        resp = client.get("/accounts/nonexistent_xyz_abc")
        assert resp.status_code == 404

    def test_delete_account_not_found(self, client):
        resp = client.delete("/accounts/nonexistent_xyz_abc")
        assert resp.status_code == 404


class TestSignalEndpoints:
    def test_get_signals_not_found(self, client):
        resp = client.get("/accounts/nonexistent_xyz_abc/signals")
        assert resp.status_code == 404


class TestDossierEndpoints:
    def test_get_dossier_not_found(self, client):
        resp = client.get("/accounts/nonexistent_xyz_abc/dossier")
        assert resp.status_code == 404

    def test_get_dossier_by_id_not_found(self, client):
        resp = client.get("/dossiers/PRISM-9999-0001")
        assert resp.status_code == 404


class TestContentEndpoints:
    def test_upload_content_not_found(self, client):
        resp = client.post(
            "/accounts/nonexistent_xyz_abc/content",
            json={
                "source_type": "blog_post",
                "title": "Test Post",
                "raw_text": "Some content here",
                "publish_date": "2026-02-15",
            },
        )
        assert resp.status_code == 404


class TestAuthMiddleware:
    def test_missing_api_key(self, app):
        client = TestClient(app)
        resp = client.get("/accounts")
        assert resp.status_code == 401

    def test_invalid_api_key(self, app):
        client = TestClient(app)
        client.headers["X-API-Key"] = "wrong-key"
        resp = client.get("/accounts")
        assert resp.status_code == 401
