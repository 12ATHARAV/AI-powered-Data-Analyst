import time
import uuid
import re
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from ..db.engine import session_context

# Rate limiter: tracks timestamps of requests per client key (IP or session ID)
CHAT_RATE_LIMIT = 15       # Maximum chat requests allowed
RATE_LIMIT_WINDOW = 60.0   # Window duration in seconds (1 minute)
_request_history: Dict[str, List[float]] = defaultdict(list)

def _is_rate_limited(client_key: str) -> bool:
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    # Keep only timestamps within the current window
    valid_times = [t for t in _request_history[client_key] if t > cutoff]
    if len(valid_times) >= CHAT_RATE_LIMIT:
        _request_history[client_key] = valid_times
        return True
    valid_times.append(now)
    _request_history[client_key] = valid_times
    return False

class SessionAndRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Resolve Session ID
        session_id = (
            request.headers.get("X-Session-ID")
            or request.query_params.get("session_id")
            or request.cookies.get("ada_session_id")
        )

        # For static assets or root, default to "default"
        is_api_request = request.url.path.startswith("/api")
        is_health = request.url.path.endswith("/health")

        if not session_id:
            if is_api_request and not is_health:
                session_id = f"sess_{uuid.uuid4().hex[:12]}"
            else:
                session_id = "default"

        # Sanitize session_id to prevent path injection
        clean_session_id = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id) or "default"
        token = session_context.set(clean_session_id)

        # 2. Rate Limit Expensive Agent Chat Requests
        if request.url.path.startswith("/api/chat") and request.method == "POST":
            client_ip = request.client.host if request.client else "unknown"
            rate_key = f"{client_ip}:{clean_session_id}"
            if _is_rate_limited(rate_key):
                session_context.reset(token)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded (15 queries/minute). To ensure availability for all demo visitors, please wait a moment."
                    },
                )

        try:
            response: Response = await call_next(request)
            # Propagate session header & cookie so browser preserves its isolated session
            if is_api_request and clean_session_id != "default":
                response.headers["X-Session-ID"] = clean_session_id
                response.set_cookie(
                    key="ada_session_id",
                    value=clean_session_id,
                    max_age=14400,  # 4 hours
                    httponly=False,
                    samesite="lax",
                )
            return response
        finally:
            session_context.reset(token)
