import base64
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.clerk import AuthError, derive_issuer, verify_session_token
from app.config import Settings
from app.db.base import Base
from app.db.session import get_session
from app.deps import get_db
from app.main import app


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


class MockJWKClient:
    def __init__(self, public_key: Any) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> Any:
        class MockKey:
            def __init__(self, key: Any) -> None:
                self.key = key

        return MockKey(self.public_key)


def test_derive_issuer() -> None:
    # Build a sample Clerk publishable key
    host = "clerk.example.com$"
    encoded = base64.b64encode(host.encode("utf-8")).decode("utf-8").rstrip("=")
    pub_key = f"pk_test_{encoded}"

    issuer = derive_issuer(pub_key)
    assert issuer == "https://clerk.example.com"

    with pytest.raises(AuthError):
        derive_issuer("")

    with pytest.raises(AuthError):
        derive_issuer("invalid_key_format")


def test_verify_session_token_success_and_failures(rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]) -> None:
    private_key, public_key = rsa_keys
    jwk_client = MockJWKClient(public_key)

    settings = Settings(
        clerk_issuer="https://clerk.example.com",
        clerk_authorized_parties="http://localhost:8080,http://localhost:5173",
    )

    now = int(time.time())
    payload = {
        "sub": "user_2test123",
        "email": "user@example.com",
        "iss": "https://clerk.example.com",
        "azp": "http://localhost:8080",
        "iat": now,
        "exp": now + 300,
    }

    # 1. Valid token
    valid_token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "k1"})
    claims = verify_session_token(valid_token, settings, jwk_client=jwk_client)
    assert claims["sub"] == "user_2test123"
    assert claims["email"] == "user@example.com"

    # 2. Expired token
    expired_payload = dict(payload, exp=now - 60)
    expired_token = jwt.encode(expired_payload, private_key, algorithm="RS256", headers={"kid": "k1"})
    with pytest.raises(AuthError):
        verify_session_token(expired_token, settings, jwk_client=jwk_client)

    # 3. Wrong issuer
    wrong_iss_payload = dict(payload, iss="https://wrong.issuer.com")
    wrong_iss_token = jwt.encode(wrong_iss_payload, private_key, algorithm="RS256", headers={"kid": "k1"})
    with pytest.raises(AuthError):
        verify_session_token(wrong_iss_token, settings, jwk_client=jwk_client)

    # 4. Wrong azp
    wrong_azp_payload = dict(payload, azp="http://attacker.com")
    wrong_azp_token = jwt.encode(wrong_azp_payload, private_key, algorithm="RS256", headers={"kid": "k1"})
    with pytest.raises(AuthError):
        verify_session_token(wrong_azp_token, settings, jwk_client=jwk_client)

    # 5. Tampered signature
    tampered_token = valid_token[:-4] + "abcd"
    with pytest.raises(AuthError):
        verify_session_token(tampered_token, settings, jwk_client=jwk_client)

    # 6. alg=none
    none_token = jwt.encode(payload, key="", algorithm="none")
    with pytest.raises(AuthError):
        verify_session_token(none_token, settings, jwk_client=jwk_client)


def test_api_me_endpoint_and_user_creation(test_db, rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey], monkeypatch) -> None:
    private_key, public_key = rsa_keys
    client = TestClient(app)

    # Missing header -> 401
    resp_no_auth = client.get("/api/me")
    assert resp_no_auth.status_code == 401
    assert resp_no_auth.json() == {"detail": "Not authenticated"}

    # Invalid header -> 401
    resp_bad = client.get("/api/me", headers={"Authorization": "InvalidToken"})
    assert resp_bad.status_code == 401

    # Override get_db and get_session to use test SQLite
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_session] = lambda: test_db

    # Monkeypatch verify_session_token to return valid claims
    calls = 0

    def mock_verify(token: str, settings: Any, jwk_client: Any = None) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if token == "good_token":
            return {
                "sub": "clerk_unique_123",
                "email": "analyst@example.com",
            }
        raise AuthError("Invalid token")

    monkeypatch.setattr("app.auth.clerk.verify_session_token", mock_verify)

    # First call creates the user
    resp1 = client.get("/api/me", headers={"Authorization": "Bearer good_token"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["clerk_user_id"] == "clerk_unique_123"
    assert data1["email"] == "analyst@example.com"
    user_id_1 = data1["id"]

    # Second call reuses existing user
    resp2 = client.get("/api/me", headers={"Authorization": "Bearer good_token"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["id"] == user_id_1
    assert data2["clerk_user_id"] == "clerk_unique_123"

    # Bad token gives 401 Invalid or expired session
    resp_bad_token = client.get("/api/me", headers={"Authorization": "Bearer expired_token"})
    assert resp_bad_token.status_code == 401
    assert resp_bad_token.json() == {"detail": "Invalid or expired session"}

    app.dependency_overrides.clear()
