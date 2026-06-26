"""
Main Zededa MCP server entry point.
"""

from faulthandler import register
import sys
import asyncio
import threading

sys.path.append('..')

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if it exists

import os
from fastmcp import FastMCP
from starlette.middleware import Middleware

from health import register_health_routes
from metrics import MetricsMiddleware, register_metrics_routes

# Import all module registration functions
from projects import register_project_tools
from datastores import register_datastore_tools
from images import register_image_tools
from edge_apps import register_edge_app_tools
from global_edge_apps import register_global_edge_app_tools
from edge_app_instances import register_edge_app_instance_tools
from edge_nodes import register_edge_node_tools
from networks import register_network_tools
from network_instances import register_network_instance_tools
from app_profiles import register_app_profile_tools
from asset_groups import register_asset_group_tools
from profile_deployments import register_profile_deployment_tools
from artifacts import register_artifact_tools
from volume_instances import register_volume_instance_tools
from authorization_profiles import register_auth_profiles_tools
from users import register_user_tools
from sessions import register_session_tools
from roles import register_roles_tools
from realms import register_realm_tools
from enterprises import register_enterprises_tools
from entitlements import register_entitlements_tools
from document_policies import register_document_policies_tools
from cluster_instances import register_cluster_instance_tools
from third_party_plugins import register_third_party_plugin_tools
from datastreams import register_datastream_tools
from azure_deployments import register_azure_deployment_tools
from api_usage_tracking import register_api_usage_tracking_tools
from edge_node_clusters import register_edge_node_cluster_tools
from brands import register_brand_tools
from sysmodels import register_hardware_model_tools
from deployment_projects import register_deployment_project_tools
from kubernetes_deployments_zks import register_kubernetes_deployment_tools
from helm_charts_zks import register_helm_chart_tools
from gitrepos_zks import register_gitrepo_tools
from private_repository_zks import register_private_repository_tools
from secrets_zks import register_secret_tools
from zks_instances import register_zks_instance_tools
from cluster_groups_zks import register_cluster_group_tools
from datetime_utils import register_datetime_tools
from utility.swagger_config import initialize_swagger_cache_sync, start_background_swagger_refresh

# Check for mock mode
USE_MOCK_API_MCP_DATA = os.getenv("USE_MOCK_API_MCP_DATA",
                                  "false").lower() == "true"
print(
    f"[DEBUG] USE_MOCK_API_MCP_DATA environment variable: {os.getenv('USE_MOCK_API_MCP_DATA')}"
)
print(f"[DEBUG] USE_MOCK_API_MCP_DATA parsed value: {USE_MOCK_API_MCP_DATA}")

# Pass mock mode to modules if needed
mcp = FastMCP("zedcloud")
mcp.USE_MOCK_API_MCP_DATA = USE_MOCK_API_MCP_DATA  # Attach to mcp instance for access in tools
print(f"[DEBUG] mcp.USE_MOCK_API_MCP_DATA set to: {mcp.USE_MOCK_API_MCP_DATA}")

register_health_routes(mcp)
register_metrics_routes(mcp)

# Register all tools by calling the registration functions
print("[DEBUG] Registering project tools...")
register_project_tools(mcp)
register_datastore_tools(mcp)
register_image_tools(mcp)
register_edge_app_tools(mcp)
register_global_edge_app_tools(mcp)
register_edge_app_instance_tools(mcp)
register_edge_node_tools(mcp)
register_network_tools(mcp)
register_network_instance_tools(mcp)
register_app_profile_tools(mcp)
register_asset_group_tools(mcp)
register_profile_deployment_tools(mcp)
register_artifact_tools(mcp)
register_volume_instance_tools(mcp)
register_auth_profiles_tools(mcp)
register_user_tools(mcp)
register_session_tools(mcp)
register_roles_tools(mcp)
register_realm_tools(mcp)
register_enterprises_tools(mcp)
register_entitlements_tools(mcp)
register_document_policies_tools(mcp)
register_cluster_instance_tools(mcp)
register_third_party_plugin_tools(mcp)
register_datastream_tools(mcp)
register_azure_deployment_tools(mcp)
register_api_usage_tracking_tools(mcp)
register_edge_node_cluster_tools(mcp)
register_brand_tools(mcp)
register_hardware_model_tools(mcp)
register_deployment_project_tools(mcp)
register_kubernetes_deployment_tools(mcp)
register_helm_chart_tools(mcp)
register_gitrepo_tools(mcp)
register_private_repository_tools(mcp)
register_secret_tools(mcp)
register_zks_instance_tools(mcp)
register_cluster_group_tools(mcp)
register_datetime_tools(mcp)

if __name__ == "__main__":
    # Print mode for visibility
    if USE_MOCK_API_MCP_DATA:
        print("[MCP] Running in MOCK DATA mode!")
    else:
        print("[MCP] Running in REAL mode.")
    
    # Load bundled swagger specs synchronously (fast, non-blocking)
    # API fetch runs as a background task after the server starts
    initialize_swagger_cache_sync()

    # Schedule background API fetch in a daemon thread so mcp.run() starts immediately
    def _background_swagger_fetch():
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(start_background_swagger_refresh())
        finally:
            loop.close()

    fetch_thread = threading.Thread(target=_background_swagger_fetch, daemon=True)
    fetch_thread.start()

    mcp.run(transport='streamable-http', host="0.0.0.0", middleware=[Middleware(MetricsMiddleware)])
