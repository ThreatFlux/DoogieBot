# backend/app/services/mcp_config_service/status.py
"""
Functionality related to checking MCP server status.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session
from docker.errors import APIError, NotFound as DockerNotFound

from app.schemas.mcp import MCPServerStatus
from .crud import get_config_by_id # Use relative import
from .docker_utils import _get_docker_client, _get_container_name # Use relative import

logger = logging.getLogger(__name__)

def get_config_status(db: Session, config_id: str) -> Optional[MCPServerStatus]:
    """ Get the status of an MCP server container. """
    db_config = get_config_by_id(db, config_id)
    if not db_config: return None

    container_id, status_str, error_message = None, "stopped", None
    try:
        docker_client = _get_docker_client()
        container_name = _get_container_name(config_id)
        try:
            containers = docker_client.containers.list(all=True, filters={"name": container_name})
            if containers:
                container = containers[0]
                container_id = container.id
                status_str = container.status
                # Normalize status
                if status_str not in ["running", "exited", "created", "stopped", "removing"]:
                    error_message = f"Unexpected container status: {container.status}"
                    status_str = "error"
                elif status_str in ["exited", "removing"]:
                     status_str = "stopped"
        except DockerNotFound: pass
        except APIError as e: status_str, error_message = "error", f"Docker API error: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting container status: {e}")
        status_str, error_message = "error", str(e)

    return MCPServerStatus(
        id=config_id, name=db_config.name, enabled=db_config.config.get("enabled", False),
        status=status_str, container_id=container_id, error_message=error_message
    )