"""
Zededa MCP tools for Orchestrator Service - Azure Deployments.
"""
from typing import Any, Optional
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json
from mock_utils import filter_mock_by_identifier
from auth import ensure_bearer_token


def register_azure_deployment_tools(mcp):
    """Register all Azure deployment-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"orchestrator", "azure_model_policy"})
    async def get_azure_module_policy_from_orchestrator(
            module_policy_id: str) -> dict[str, Any] | str:
        """Get an Azure module policy from Zededa Orchestrator Service by its ID."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("azure-deployments-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, module_policy_id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Azure module policy with ID '{module_policy_id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/azure/edgedevice/modulepolicyid/{module_policy_id}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve Azure module policy with ID: {module_policy_id}."
        return response
