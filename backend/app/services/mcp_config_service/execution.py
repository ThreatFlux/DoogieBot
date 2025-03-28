# backend/app/services/mcp_config_service/execution.py
"""
Functionality for executing tool calls on MCP servers.
"""
import json
import uuid
import logging
import time
import socket
from typing import Dict, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status as fastapi_status
import docker
from docker.errors import DockerException, APIError, NotFound as DockerNotFound
from docker.utils.socket import frames_iter_no_tty

from app.schemas.mcp import MCPServerStatus # Needed for return type hint? No, execute returns dict
from .crud import get_config_by_id # Use relative import
from .status import get_config_status # Use relative import
from .docker_utils import _get_docker_client, _get_container_name # Use relative import

logger = logging.getLogger(__name__)

def _execute_mcp_tool_call_via_docker_attach(
    db: Session, # Pass db session if needed by helpers
    config_id: str,
    container_id: str,
    container_name: str,
    tool_call_id: str,
    rpc_tool_call_request: Dict[str, Any],
    # rpc_initialize_request: Dict[str, Any] # No longer needed
) -> Dict[str, Any]:
    """
    Internal helper to execute tool call via docker attach.
    Sends only the tools/call request.
    """
    tool_result_content = None
    tool_error_content = None
    socket_conn = None
    raw_socket = None
    stderr_buffer = b"" # Initialize stderr_buffer here

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

        # --- Send Tool Call Request --- (Directly, skipping initialize)
        logger.info(f"Sending tools/call request directly to attached stdin: {rpc_tool_call_request}")
        raw_socket.sendall((json.dumps(rpc_tool_call_request) + '\n').encode('utf-8'))

        # --- Read Tool Call Response ---
        tool_response_found = False
        buffer = b""
        tool_read_start_time = time.time()
        tool_read_timeout = 60 # Timeout for tool response reading
        logger.debug(f"Starting to read tool call response for ID: {tool_call_id} (Timeout: {tool_read_timeout}s)...")
        try:
            # Set socket timeout specifically for this read operation
            logger.debug(f"Setting socket timeout to {tool_read_timeout} seconds for tool response read.")
            raw_socket.settimeout(tool_read_timeout)

            logger.debug("Entering while loop for tool response read...")
            while time.time() - tool_read_start_time < tool_read_timeout:
                try:
                    # Use non-blocking recv with socket timeout handling
                    chunk = raw_socket.recv(4096)
                    if chunk:
                        logger.debug(f"Attach Read (Tool) RAW: {chunk!r}")
                        # Assume stdout for now, as stderr is less likely for JSON response
                        buffer += chunk
                        logger.debug(f"Tool response buffer updated: {buffer!r}")

                        # Try to find and parse the tool response JSON using brace matching
                        while True: # Inner loop to parse multiple JSON objects if needed
                            logger.debug("Entering inner JSON parsing loop for tool response buffer (brace matching)...")
                            potential_json_bytes = None # Define here for use in except block
                            try:
                                json_start = buffer.find(b'{')
                                if json_start == -1:
                                    logger.debug("No JSON start '{' found in tool response buffer.")
                                    break # No JSON start found
                                json_end = buffer.find(b'}', json_start)
                                if json_end == -1:
                                    logger.debug("Incomplete JSON in tool response buffer (no end '}').")
                                    break # Incomplete JSON, wait for more data

                                potential_json_bytes = buffer[json_start : json_end + 1]
                                logger.debug(f"Potential tool response JSON found: {potential_json_bytes!r}")
                                rpc_response = json.loads(potential_json_bytes.decode('utf-8', errors='replace'))
                                logger.debug(f"Successfully parsed potential tool response JSON: {rpc_response}")

                                # Consume the parsed part from the buffer *immediately*
                                buffer = buffer[json_end + 1 :]
                                logger.debug(f"Buffer after consuming parsed JSON: {buffer!r}")

                                if isinstance(rpc_response, dict) and rpc_response.get("id") == tool_call_id:
                                    logger.info(f"MATCH! Received target tool call response: {rpc_response}")
                                    if "result" in rpc_response: tool_result_content = {"result": rpc_response["result"]}
                                    elif "error" in rpc_response: tool_error_content = {"error": rpc_response["error"]}
                                    else:
                                        logger.error("Invalid JSON-RPC response (missing result/error)")
                                        tool_error_content = {"error": {"code": -32603, "message": "Invalid JSON-RPC response (missing result/error)"}}
                                    tool_response_found = True
                                    break # Found the target response, break inner while
                                else:
                                     logger.warning(f"Received JSON, but not the target tool response ID (Expected: {tool_call_id}, Got: {rpc_response.get('id')}). JSON: {rpc_response}")
                                     # Continue inner loop in case target response is later in buffer

                            except json.JSONDecodeError:
                                # Simplified log message
                                logger.warning("JSONDecodeError parsing tool response buffer segment.")
                                # Assume the segment was bad, break inner loop to get more data?
                                break # Break inner while
                            except Exception as parse_err:
                                 logger.error(f"Unexpected error parsing potential JSON during tool call wait: {parse_err}")
                                 # Consume the problematic segment to avoid infinite loop
                                 if 'json_end' in locals() and json_end != -1: buffer = buffer[json_end + 1 :]
                                 else: buffer = b"" # Risky, might discard good data
                                 break # Break inner while
                        if tool_response_found:
                            break # Break outer while loop

                    else:
                        # Socket closed by remote end?
                        logger.warning("Attach Read (Tool): Socket recv returned empty, connection likely closed.")
                        break # Break outer while loop

                except BlockingIOError:
                    # No data available right now, sleep briefly before next check
                    time.sleep(0.05)
                except socket.timeout:
                    logger.warning(f"Socket timeout occurred during recv() for tool response (ID: {tool_call_id}).")
                    break # Break outer while loop on timeout
                except OSError as sock_err:
                    logger.error(f"Attach Read (Tool): Socket error during recv: {sock_err}")
                    raise # Re-raise critical socket errors

                # Break outer loop if response was found inside inner try
                if tool_response_found:
                    break

            # --- After the loop finishes (either by break, timeout, or exhaustion) ---
            if not tool_response_found:
                # Attempt one last parse of remaining buffer (might contain response without newline)
                final_line_str = buffer.strip().decode('utf-8', errors='replace')
                if final_line_str:
                    logger.debug(f"Attempting final parse of remaining buffer: {final_line_str}")
                    try:
                        rpc_response = json.loads(final_line_str)
                        if isinstance(rpc_response, dict) and rpc_response.get("id") == tool_call_id:
                            logger.info(f"MATCH! Found target tool response in final buffer parse: {rpc_response}")
                            if "result" in rpc_response: tool_result_content = {"result": rpc_response["result"]}
                            elif "error" in rpc_response: tool_error_content = {"error": rpc_response["error"]}
                            else:
                                logger.error("Invalid JSON-RPC response in final buffer (missing result/error)")
                                tool_error_content = {"error": {"code": -32603, "message": "Invalid JSON-RPC response (missing result/error)"}}
                            tool_response_found = True
                        else:
                            logger.warning(f"Parsed final buffer, but not the target tool response ID (Expected: {tool_call_id}, Got: {rpc_response.get('id')}). JSON: {rpc_response}")
                    except json.JSONDecodeError:
                        logger.warning(f"JSONDecodeError parsing final tool response buffer: {final_line_str}")
                    except Exception as parse_err:
                        logger.error(f"Error parsing final tool response buffer: {parse_err} - Buffer: {final_line_str}")

            # Final check if response was found anywhere
            if not tool_response_found:
                 logger.error(f"Failed to find tool response (ID: {tool_call_id}) after loop and final buffer check.")
                 raise TimeoutError(f"Did not receive tool call response (ID: {tool_call_id}) within timeout or before stream ended.")

        except (TimeoutError, socket.timeout) as timeout_err: # Catch both explicit TimeoutError and socket.timeout
             logger.error(f"Timeout ({type(timeout_err).__name__}) caught waiting for tool call response from {container_name}. Stderr: {stderr_buffer!r}")
             # If we timed out, check if stderr has useful info
             if stderr_buffer: tool_error_content = {"error": {"code": -32000, "message": "Timeout waiting for tool response", "data": stderr_buffer.decode(errors='replace')}}
             else: tool_error_content = {"error": {"code": -32000, "message": "Timeout waiting for tool response"}}
        except Exception as read_err: # Catch other errors like socket issues
             logger.error(f"Exception caught reading tool call response stream: {read_err}. Stderr: {stderr_buffer!r}")
             # Include stderr in the error if available
             if stderr_buffer: tool_error_content = {"error": {"code": -32000, "message": f"Error reading tool response stream: {read_err}", "data": stderr_buffer.decode(errors='replace')}}
             else: tool_error_content = {"error": {"code": -32000, "message": f"Error reading tool response stream: {read_err}"}}

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
    except Exception as e:
         logger.exception(f"Unexpected error during _execute_mcp_tool_call_via_docker_attach for call {tool_call_id}: {e}")
         if not tool_error_content: tool_error_content = {"error": {"code": -32000, "message": f"Unexpected error: {str(e)}"}}
    finally:
        # Close the raw socket if it was obtained
        if raw_socket:
            try:
                # Close write half first if possible
                if hasattr(raw_socket, 'shutdown'):
                    try: raw_socket.shutdown(1) # SHUT_WR = 1
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
        # Should ideally not happen if timeout/errors are caught properly
        logger.error(f"Tool execution resulted in neither success nor error content for {tool_call_id}")
        return {"error": {"code": -32000, "message": "Tool execution failed with no specific result or error."}}


