# backend/app/services/mcp_config_service/__init__.py
"""
MCP Configuration Service Package.

This package handles the management of MCP server configurations, including:
1. CRUD operations for MCP server configurations
2. Docker container management for running MCP servers
3. Generating MCP configuration JSON for clients
4. Executing tool calls via MCP servers
5. Describing tools provided by MCP servers
"""

# Import functions/classes from submodules to expose them at the package level
from .crud import (
    create_config,
    get_config_by_id,
    get_configs_by_user,
    update_config,
    delete_config,
    get_all_enabled_configs,
)
from .docker_utils import (
    _get_docker_client,
    _get_container_name,
    _transform_command_to_docker,
)
from .status import get_config_status
from .lifecycle import start_server, stop_server, restart_server
from .execution import execute_mcp_tool
from .config_gen import generate_mcp_config_json

# Define a facade class or simply expose functions directly
# For simplicity, let's expose functions directly for now.
# If a class structure is preferred later, we can refactor __init__.py

__all__ = [
    "create_config",
    "get_config_by_id",
    "get_configs_by_user",
    "update_config",
    "delete_config",
    "get_all_enabled_configs",
    "get_config_status",
    "start_server",
    "stop_server",
    "restart_server",
    "execute_mcp_tool",
    "generate_mcp_config_json",
]

# You could also define a class here that uses the imported functions:
# class MCPConfigService:
#     @staticmethod
#     def create_config(*args, **kwargs): return create_config(*args, **kwargs)
#     # ... etc. ...