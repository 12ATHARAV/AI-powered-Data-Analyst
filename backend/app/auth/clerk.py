import base64
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import repo
from app.db.models import User
from app.db.session import get_session


class AuthError(Exception):
    """Raised when authentication fails."""
    pass


def derive_issuer(publishable_key: str) -> str:
    """Derive the Clerk issuer HTTPS URL from a publishable key."""
    if not publishable_key:
        raise AuthError("Clerk publishable key is missing")

    parts = publishable_key.split("_")
    if len(parts) >= 3:
        raw = parts[2]
        padding = (4 - len(raw) % 4) % 4
        padded = raw + ("=" * padding)
        try:
            decoded = base64.b64decode(padded).decode("utf-8")
            host = decoded.rstrip("$")
            return f"https://{host}"
        except Exception as e:
            raise AuthError(f"Failed to decode publishable key: {e}") from e

    raise AuthError("Invalid publishable key format")


@lru_cache
def _get_default_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    """Cached PyJWKClient instance."""
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def verify_session_token(
    token: str,
    settings: Settings,
    jwk_client: Any | None = None,
) -> dict[str, Any]:
    """Verify Clerk session JWT token against JWKS."""
    if not token or not token.strip():
        raise AuthError("Session token is required")

    issuer = settings.clerk_issuer.strip()
    if not issuer and settings.clerk_publishable_key.strip():
        issuer = derive_issuer(settings.clerk_publishable_key.strip())

    jwks_url = settings.clerk_jwks_url.strip()
    if not jwks_url and issuer:
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"

    if jwk_client is None:
        if not jwks_url:
            raise AuthError("Clerk JWKS URL or publishable key must be configured")
        jwk_client = _get_default_jwk_client(jwks_url)

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer if issuer else None,
            leeway=10,
            options={
                "require": ["exp", "iat", "sub"],
                "verify_aud": False,
            },
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError, Exception) as e:
        raise AuthError(f"Invalid or expired session: {e}") from e

    authorized_parties_str = settings.clerk_authorized_parties.strip()
    if authorized_parties_str:
        allowed = [p.strip() for p in authorized_parties_str.split(",") if p.strip()]
        if allowed:
            azp = claims.get("azp")
            if azp not in allowed:
                raise AuthError(f"Unauthorized party: {azp}")

    return claims


def get_current_user(
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_session),
) -> User:
    """FastAPI dependency to extract and verify Clerk user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = verify_session_token(token, settings)
    except AuthError as e:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from e

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid session: missing sub")

    email = claims.get("email")
    user = repo.get_or_create_user(db, clerk_user_id=sub, email=email)
    return user
