"""
Correlation ID middleware for the iPhone Gateway.

Assigns a unique X-Request-ID to every incoming request, stores it in
``request.state.request_id``, and echoes it back as a response header.
All unhandled errors should read that ID from request.state so that log
lines and error envelopes share the same correlation token.
"""
from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Per-request correlation ID middleware.

    Behaviour:
    - Accepts an incoming ``X-Request-ID`` header and reuses it (allows clients
      to supply their own trace token for end-to-end correlation).
    - If no header is present, generates a new ``uuid4`` string.
    - Stores the ID in ``request.state.request_id`` so handlers and exception
      handlers can reference it without thread-local hacks.
    - Injects ``X-Request-ID`` into every response regardless of status code.
    - Logs ``<METHOD> <path> → <status> [request_id]`` at INFO level.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # Honour a client-supplied ID; fall back to a fresh uuid4
        request_id: str = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s → %d [%s]",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response
