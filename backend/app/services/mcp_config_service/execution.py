# backend/app/services/mcp_config_service/execution.py
"""
Functionality for executing tool calls on MCP servers.
"""
import json
import uuid
import logging
import time
import socket
import struct # Needed for unpacking header
from typing import Dict, Any, Optional # Added Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status as fastapi_status
import docker
from docker.errors import DockerException, APIError, NotFound as DockerNotFound
# from docker.utils.socket import frames_iter_no_tty # Not used directly

# Import SessionLocal for creating sessions within the function
from app.db.base import SessionLocal
from app.schemas.mcp import MCPServerStatus # Needed for return type hint? No, execute returns dict
from .crud import get_config_by_id # Use relative import
from .status import get_config_status # Use relative import
from .docker_utils import _get_docker_client, _get_container_name # Use relative import

logger = logging.getLogger(__name__)

def _find_complete_json(buffer: bytes) -> tuple[bytes | None, bytes]:
    """
    Finds the first complete JSON object in the buffer using brace counting.
    Returns (json_object_bytes, remaining_buffer) or (None, original_buffer).
    """
    json_start = buffer.find(b'{')
    if json_start == -1:
        return None, buffer # No start found

    brace_level = 0
    in_string = False
    escaped = False
    for i in range(json_start, len(buffer)):
        char = buffer[i:i+1]

        if in_string:
            if char == b'"' and not escaped:
                in_string = False
            elif char == b'\\' and not escaped:
                escaped = True
            else:
                escaped = False
        else:
            if char == b'"':
                in_string = True
                escaped = False
            elif char == b'{':
                brace_level += 1
            elif char == b'}':
                brace_level -= 1
                if brace_level == 0:
                    # Found the end of a complete JSON object
                    json_bytes = buffer[json_start : i + 1]
                    remaining_buffer = buffer[i + 1 :]
                    return json_bytes, remaining_buffer

    return None, buffer # Incomplete JSON object in buffer

