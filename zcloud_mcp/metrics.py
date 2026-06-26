"""
Prometheus metrics for the Zededa MCP server.

Exposes:
  - MCP server availability gauge
  - HTTP request counters: total, 4XX, 5XX
  - HTTP request duration histogram

Note: CPU and memory are already provided by prometheus_client's built-in
process collector: process_cpu_seconds_total, process_resident_memory_bytes,
process_virtual_memory_bytes.
"""

import time
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from health import HEALTH_ROUTE

METRICS_ROUTE = "/metrics"
MCP_ROUTE = "/mcp"

# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
mcp_up = Gauge(
    "mcp_up",
    "MCP server availability: 1 = up, 0 = down",
)
mcp_up.set(1)

# ---------------------------------------------------------------------------
# HTTP metrics
# ---------------------------------------------------------------------------
mcp_http_requests_total = Counter(
    "mcp_http_requests_total",
    "Total number of HTTP requests received by the MCP server",
    ["method", "path", "status_code"],
)
mcp_http_requests_4xx_total = Counter(
    "mcp_http_requests_4xx_total",
    "Total number of HTTP 4XX responses from the MCP server",
    ["method", "path", "status_code"],
)
mcp_http_requests_5xx_total = Counter(
    "mcp_http_requests_5xx_total",
    "Total number of HTTP 5XX responses from the MCP server",
    ["method", "path", "status_code"],
)
mcp_http_request_duration_seconds = Histogram(
    "mcp_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
_EXCLUDED_PATHS = frozenset({METRICS_ROUTE, HEALTH_ROUTE})

# Only paths in this set are tracked. Requests to any other path are passed
# through without recording metrics.
# Update this set whenever a new custom route is added to the server.
_TRACKED_PATHS = frozenset({MCP_ROUTE})


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records HTTP request metrics only for known paths."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _EXCLUDED_PATHS or path not in _TRACKED_PATHS:
            return await call_next(request)

        method = request.method
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        status = str(response.status_code)

        mcp_http_requests_total.labels(method=method, path=path, status_code=status).inc()
        mcp_http_request_duration_seconds.labels(method=method, path=path).observe(duration)

        if 400 <= response.status_code < 500:
            mcp_http_requests_4xx_total.labels(method=method, path=path, status_code=status).inc()
        elif response.status_code >= 500:
            mcp_http_requests_5xx_total.labels(method=method, path=path, status_code=status).inc()

        return response

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
def register_metrics_routes(mcp) -> None:
    """Register the /metrics endpoint on the FastMCP instance."""

    @mcp.custom_route(METRICS_ROUTE, methods=["GET"])
    async def metrics_endpoint(request: Request) -> Response:
        """Expose Prometheus metrics."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
