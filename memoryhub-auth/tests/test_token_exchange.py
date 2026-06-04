"""Tests for OAuth 2.1 token exchange grant (RFC 8693)."""

import uuid
from unittest.mock import AsyncMock, patch

import bcrypt
import jwt as pyjwt
import pytest
from httpx import AsyncClient

from src.errors import OAuthError
from src.keys import get_public_key
from src.models import OAuthClient

GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
VALID_TOKEN_REVIEW = {
    "username": "system:serviceaccount:test-ns:my-agent",
    "groups": ["system:serviceaccounts", "system:authenticated"],
    "authenticated": True,
}


@pytest.fixture(autouse=True)
def _clear_token_exchange_caches():
    import src.token_exchange
    src.token_exchange._sa_token_cache = None
    src.token_exchange._tenant_cache = {}
    src.token_exchange._k8s_client_cache = None
    yield
    src.token_exchange._sa_token_cache = None
    src.token_exchange._tenant_cache = {}
    src.token_exchange._k8s_client_cache = None


def _mock_k8s(username="system:serviceaccount:test-ns:my-agent", tenant="test-tenant"):
    """Return stacked context manager mocking validate_subject_token and resolve_tenant."""
    validate = patch(
        "src.routes.token.validate_subject_token",
        new_callable=AsyncMock,
        return_value={
            "username": username,
            "groups": ["system:serviceaccounts", "system:authenticated"],
            "authenticated": True,
        },
    )
    resolve = patch(
        "src.routes.token.resolve_tenant",
        new_callable=AsyncMock,
        return_value=tenant,
    )
    return validate, resolve


@pytest.mark.asyncio
class TestTokenExchange:

    async def test_valid_exchange_returns_jwt(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        mock_v, mock_r = _mock_k8s()
        with mock_v, mock_r:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "fake-k8s-token",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 300
        assert data["issued_token_type"] == "urn:ietf:params:oauth:token-type:access_token"
        assert set(data["scope"].split()) == {"memory:read", "memory:write:user"}

        decoded = pyjwt.decode(
            data["access_token"],
            get_public_key(),
            algorithms=["RS256"],
            audience="memoryhub",
        )
        assert decoded["iss"] == "https://test-auth.example.com"
        assert decoded["aud"] == "memoryhub"
        assert decoded["sub"] == "system:serviceaccount:test-ns:my-agent"
        assert decoded["tenant_id"] == "test-tenant"
        assert decoded["identity_type"] == "user"
        assert set(decoded["scopes"]) == {"memory:read", "memory:write:user"}

    async def test_valid_exchange_with_scope_subsetting(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        mock_v, mock_r = _mock_k8s()
        with mock_v, mock_r:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "fake-k8s-token",
                    "scope": "memory:read",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["scope"] == "memory:read"

        decoded = pyjwt.decode(
            data["access_token"],
            get_public_key(),
            algorithms=["RS256"],
            audience="memoryhub",
        )
        assert decoded["scopes"] == ["memory:read"]

    async def test_valid_exchange_with_explicit_subject_token_type(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        mock_v, mock_r = _mock_k8s()
        with mock_v, mock_r:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "fake-k8s-token",
                    "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
                },
            )

        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_missing_client_id_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/token",
            data={
                "grant_type": GRANT_TYPE,
                "subject_token": "fake-k8s-token",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_request"
        assert "client_id" in response.json()["error_description"].lower()

    async def test_missing_subject_token_returns_400(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        response = await client.post(
            "/token",
            data={
                "grant_type": GRANT_TYPE,
                "client_id": "test-agent",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_request"
        assert "subject_token" in response.json()["error_description"].lower()

    async def test_unsupported_subject_token_type_returns_400(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        response = await client.post(
            "/token",
            data={
                "grant_type": GRANT_TYPE,
                "client_id": "test-agent",
                "subject_token": "fake-k8s-token",
                "subject_token_type": "urn:ietf:params:oauth:token-type:saml2",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_request"

    async def test_invalid_scope_returns_400(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        mock_v, mock_r = _mock_k8s()
        with mock_v, mock_r:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "fake-k8s-token",
                    "scope": "memory:admin",
                },
            )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_scope"

    async def test_unknown_client_id_returns_401(self, client: AsyncClient):
        mock_v, mock_r = _mock_k8s()
        with mock_v, mock_r:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "nonexistent-client",
                    "subject_token": "fake-k8s-token",
                },
            )
        assert response.status_code == 401
        assert response.json()["error"] == "invalid_client"

    async def test_inactive_client_returns_401(
        self, client: AsyncClient, db_session
    ):
        inactive = OAuthClient(
            id=str(uuid.uuid4()),
            client_id="inactive-exchange",
            client_secret_hash=bcrypt.hashpw(b"unused", bcrypt.gensalt()).decode(),
            client_name="Inactive Exchange",
            identity_type="service",
            tenant_id="test-tenant",
            default_scopes=["memory:read"],
            active=False,
        )
        db_session.add(inactive)
        await db_session.commit()

        mock_v, mock_r = _mock_k8s()
        with mock_v, mock_r:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "inactive-exchange",
                    "subject_token": "fake-k8s-token",
                },
            )
        assert response.status_code == 401
        assert response.json()["error"] == "invalid_client"

    async def test_sa_token_validation_failure_returns_401(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        with patch(
            "src.routes.token.validate_subject_token",
            new_callable=AsyncMock,
            side_effect=OAuthError(401, "invalid_grant", "Token validation failed"),
        ):
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "bad-k8s-token",
                },
            )
        assert response.status_code == 401
        assert response.json()["error"] == "invalid_grant"

    async def test_token_exchange_disabled_returns_400(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        with patch("src.routes.token.settings") as mock_settings:
            mock_settings.token_exchange_enabled = False
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "fake-k8s-token",
                },
            )
        assert response.status_code == 400
        assert response.json()["error"] == "unsupported_grant_type"

    async def test_resolve_tenant_called_with_correct_namespace(
        self, client: AsyncClient, sample_client: OAuthClient
    ):
        mock_v, mock_r = _mock_k8s(
            username="system:serviceaccount:my-namespace:my-agent",
            tenant="resolved-tenant",
        )
        with mock_v, mock_r as resolve_mock:
            response = await client.post(
                "/token",
                data={
                    "grant_type": GRANT_TYPE,
                    "client_id": "test-agent",
                    "subject_token": "fake-k8s-token",
                },
            )

        assert response.status_code == 200
        resolve_mock.assert_called_once_with("my-namespace")

        decoded = pyjwt.decode(
            response.json()["access_token"],
            get_public_key(),
            algorithms=["RS256"],
            audience="memoryhub",
        )
        assert decoded["tenant_id"] == "resolved-tenant"
