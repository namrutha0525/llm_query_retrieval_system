import logging
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"Response: {response.status_code} - "
            f"Processed in {process_time:.3f}s"
        )

        # Add processing time to response headers
        response.headers["X-Process-Time"] = str(process_time)

        return response

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # In production, use Redis or similar

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = time.time()

        # Clean old entries
        self._clean_old_entries(current_time)

        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)}
            )

        # Record request
        self._record_request(client_ip, current_time)

        return await call_next(request)

    def _clean_old_entries(self, current_time: float):
        """Remove old request entries"""
        cutoff_time = current_time - self.window_seconds

        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req_time for req_time in self.requests[ip] 
                if req_time > cutoff_time
            ]
            if not self.requests[ip]:
                del self.requests[ip]

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited"""
        if client_ip not in self.requests:
            return False

        return len(self.requests[client_ip]) >= self.max_requests

    def _record_request(self, client_ip: str, current_time: float):
        """Record a request from client"""
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        self.requests[client_ip].append(current_time)

def setup_cors_middleware():
    """Setup CORS middleware configuration"""
    return CORSMiddleware(
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
