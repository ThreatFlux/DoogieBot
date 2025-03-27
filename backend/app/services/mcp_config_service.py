"""
MCP (Model Context Protocol) Configuration Service.

This service handles the management of MCP server configurations, including:
1. CRUD operations for MCP server configurations
2. Docker container management for running MCP servers
3. Generating MCP configuration JSON for clients
4. Executing tool calls via MCP servers
"""

import json
import uuid
import logging
from typing import Dict, List, Optional, Any
import docker
from docker.errors import DockerException, APIError, NotFound as DockerNotFound # Alias
from docker.models.containers import Container # For type hinting

from sqlalchemy.orm import Session
# Import status with an alias
from fastapi import HTTPException, status as fastapi_status

from app.models.mcp_config import MCPServerConfig
from app.schemas.mcp import (
    MCPServerConfigCreate,
    MCPServerConfigUpdate,
    MCPServerStatus
)

# Configure logging
logger = logging.getLogger(__name__)

class MCPConfigService:
    """
    Service for managing MCP server configurations and Docker containers.

    The Model Context Protocol (MCP) is an open standard developed by Anthropic
    that provides standardized interfaces for LLM applications to connect with
    external data sources and tools.
    """

    @staticmethod
    def create_config(db: Session, config: MCPServerConfigCreate, user_id: str) -> MCPServerConfig:
        """ Create a new MCP server configuration. """
        config_id = str(uuid.uuid4())
        db_config = MCPServerConfig(
            id=config_id, name=config.name, command=config.command,
            args=config.args, env=config.env, enabled=config.enabled, user_id=user_id
        )
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        logger.info(f"Created MCP server configuration: {db_config.name} (ID: {db_config.id})")
        return db_config

    @staticmethod
    def get_config_by_id(db: Session, config_id: str) -> Optional[MCPServerConfig]:
        """ Get an MCP server configuration by ID. """
        return db.query(MCPServerConfig).filter(MCPServerConfig.id == config_id).first()

    @staticmethod
    def get_configs_by_user(db: Session, user_id: str) -> List[MCPServerConfig]:
        """ Get all MCP server configurations for a user. """
        return db.query(MCPServerConfig).filter(MCPServerConfig.user_id == user_id).all()

    @staticmethod
    def update_config(db: Session, config_id: str, config_update: MCPServerConfigUpdate) -> Optional[MCPServerConfig]:
        """ Update an MCP server configuration. """
        db_config = MCPConfigService.get_config_by_id(db, config_id)
        if not db_config: return None
        update_data = config_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_config, key, value)
        db.commit()
        db.refresh(db_config)
        logger.info(f"Updated MCP server configuration: {db_config.name} (ID: {db_config.id})")
        return db_config

    @staticmethod
    def delete_config(db: Session, config_id: str) -> bool:
        """ Delete an MCP server configuration. """
        db_config = MCPConfigService.get_config_by_id(db, config_id)
        if not db_config: return False
        try: MCPConfigService.stop_server(db, config_id)
        except Exception as e: logger.warning(f"Error stopping server during deletion: {e}")
        db.delete(db_config)
        db.commit()
        logger.info(f"Deleted MCP server configuration: {db_config.name} (ID: {db_config.id})")
        return True

    @staticmethod
    def _get_docker_client():
        """ Get a Docker client instance. """
        try:
            return docker.from_env(timeout=10)
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Docker error: {str(e)}")

    @staticmethod
    def _get_container_name(config_id: str) -> str:
        """ Generate a standardized container name. """
        return f"mcp-{config_id}"

    @staticmethod
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

    @staticmethod
    def get_config_status(db: Session, config_id: str) -> Optional[MCPServerStatus]:
        """ Get the status of an MCP server container. """
        db_config = MCPConfigService.get_config_by_id(db, config_id)
        if not db_config: return None

        container_id, status_str, error_message = None, "stopped", None
        try:
            docker_client = MCPConfigService._get_docker_client()
            container_name = MCPConfigService._get_container_name(config_id)
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
            id=config_id, name=db_config.name, enabled=db_config.enabled,
            status=status_str, container_id=container_id, error_message=error_message
        )

    @staticmethod
    def start_server(db: Session, config_id: str) -> Optional[MCPServerStatus]:
        """ Start an MCP server using Docker. """
        db_config = MCPConfigService.get_config_by_id(db, config_id)
        if not db_config or not db_config.enabled:
             return MCPServerStatus(
                id=config_id, name=db_config.name if db_config else "Unknown", enabled=False, status="stopped",
                error_message="Configuration not found or disabled" if not db_config else "Configuration disabled"
            )
        try:
            docker_client = MCPConfigService._get_docker_client()
            container_name = MCPConfigService._get_container_name(config_id)
            try:
                containers = docker_client.containers.list(all=True, filters={"name": container_name})
                if containers:
                    container = containers[0]
                    if container.status != "running":
                        try: container.start(); logger.info(f"Started existing MCP container: {container_name}")
                        except APIError as start_error: logger.error(f"Failed to start existing container {container_name}: {start_error}"); raise start_error
                else:
                    # Create a new container
                    env_vars = db_config.env or {}
                    docker_args = MCPConfigService._transform_command_to_docker(db_config.command, db_config.args)

                    # --- Start Parsing Logic ---
                    image, command_parts, run_options = None, [], []
                    options_taking_values = {'-p', '-v', '-e', '--network', '--env-file', '--add-host', '--label', '-l'}
                    boolean_flags = {'-i', '-t', '-d', '--rm', '--init', '--privileged'}
                    try: run_index = docker_args.index("run"); current_index = run_index + 1
                    except ValueError: run_index, current_index = -1, 0

                    while current_index < len(docker_args):
                        arg = docker_args[current_index]
                        if arg.startswith("-"):
                            run_options.append(arg); current_index += 1
                            takes_value = False
                            if arg in options_taking_values: takes_value = True
                            elif arg.startswith("--") and "=" not in arg and arg not in boolean_flags: takes_value = True
                            elif len(arg) == 2 and arg[1] != '-' and arg not in boolean_flags: takes_value = True
                            if takes_value and current_index < len(docker_args) and not docker_args[current_index].startswith("-"):
                                run_options.append(docker_args[current_index]); current_index += 1
                        else: image = arg; command_parts = docker_args[current_index + 1:]; break
                    if image is None: raise ValueError("Cannot parse Docker image from arguments")
                    command_to_run = command_parts if command_parts else None
                    # --- End Parsing Logic ---

                    # --- Map run_options to docker-py kwargs ---
                    run_kwargs = {}
                    i = 0
                    while i < len(run_options):
                        opt = run_options[i]
                        if opt == '-i': run_kwargs['stdin_open'] = True; i += 1
                        elif opt == '-t': run_kwargs['tty'] = True; i += 1
                        elif opt == '-d': run_kwargs['detach'] = True; i += 1
                        elif opt == '--rm': run_kwargs['auto_remove'] = True; i += 1
                        elif opt == '--init': run_kwargs['init'] = True; i += 1
                        elif opt == '--privileged': run_kwargs['privileged'] = True; i += 1
                        elif opt == '-p' and i + 1 < len(run_options):
                            ports_dict = run_kwargs.get('ports', {}); parts = run_options[i+1].split(':')
                            if len(parts) == 2: ports_dict[f'{parts[1]}/tcp'] = parts[0]
                            elif len(parts) == 3: ports_dict[f'{parts[1]}/{parts[2]}'] = parts[0]
                            run_kwargs['ports'] = ports_dict; i += 2
                        elif opt == '-v' and i + 1 < len(run_options):
                            volumes_list = run_kwargs.get('volumes', []); volumes_list.append(run_options[i+1])
                            run_kwargs['volumes'] = volumes_list; i += 2
                        elif opt == '-e' and i + 1 < len(run_options): i += 2 # Handled below
                        elif (opt == '--label' or opt == '-l') and i + 1 < len(run_options):
                             labels_dict = run_kwargs.get('labels', {})
                             if '=' in run_options[i+1]: key, value = run_options[i+1].split('=', 1); labels_dict[key] = value
                             else: labels_dict[run_options[i+1]] = ""
                             run_kwargs['labels'] = labels_dict; i += 2
                        elif opt.startswith("--network") and i + 1 < len(run_options): run_kwargs['network'] = run_options[i+1]; i += 2
                        elif opt.startswith("--network=") : run_kwargs['network'] = opt.split("=", 1)[1]; i += 1
                        else:
                             logger.warning(f"Ignoring unknown/unhandled Docker option during mapping: {opt}")
                             if i + 1 < len(run_options) and not run_options[i+1].startswith("-"):
                                 if not (opt.startswith("--") and "=" in opt):
                                     is_bool_flag = opt in boolean_flags or (opt.startswith("--") and opt not in options_taking_values and "=" not in opt)
                                     if not is_bool_flag: i += 1
                             i += 1
                    # --- End Mapping ---

                    final_env = db_config.env or {}; i = 0
                    while i < len(run_options):
                        if run_options[i] == '-e' and i + 1 < len(run_options):
                            env_item = run_options[i+1]
                            if '=' in env_item: key, value = env_item.split('=', 1); final_env[key] = value
                            i += 2
                        else: i += 1

                    run_kwargs['detach'] = True
                    # Respect auto_remove if set via --rm
                    run_kwargs['name'] = container_name

                    logger.debug(f"Running container '{container_name}' with image='{image}', command={command_to_run}, env={final_env}, kwargs={run_kwargs}")
                    container = docker_client.containers.run(image=image, command=command_to_run, environment=final_env, **run_kwargs)
                    logger.info(f"Created and started new MCP container: {container_name}")
            except APIError as e: logger.error(f"Docker API error during start/create: {e}"); raise
            return MCPConfigService.get_config_status(db, config_id)
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
            config_name = db_config.name if db_config else "Unknown"; config_enabled = db_config.enabled if db_config else False
            return MCPServerStatus(id=config_id, name=config_name, enabled=config_enabled, status="error", error_message=str(e))

    @staticmethod
    def stop_server(db: Session, config_id: str) -> Optional[MCPServerStatus]:
        """ Stop an MCP server Docker container. """
        db_config = MCPConfigService.get_config_by_id(db, config_id)
        if not db_config: return None
        try:
            docker_client = MCPConfigService._get_docker_client()
            container_name = MCPConfigService._get_container_name(config_id)
            try:
                containers = docker_client.containers.list(all=True, filters={"name": container_name})
                if containers:
                    container = containers[0]
                    if container.status == "running":
                        try: container.stop(timeout=10); logger.info(f"Stopped MCP container: {container_name}")
                        except APIError as stop_error: logger.error(f"Failed to stop container {container_name}: {stop_error}"); raise stop_error
                    if not container.attrs.get('HostConfig', {}).get('AutoRemove', False):
                         try: container.remove(); logger.info(f"Removed stopped MCP container: {container_name}")
                         except APIError as remove_error:
                             if remove_error.response.status_code == 409 and 'removal in progress' in remove_error.explanation.lower(): logger.info(f"Container {container_name} already being removed.")
                             else: logger.error(f"Failed to remove container {container_name}: {remove_error}")
            except DockerNotFound: logger.info(f"Container {container_name} not found, nothing to stop.")
            except APIError as e: logger.error(f"Docker API error during stop: {e}"); raise
            return MCPConfigService.get_config_status(db, config_id)
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")
            return MCPServerStatus(id=config_id, name=db_config.name, enabled=db_config.enabled, status="error", error_message=str(e))

    @staticmethod
    def restart_server(db: Session, config_id: str) -> Optional[MCPServerStatus]:
        """ Restart an MCP server Docker container. """
        stop_result = MCPConfigService.stop_server(db, config_id)
        current_status = MCPConfigService.get_config_status(db, config_id)
        if current_status and current_status.status == "running":
             logger.warning(f"Server {config_id} did not stop cleanly, current status: {current_status.status}. Attempting start anyway.")
        return MCPConfigService.start_server(db, config_id)

    @staticmethod
    def execute_mcp_tool(
        db: Session,
        config_id: str,
        tool_call_id: str, # ID from the LLM's tool call request
        tool_name: str, # Name of the tool/function requested by LLM (prefixed)
        arguments_str: str # Arguments for the tool (as a JSON string from LLM)
    ) -> Dict[str, Any]: # Return type will be the tool result content (JSON stringified)
        """
        Executes a specific tool provided by a running MCP server container via docker exec.
        Assumes the MCP server reads a JSON-RPC request from stdin and writes a JSON-RPC response to stdout.
        """
        logger.info(f"Executing tool '{tool_name}' via MCP server config '{config_id}' (Call ID: {tool_call_id})")

        # 1. Validate Config and Server Status
        db_config = MCPConfigService.get_config_by_id(db, config_id)
        if not db_config: raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="MCP configuration not found")
        if not db_config.enabled: raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="MCP server configuration is disabled")
        status = MCPConfigService.get_config_status(db, config_id)
        if not status or status.status != "running" or not status.container_id: raise HTTPException(status_code=fastapi_status.HTTP_409_CONFLICT, detail=f"MCP server '{db_config.name}' is not running.")
        container_id = status.container_id
        container_name = MCPConfigService._get_container_name(config_id) # For logging

        # 2. Parse Arguments
        try:
            arguments = json.loads(arguments_str)
            if not isinstance(arguments, dict): raise ValueError("Arguments must be a JSON object (dict)")
            logger.debug(f"Parsed arguments for tool '{tool_name}': {arguments}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid arguments for tool call {tool_call_id}: {e}")
            raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail=f"Invalid tool arguments: {e}")

        # 3. Construct JSON-RPC Request
        mcp_tool_name = tool_name.split("__")[-1] if "__" in tool_name else tool_name
        rpc_request = {"jsonrpc": "2.0", "method": mcp_tool_name, "params": arguments, "id": tool_call_id}
        rpc_request_bytes = json.dumps(rpc_request).encode('utf-8') # Encode to bytes
        logger.debug(f"Constructed JSON-RPC request bytes for container {container_name}")

        # 4. Execute Command in Container using docker exec
        tool_result_content = None
        tool_error_content = None
        try:
            docker_client = MCPConfigService._get_docker_client()
            container: Container = docker_client.containers.get(container_id)

            # --- Actual docker exec logic using socket for stdio ---
            # Use exec_run with stdin=True, stream=True to interact
            # We need to write the request to stdin and read the response from stdout
            # This requires handling the socket connection provided by exec_run
            logger.debug(f"Executing in container {container_name} via socket")

            exec_id_resp = docker_client.api.exec_create(
                container.id,
                cmd='cat -', # Command to read stdin and echo to stdout (adjust if server needs different invocation)
                stdin=True,
                stdout=True,
                stderr=True, # Capture stderr as well
                tty=False
            )
            exec_id = exec_id_resp['Id']
            socket = None # Initialize socket variable

            try:
                socket = docker_client.api.exec_start(exec_id, stream=False, socket=True) # Get socket
                # socket._sock is the underlying socket object
                if hasattr(socket, '_sock') and socket._sock:
                     socket._sock.settimeout(20) # Set a reasonable timeout (e.g., 20 seconds)
                else:
                     # Handle cases where _sock might not be available (older docker-py?)
                     logger.warning("Could not access underlying socket to set timeout.")
                     # Consider alternative timeout mechanisms if needed

                # Send request
                logger.debug("Sending request to socket stdin...")
                socket.sendall(rpc_request_bytes)
                # socket.shutdown(1) # SHUT_WR - Signal that we are done writing
                # For some reason shutdown(1) causes issues with reading response on some systems/docker versions
                # Closing the write half might be handled implicitly or differently.
                # Let's try closing write half explicitly if available, otherwise rely on timeout/EOF.
                if hasattr(socket, 'close_write'):
                    socket.close_write()
                elif hasattr(socket, '_sock') and socket._sock and hasattr(socket._sock, 'shutdown'):
                     try:
                         socket._sock.shutdown(1) # Try shutting down write half of underlying socket
                     except OSError as sock_err:
                         logger.warning(f"Ignoring error during socket shutdown SHUT_WR: {sock_err}")


                # Read response
                logger.debug("Reading response from socket stdout/stderr...")
                response_bytes = b""
                while True:
                    try:
                        # Read with timeout
                        chunk = socket.recv(4096)
                        if not chunk:
                            logger.debug("Socket recv returned empty chunk, breaking read loop.")
                            break
                        response_bytes += chunk
                    except TimeoutError:
                         logger.warning(f"Timeout reading from exec socket for tool call {tool_call_id}")
                         break
                    except OSError as sock_err:
                         # Handle potential errors if socket is closed unexpectedly
                         logger.warning(f"Socket error during recv: {sock_err}")
                         break

                output_str = response_bytes.decode('utf-8', errors='replace').strip()
                logger.debug(f"Exec socket raw output: {output_str}")

                # Check exec exit code after reading output
                exec_info = docker_client.api.exec_inspect(exec_id)
                exit_code = exec_info['ExitCode']
                logger.debug(f"Exec exit code: {exit_code}")

                if exit_code != 0:
                     tool_error_content = {"error": {"code": -32603, "message": f"Tool execution failed in container with exit code {exit_code}", "data": output_str}}
                elif not output_str:
                     tool_error_content = {"error": {"code": -32603, "message": "Tool execution produced no output"}}
                else:
                     # Try parsing the output as JSON-RPC response
                     try:
                         # Find the start of the JSON object/array
                         json_start_index = -1
                         for i, char in enumerate(output_str):
                             if char == '{' or char == '[':
                                 json_start_index = i
                                 break

                         if json_start_index == -1:
                              raise json.JSONDecodeError("No JSON object/array start found", output_str, 0)

                         # Attempt to decode from the first brace/bracket
                         rpc_response = json.loads(output_str[json_start_index:])

                         if not isinstance(rpc_response, dict) or "jsonrpc" not in rpc_response or "id" not in rpc_response: raise ValueError("Invalid JSON-RPC response structure")
                         if rpc_response["id"] != tool_call_id: raise ValueError(f"JSON-RPC response ID mismatch (expected {tool_call_id}, got {rpc_response['id']})")
                         if "result" in rpc_response: tool_result_content = {"result": rpc_response["result"]}
                         elif "error" in rpc_response: tool_error_content = {"error": rpc_response["error"]}
                         else: tool_error_content = {"error": {"code": -32603, "message": "Invalid JSON-RPC response (missing result/error)"}}
                     except json.JSONDecodeError as json_err:
                         logger.error(f"Failed to parse JSON-RPC response from tool: {json_err}. Output: {output_str}")
                         tool_error_content = {"error": {"code": -32700, "message": f"Parse error: Invalid JSON received from tool ({json_err})", "data": output_str}}
                     except ValueError as ve:
                          logger.error(f"Invalid JSON-RPC response structure: {ve}. Output: {output_str}")
                          tool_error_content = {"error": {"code": -32603, "message": f"Invalid JSON-RPC response structure: {ve}", "data": output_str}}

            finally:
                 # Ensure socket is closed
                 if socket:
                     try: socket.close()
                     except Exception as close_err: logger.warning(f"Ignoring error during socket close: {close_err}")
            # --- End docker exec logic ---

        except DockerNotFound:
             logger.error(f"Container {container_name} (ID: {container_id}) not found during tool execution.")
             raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="MCP server container not found.")
        except APIError as e:
             logger.error(f"Docker API error during tool execution: {e}")
             raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Docker API error: {e}")
        except Exception as e:
             logger.exception(f"Unexpected error during tool execution for call {tool_call_id}: {e}")
             raise HTTPException(status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to execute tool: {str(e)}")

        # 5. Format Result for LLM (Return JSON string in 'result' field)
        if tool_result_content:
            logger.info(f"Tool '{tool_name}' executed successfully for call {tool_call_id}.")
            result_data = tool_result_content.get("result")
            if not isinstance(result_data, str): result_data_str = json.dumps(result_data)
            else: result_data_str = result_data
            return {"result": result_data_str}
        elif tool_error_content:
            logger.warning(f"Tool '{tool_name}' execution failed for call {tool_call_id}: {tool_error_content}")
            return {"result": json.dumps(tool_error_content)}
        else:
             logger.error(f"Tool execution resulted in neither success nor error content for {tool_call_id}")
             return {"result": json.dumps({"error": {"code": -32000, "message": "Tool execution failed with no specific result or error."}})}


    @staticmethod
    def generate_mcp_config_json(db: Session, user_id: str) -> Dict[str, Any]:
        """ Generate the MCP configuration JSON for Claude Desktop or other MCP clients. """
        configs = MCPConfigService.get_configs_by_user(db, user_id)
        mcp_servers = {}
        for config in configs:
            if config.enabled:
                server_config = {"command": config.command, "args": config.args}
                if config.env: server_config["env"] = config.env
                mcp_servers[config.name] = server_config
        return {"mcpServers": mcp_servers}
