"""
Zededa MCP tools for user session management.
"""
from typing import Any, Optional
import urllib.parse
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json
from auth import ensure_bearer_token


def register_session_tools(mcp):
    """ Register all session-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"iam", "all_sessions", "active_users"})
    async def query_all_user_sessions() -> dict[str, Any] | str:
        """Query all active user sessions for all users."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("sessions-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if token is None:
            return "Authorization header is missing or not a Bearer token."

        url = f"{ZEDEDA_API_BASE}/api/v1/sessions"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve user sessions."
        return response

    @mcp.tool(tags={"iam", "self_session", "current_user_session_details"})
    async def get_user_session_self() -> dict[str, Any] | str:
        """Get the details of the current user session."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("sessions-self.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if token is None:
            return "Authorization header is missing or not a Bearer token."

        url = f"{ZEDEDA_API_BASE}/api/v1/sessions/self"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve current user session."
        return response

    @mcp.tool(tags={"iam", "user_session", "by_session_token"})
    async def get_user_session_by_token(
            session_token: Optional[str] = None,
            session_token_path: Optional[str] = None) -> dict[str, Any] | str:
        """Get the details of a user session with given session token."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("sessions-token.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if token is None:
            return "Authorization header is missing or not a Bearer token."

        if not session_token and not session_token_path:
            return "Either session_token or session_token_path must be provided."

        if session_token_path:
            # Use path parameter version
            url = f"{ZEDEDA_API_BASE}/api/v1/sessions/token/{urllib.parse.quote(session_token_path)}"
        else:
            # Use query parameter version
            params = {}
            if session_token:
                params["sessionToken.base64"] = session_token

            url = f"{ZEDEDA_API_BASE}/api/v1/sessions/token"
            if params:
                query_parts = []
                for key, value in params.items():
                    query_parts.append(
                        f"{key}={urllib.parse.quote(str(value))}")
                url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve user session by token."
        return response
