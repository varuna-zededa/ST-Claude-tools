"""
Main Zededa MCP server health endpoints.
"""

from starlette.responses import JSONResponse

HEALTH_ROUTE = "/v1/health"

def register_health_routes(mcp):
    @mcp.custom_route(HEALTH_ROUTE, methods=["GET"])
    async def health_status(request):
        """
        Health liveness endpoint
        """
        content = {"status": "healthy"}
        return JSONResponse(content)
