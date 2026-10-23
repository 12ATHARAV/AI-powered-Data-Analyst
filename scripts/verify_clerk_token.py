import json
import sys
from pathlib import Path

# Add backend to sys.path so app modules can be loaded
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.auth.clerk import AuthError, verify_session_token  # noqa: E402
from app.config import get_settings  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_clerk_token.py <token>")
        sys.exit(1)

    token = sys.argv[1].strip()
    settings = get_settings()

    print("Verifying token against Clerk configuration...")
    print(f"Publishable Key set: {bool(settings.clerk_publishable_key)}")
    print(f"Issuer: {settings.clerk_issuer or '(derived from publishable key)'}")
    print(f"JWKS URL: {settings.clerk_jwks_url or '(default .well-known/jwks.json)'}")
    print(f"Authorized Parties: {settings.clerk_authorized_parties or '(none)'}\n")

    try:
        claims = verify_session_token(token, settings)
        print("PASS: Token successfully verified!")
        print("Decoded Claims:")
        print(json.dumps(claims, indent=2, default=str))
    except AuthError as e:
        print(f"FAIL: Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
