# backend/app/services/mcp_config_service/docker_utils.py
"""
Docker utility functions for MCP Service.
"""
import logging
from typing import List
import docker
from docker.errors import DockerException
from fastapi import HTTPException, status as fastapi_status

logger = logging.getLogger(__name__)

def _get_docker_client():
    """ Get a Docker client instance. """
    try:
        # Use low-level API client for async compatibility if needed later,
        # but from_env should work for now as operations are in threads.
        return docker.from_env(timeout=10)
    except DockerException as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Docker error: {str(e)}")

def _get_container_name(config_id: str) -> str:
    """ Generate a standardized container name. """
    return f"mcp-{config_id}"

def _transform_command_to_docker(command: str, args: List[str]) -> List[str]:
    """ Transform npx/uvx commands to docker run commands if needed. """
    if command == "docker": return args
    if command == "npx" and "run" not in args:
        return ["run", "--rm", "-i", "node:latest", "npx"] + args
    if command == "uvx" and "run" not in args:
        return ["run", "--rm", "-i", "python:latest", "pip", "install", "-q", "uvx", "&&", "uvx"] + args
    if "run" not in args:
        return ["run", "--rm", "-i"] + args
    return args