def execute_mcp_tool(
    db: Session,
    config_id: str,
    tool_call_id: str, # ID from the LLM's tool call request
    tool_name: str, # Name of the tool/function requested by LLM (prefixed)
    arguments_str: str # Arguments for the tool (as a JSON string from LLM)
) -> Dict[str, Any]: # Return type will be the tool result content (JSON stringified)
    """
    Executes a specific tool provided by a running MCP server container via docker attach.
    Assumes the MCP server reads a JSON-RPC request from stdin and writes a JSON-RPC response to stdout.
    """
    logger.info(f"Executing tool '{tool_name}' via MCP server config '{config_id}' (Call ID: {tool_call_id})")

    # 1. Validate Config and Server Status
    db_config = get_config_by_id(db, config_id)
    if not db_config: raise HTTPException(status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="MCP configuration not found")
    if not db_config.config or not db_config.config.get('enabled', False):
        raise HTTPException(status_code=fastapi_status.HTTP_400_BAD_REQUEST, detail="MCP server configuration is disabled")
    status = get_config_status(db, config_id)
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
        # Return error in the expected format instead of raising HTTPException
        return {"result": json.dumps({"error": {"code": -32602, "message": f"Invalid tool arguments: {e}"}})}

    # 3. Define MCP 'tools/call' JSON-RPC Request (Initialize request skipped)
    mcp_tool_name = tool_name.split("__")[-1] if "__" in tool_name else tool_name
    rpc_tool_call_request = {
        "jsonrpc": "2.0",
        "method": "tools/call", # Use standard MCP method
        "params": {
            "name": mcp_tool_name, # Tool name goes here
            "input": arguments # Arguments go in the 'input' field
        },
        "id": tool_call_id
    }

    # 4. Execute via Docker Attach
    try:
        execution_result = _execute_mcp_tool_call_via_docker_attach(
            db=db,
            config_id=config_id,
            container_id=container_id,
            container_name=container_name,
            tool_call_id=tool_call_id,
            rpc_tool_call_request=rpc_tool_call_request
        )
        # The helper function now returns the dict containing either "result" or "error"
        # We need to wrap this in the final {"result": json_string} structure
        if "result" in execution_result:
            result_data = execution_result["result"]
            if not isinstance(result_data, str): result_data_str = json.dumps(result_data)
            else: result_data_str = result_data
            logger.info(f"Tool '{tool_name}' executed successfully for call {tool_call_id}.")
            return {"result": result_data_str}
        elif "error" in execution_result:
            logger.warning(f"Tool '{tool_name}' execution failed for call {tool_call_id}: {execution_result['error']}")
            return {"result": json.dumps(execution_result)} # Return the error dict as JSON string in result
        else:
             logger.error(f"Tool execution helper returned unexpected structure for {tool_call_id}: {execution_result}")
             return {"result": json.dumps({"error": {"code": -32000, "message": "Tool execution failed with unexpected internal structure."}})}

    except HTTPException as http_exc:
         # If validation failed before calling the helper
         logger.error(f"HTTPException during tool execution setup for {tool_call_id}: {http_exc.detail}")
         return {"result": json.dumps({"error": {"code": -32000, "message": f"Tool setup error: {http_exc.detail}"}})}
    except Exception as e:
         logger.exception(f"Unexpected error during execute_mcp_tool for call {tool_call_id}: {e}")
         return {"result": json.dumps({"error": {"code": -32000, "message": f"Unexpected error: {str(e)}"}})}