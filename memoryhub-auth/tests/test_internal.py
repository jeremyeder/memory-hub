"""Tests for the internal API-key validation endpoint."""
import hashlib
import os
import uuid
from datetime import UTC, datetime

import pytest

# Set env vars before importing src modules.
os.environ.setdefault("AUTH_ADMIN_KEY", "test-admin-key")
os.environ["AUTH_INTERNAL_SERVICE_KEY"] = "test-service-key"

from src.models import OAuthClient  # noqa: E402

SERVICE_HEADERS = {"X-Service-Key": "test-service-key"}
ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}

API_KEY = "mh-dev-abcdef0123456789"
API_KEY_HASH = hashlib.sha256(API_KEY.encode()).hexdigest()


@pytest.fixture
def _set_service_key(monkeypatch):
    monkeypatch.setenv("AUTH_INTERNAL_SERVICE_KEY", "test-service-key")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_service_key")
class TestValidateApiKey:
    async def test_validate_valid_api_key(self, client, db_session):
        # Insert a client with a known api_key_hash
        obj = OAuthClient(
            id=str(uuid.uuid4()),
            client_id="key-agent",
            client_secret_hash="unused",
            client_name="Key Agent",
            identity_type="service",
            tenant_id="key-tenant",
            default_scopes=["memory:read", "memory:write:user"],
            active=True,
            api_key_hash=API_KEY_HASH,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(obj)
        await db_session.commit()

        resp = await client.post(
            "/internal/validate-api-key",
            json={"api_key": API_KEY},
            headers=SERVICE_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user_id"] == "key-agent"
        assert data["name"] == "Key Agent"
        assert data["identity_type"] == "service"
        assert data["tenant_id"] == "key-tenant"
        assert data["scopes"] == ["memory:read", "memory:write:user"]

    async def test_validate_invalid_api_key(self, client):
        resp = await client.post(
            "/internal/validate-api-key",
            json={"api_key": "mh-dev-badbadbadbadbadb"},
            headers=SERVICE_HEADERS,
        )
        assert resp.status_code == 401, resp.text

    async def test_validate_missing_service_key(self, client):
        resp = await client.post(
            "/internal/validate-api-key",
            json={"api_key": API_KEY},
            # No X-Service-Key header
        )
        assert resp.status_code == 401, resp.text

    async def test_validate_inactive_client(self, client, db_session):
        inactive_key = "mh-dev-inactive12345678"
        inactive_hash = hashlib.sha256(inactive_key.encode()).hexdigest()
        obj = OAuthClient(
            id=str(uuid.uuid4()),
            client_id="inactive-key-agent",
            client_secret_hash="unused",
            client_name="Inactive Key Agent",
            identity_type="user",
            tenant_id="key-tenant",
            default_scopes=["memory:read"],
            active=False,
            api_key_hash=inactive_hash,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(obj)
        await db_session.commit()

        resp = await client.post(
            "/internal/validate-api-key",
            json={"api_key": inactive_key},
            headers=SERVICE_HEADERS,
        )
        assert resp.status_code == 401, resp.text