def _read_mcp_response(
    raw_socket: socket.socket,
    expected_id: str,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Helper function to read and parse a specific JSON-RPC response from a socket,
    handling Docker stream framing.
    """
    response_found = False
    buffer = b""
    read_start_time = time.time()
    response_content = None
    error_content = None

    logger.debug(f"Starting to read MCP response for ID: {expected_id} (Timeout: {timeout}s)...")
    try:
        logger.debug(f"Setting socket timeout to {timeout} seconds for MCP response read.")
        raw_socket.settimeout(timeout)

        logger.debug(f"Entering while loop for MCP response read (ID: {expected_id})...")
        while time.time() - read_start_time < timeout:
            try:
                chunk = raw_socket.recv(8192) # Read larger chunks
                if chunk:
                    logger.debug(f"Attach Read (ID: {expected_id}) RAW: {chunk!r}")
                    buffer += chunk
                    logger.debug(f"MCP response buffer updated (ID: {expected_id}): {buffer!r}")

                    # Process buffer to find complete JSON objects
                    while True:
                        # Check if buffer has at least the header size
                        if len(buffer) < 8:
                            break # Need more data for header

                        # Unpack header to get stream type and size
                        # > stands for big-endian, B for unsigned char (stream type), L for unsigned long (size)
                        try:
                            stream_type, size = struct.unpack('>BxxxL', buffer[:8])
                            logger.debug(f"Docker Header: stream_type={stream_type}, size={size}")
                        except struct.error as e:
                             logger.error(f"Error unpacking Docker header: {e}. Buffer: {buffer!r}")
                             # Discard the problematic buffer part? This is risky.
                             # For now, let's just break and hope more data fixes it.
                             buffer = b"" # Clear buffer as it's likely corrupted
                             break

                        # Check if we have the complete frame payload
                        if len(buffer) < 8 + size:
                            logger.debug(f"Incomplete frame payload. Have {len(buffer)-8}, need {size}. Waiting for more data.")
                            break # Need more data for the payload

                        # Extract the payload (JSON)
                        payload = buffer[8 : 8 + size]
                        logger.debug(f"Extracted payload: {payload!r}")

                        # Consume the frame (header + payload) from the buffer
                        buffer = buffer[8 + size :]
                        logger.debug(f"Buffer after consuming frame: {buffer!r}")

                        # Only process stdout (stream_type 1)
                        if stream_type == 1:
                            try:
                                rpc_response = json.loads(payload.decode('utf-8', errors='replace'))
                                logger.debug(f"Successfully parsed payload JSON (ID: {expected_id}): {rpc_response}")

                                if isinstance(rpc_response, dict) and rpc_response.get("id") == expected_id:
                                    logger.info(f"MATCH! Received target MCP response (ID: {expected_id}): {rpc_response}")
                                    if "result" in rpc_response: response_content = {"result": rpc_response["result"]}
                                    elif "error" in rpc_response: error_content = {"error": rpc_response["error"]}
                                    else:
                                        logger.error(f"Invalid JSON-RPC response (missing result/error) (ID: {expected_id})")
                                        error_content = {"error": {"code": -32603, "message": "Invalid JSON-RPC response (missing result/error)"}}
                                    response_found = True
                                    break # Found the target response, break inner while
                                else:
                                     logger.warning(f"Received JSON, but not the target MCP response ID (Expected: {expected_id}, Got: {rpc_response.get('id')}). JSON: {rpc_response}")
                                     # Continue processing buffer in case target is later

                            except json.JSONDecodeError as json_err:
                                logger.warning(f"JSONDecodeError parsing payload: {json_err}. Payload: {payload!r}")
                                # Continue processing buffer, maybe it wasn't JSON
                            except Exception as parse_err:
                                 logger.error(f"Unexpected error parsing payload JSON (ID: {expected_id}): {parse_err}")
                                 # Continue processing buffer
                        elif stream_type == 2: # Stderr
                             logger.warning(f"MCP Stderr (ID: {expected_id}): {payload.decode('utf-8', errors='replace')}")
                             # Store stderr? For now, just log it.
                        else: # Stdin or other?
                             logger.warning(f"Received unexpected stream type {stream_type} from Docker attach.")

                    # End of inner while loop (processing buffer)
                    if response_found:
                        break # Break outer while loop if target found

                else:
                    logger.warning(f"Attach Read (ID: {expected_id}): Socket recv returned empty, connection likely closed.")
                    break # Break outer while loop

            except BlockingIOError:
                time.sleep(0.05)
            except socket.timeout:
                logger.warning(f"Socket timeout occurred during recv() for MCP response (ID: {expected_id}).")
                break # Break outer while loop on timeout
            except OSError as sock_err:
                logger.error(f"Attach Read (ID: {expected_id}): Socket error during recv: {sock_err}")
                raise # Re-raise critical socket errors

            if response_found:
                break # Break outer while loop if target found

        # --- After the outer while loop finishes ---
        if not response_found:
             # Check remaining buffer just in case (though less likely with framing)
             logger.warning(f"Target response (ID: {expected_id}) not found within timeout. Checking remaining buffer: {buffer!r}")
             # Simple check for the ID in the remaining buffer as a last resort
             if expected_id.encode() in buffer:
                 logger.error(f"Found expected ID '{expected_id}' in final buffer, but couldn't parse full JSON.")
                 error_content = {"error": {"code": -32000, "message": f"Incomplete/unparsable response containing expected ID {expected_id}"}}
             else:
                 logger.error(f"Failed to find MCP response (ID: {expected_id}) after loop.")
                 raise TimeoutError(f"Did not receive MCP response (ID: {expected_id}) within timeout.")

    except (TimeoutError, socket.timeout) as timeout_err:
         logger.error(f"Timeout ({type(timeout_err).__name__}) caught waiting for MCP response (ID: {expected_id}).")
         # Ensure error_content is set if not already
         if not error_content:
             error_content = {"error": {"code": -32000, "message": f"Timeout waiting for MCP response (ID: {expected_id})"}}
    except Exception as read_err:
         logger.exception(f"Exception caught reading MCP response stream (ID: {expected_id}): {read_err}")
         if not error_content:
             error_content = {"error": {"code": -32000, "message": f"Error reading MCP response stream (ID: {expected_id}): {read_err}"}}

    if response_content:
        return response_content
    elif error_content:
        return error_content
    else:
        # This path should be less likely now
        logger.error(f"MCP response reading resulted in neither success nor error content for {expected_id}")
        return {"error": {"code": -32000, "message": f"MCP response reading failed with no specific result or error (ID: {expected_id})."}}


def _execute_mcp_tool_call_via_docker_attach(
    db: Session, # Keep db here, it's needed by get_config_status called within execute_mcp_tool
    config_id: str,
    container_id: str,
    container_name: str,
    tool_call_id: str, # ID for the tools/call request
    rpc_tool_call_request: Dict[str, Any],
    rpc_initialize_request: Dict[str, Any] # Added initialize request
) -> Dict[str, Any]:
    """
    Internal helper to execute tool call via docker attach.
    Performs the MCP initialize handshake before sending the tools/call request.
    """
    tool_result_content = None
    tool_error_content = None
    socket_conn = None
    raw_socket = None

    try:
        docker_client = _get_docker_client()
        api_client = docker_client.api

        # Attach to the container's stdio using low-level API
        socket_conn = api_client.attach_socket(container_id, params={'stdin': 1, 'stdout': 1, 'stderr': 1, 'stream': 1})
        logger.debug(f"Attached socket to container {container_name} using low-level API")

        # Access underlying socket for timeout and operations
        if hasattr(socket_conn, '_sock'):
            raw_socket = socket_conn._sock
        elif hasattr(socket_conn, '_socket'):
             raw_socket = socket_conn._socket

        if not raw_socket:
            logger.error("Failed to get underlying socket for attach. Cannot proceed.")
            raise DockerException("Failed to get underlying socket from Docker attach")

        raw_socket.settimeout(30) # Set a base timeout

        # --- Send Initialize Request ---
        init_id = rpc_initialize_request["id"]
        logger.info(f"Sending initialize request to attached stdin (ID: {init_id}): {rpc_initialize_request}")
        raw_socket.sendall((json.dumps(rpc_initialize_request) + '\n').encode('utf-8'))

        # --- Read Initialize Response ---
        init_response = _read_mcp_response(raw_socket, init_id, timeout=60) # Use helper, increased timeout to 60s for init

        if "error" in init_response:
            logger.error(f"MCP Initialize failed (ID: {init_id}): {init_response['error']}")
            return init_response # Return the error from initialize
        elif "result" not in init_response:
            logger.error(f"Invalid MCP Initialize response (missing result) (ID: {init_id}): {init_response}")
            return {"error": {"code": -32603, "message": "Invalid MCP Initialize response (missing result)"}}
        else:
             logger.info(f"MCP Initialize successful (ID: {init_id}). Result: {init_response['result']}")
             # Proceed to tool call

        # --- Send Tool Call Request ---
        logger.info(f"Sending tools/call request to attached stdin (ID: {tool_call_id}): {rpc_tool_call_request}")
        raw_socket.sendall((json.dumps(rpc_tool_call_request) + '\n').encode('utf-8'))

        # --- Read Tool Call Response ---
        tool_response = _read_mcp_response(raw_socket, tool_call_id, timeout=60) # Use helper, 60s timeout for tool call

        if "result" in tool_response:
            tool_result_content = tool_response
        elif "error" in tool_response:
            tool_error_content = tool_response
        else:
            # Should be caught by _read_mcp_response, but as a fallback
            logger.error(f"Tool call response reading returned unexpected structure (ID: {tool_call_id}): {tool_response}")
            tool_error_content = {"error": {"code": -32000, "message": "Tool execution failed with unexpected internal structure."}}

    # --- Exception handling for attach/docker client ---
    except DockerNotFound:
         logger.error(f"Container {container_name} (ID: {container_id}) not found during tool execution.")
         tool_error_content = {"error": {"code": -32000, "message": "MCP server container not found."}}
    except APIError as e:
         logger.error(f"Docker API error during tool execution: {e}")
         tool_error_content = {"error": {"code": -32000, "message": f"Docker API error: {e}"}}
    except DockerException as e: # Catch broader Docker exceptions
         logger.error(f"Docker error during tool execution: {e}")
         tool_error_content = {"error": {"code": -32000, "message": f"Docker error: {e}"}}
    except (TimeoutError, socket.timeout) as timeout_err: # Catch timeouts from _read_mcp_response
         logger.error(f"Timeout ({type(timeout_err).__name__}) caught waiting for MCP response from {container_name}.")
         # Error content is already set by _read_mcp_response in this case
         if not tool_error_content: # Set a generic one if somehow missed
             tool_error_content = {"error": {"code": -32000, "message": "Timeout during MCP communication."}}
    except Exception as e:
         logger.exception(f"Unexpected error during _execute_mcp_tool_call_via_docker_attach for call {tool_call_id}: {e}")
         if not tool_error_content: tool_error_content = {"error": {"code": -32000, "message": f"Unexpected error: {str(e)}"}}
    finally:
        # Close the raw socket if it was obtained
        if raw_socket:
            try:
                # Close write half first if possible
                if hasattr(raw_socket, 'shutdown'):
                    try: raw_socket.shutdown(socket.SHUT_WR) # Use socket.SHUT_WR
                    except OSError as sock_err: logger.warning(f"Ignoring error during attach socket shutdown SHUT_WR: {sock_err}")
                raw_socket.close()
            except Exception as close_err: logger.warning(f"Ignoring error during attach raw socket close: {close_err}")
        elif socket_conn: # Fallback for the wrapper
            try: socket_conn.close()
            except Exception as close_err: logger.warning(f"Ignoring error during attach socket_conn close: {close_err}")

    # Return result or error
    if tool_result_content:
        return tool_result_content
    elif tool_error_content:
        return tool_error_content
    else:
        # Should ideally not happen if errors/timeouts are caught properly
        logger.error(f"Tool execution resulted in neither success nor error content for {tool_call_id}")
        return {"error": {"code": -32000, "message": "Tool execution failed with no specific result or error."}}


def execute_mcp_tool(
    # db: Session, # Removed direct db dependency
    config_id: str,
    tool_call_id: str, # ID from the LLM's tool call request
    tool_name: str, # Name of the tool/function requested by LLM (prefixed)
    arguments_str: str, # Arguments for the tool (as a JSON string from LLM)
    db: Optional[Session] = None # Make db optional
) -> Dict[str, Any]: # Return type will be the tool result content (JSON stringified)
    """
    Executes a specific tool provided by a running MCP server container via docker attach.
    Performs the MCP initialize handshake first.
    Manages its own DB session if one is not provided.
    """
    logger.info(f"Executing tool '{tool_name}' via MCP server config '{config_id}' (Call ID: {tool_call_id})")

    # Use context manager for session if db is not provided
    if db is None:
        logger.debug("No DB session provided to execute_mcp_tool, creating a new one.")
        with SessionLocal() as session:
            return _execute_mcp_tool_logic(session, config_id, tool_call_id, tool_name, arguments_str)
    else:
        logger.debug("Using provided DB session in execute_mcp_tool.")
        # If db is provided (e.g., from API route), use it directly without context manager
        return _execute_mcp_tool_logic(db, config_id, tool_call_id, tool_name, arguments_str)


def _execute_mcp_tool_logic(
    db: Session, # Now always receives a valid session
    config_id: str,
    tool_call_id: str,
    tool_name: str,
    arguments_str: str
) -> Dict[str, Any]:
    """Internal logic for execute_mcp_tool, requires a valid db session."""
    # 1. Validate Config and Server Status
    db_config = get_config_by_id(db, config_id)
    if not db_config: raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="MCP configuration not found")
    if not db_config.config or not db_config.config.get('enabled', False):
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="MCP server configuration is disabled")
    status = get_config_status(db, config_id) # Pass db here
    if not status or status.status != "running" or not status.container_id: raise HTTPException(status_code=fastapi_status.HTTP_409_CONFLICT, detail=f"MCP server '{db_config.name}' is not running.")
    container_id = status.container_id
    container_name = _get_container_name(config_id) # For logging

    # 2. Parse Arguments
    try:
        arguments = json.loads(arguments_str)
        if not isinstance(arguments, dict): raise ValueError("Arguments must be a JSON object (dict)")
        logger.debug(f"Parsed arguments for tool '{tool_name}': {arguments}")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid arguments for tool call {tool_call_id}: {e}")
        return {"result": json.dumps({"error": {"code": -32602, "message": f"Invalid tool arguments: {e}"}})}

    # 3. Define MCP 'initialize' and 'tools/call' JSON-RPC Requests
    init_id = f"init-{uuid.uuid4()}" # Unique ID for initialize request
    rpc_initialize_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0",
            "clientInfo": {
                "name": "Doogie Chat Backend",
                "version": "0.1.0" # TODO: Get version dynamically?
            },
            "capabilities": {} # Add empty capabilities object
        },
        "id": init_id
    }

    mcp_tool_name = tool_name.split("__")[-1] if "__" in tool_name else tool_name
    rpc_tool_call_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": mcp_tool_name,
            "input": arguments
        },
        "id": tool_call_id # Use the ID from the LLM request for the tool call
    }

    # 4. Execute via Docker Attach (with handshake)
    try:
        execution_result = _execute_mcp_tool_call_via_docker_attach(
            db=db, # Pass the session
            config_id=config_id,
            container_id=container_id,
            container_name=container_name,
            tool_call_id=tool_call_id,
            rpc_tool_call_request=rpc_tool_call_request,
            rpc_initialize_request=rpc_initialize_request # Pass initialize request
        )

        # Wrap the result/error dict in the final {"result": json_string} structure
        if "result" in execution_result:
            result_data = execution_result["result"]
            # Ensure result is always a string for the tool message content
            result_data_str = json.dumps(result_data) if not isinstance(result_data, str) else result_data
            logger.info(f"Tool '{tool_name}' executed successfully for call {tool_call_id}.")
            return {"result": result_data_str}
        elif "error" in execution_result:
            logger.warning(f"Tool '{tool_name}' execution failed for call {tool_call_id}: {execution_result['error']}")
            return {"result": json.dumps(execution_result)} # Return the error dict as JSON string in result
        else:
             logger.error(f"Tool execution helper returned unexpected structure for {tool_call_id}: {execution_result}")
             return {"result": json.dumps({"error": {"code": -32000, "message": "Tool execution failed with unexpected internal structure."}})}

    except HTTPException as http_exc:
         # This might happen if get_config_status fails within this logic now
         logger.error(f"HTTPException during tool execution logic for {tool_call_id}: {http_exc.detail}")
         return {"result": json.dumps({"error": {"code": -32000, "message": f"Tool setup error: {http_exc.detail}"}})}
    except Exception as e:
         logger.exception(f"Unexpected error during _execute_mcp_tool_logic for call {tool_call_id}: {e}")
         return {"result": json.dumps({"error": {"code": -32000, "message": f"Unexpected error: {str(e)}"}})}