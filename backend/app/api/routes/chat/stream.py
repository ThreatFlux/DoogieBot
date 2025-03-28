import logging
import json
import asyncio
import time
import traceback
from typing import Any, Dict, List, Optional # Added List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.base import get_db, SessionLocal
from app.models.user import User
from app.utils.deps import get_current_user, get_current_user_stream # Adjusted imports
from app.schemas.chat import MessageCreate # Adjusted imports
from app.services.chat import ChatService
from app.services.llm_service import LLMService
# Import specific functions from the new MCP package
from app.services.mcp_config_service import get_configs_by_user, execute_mcp_tool
from app.llm.factory import LLMFactory
from app.llm.anthropic_client import AnthropicClient
from app.llm.google_gemini_client import GoogleGeminiClient
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Background Task for Stream Completion ---
async def handle_stream_completion(state: Dict[str, Any]):
    """Handles saving messages and multi-turn logic after stream completion."""
    logger = logging.getLogger(__name__) # Re-get logger in async context
    logger.info(f"Background task started for chat {state.get('chat_id')}")
    # --- Debugging: Log received state ---
    logger.info(f"Background task state received: tool_call_occurred={state.get('tool_call_occurred')}, accumulated_tool_calls={state.get('accumulated_tool_calls')}, final_tool_calls_list={state.get('final_tool_calls_list')}")
    # --- End Debugging ---

    chat_id = state.get("chat_id")
    full_content = state.get("full_content", "")
    tool_call_occurred = state.get("tool_call_occurred", False)
    # accumulated_tool_calls = state.get("accumulated_tool_calls", {}) # No longer needed for logic
    prompt_tokens = state.get("prompt_tokens", 0)
    completion_tokens = state.get("completion_tokens", 0)
    finish_reason = state.get("finish_reason")
    first_stream_yielded_final = state.get("first_stream_yielded_final", False)
    current_model = state.get("current_model")
    current_provider = state.get("current_provider")
    start_time = state.get("start_time")
    user_id = state.get("user_id")
    context_documents = state.get("context_documents")
    temperature = state.get("temperature") # Need temperature for second call
    max_tokens = state.get("max_tokens") # Need max_tokens for second call
    system_prompt = state.get("system_prompt") # Need system_prompt for second call
    original_messages = state.get("original_messages", []) # Need original messages
    final_tool_calls_list = state.get("final_tool_calls_list", []) # <-- Get the pre-computed list

    assistant_message_saved = False
    saved_tool_calls_list = None # This will be set to final_tool_calls_list if valid
    current_messages = list(original_messages) # Start history for multi-turn

    try:
        with SessionLocal() as db: # Use a new session for the background task
            # --- Save Tool Call Message using pre-computed list ---
            if tool_call_occurred and final_tool_calls_list: # Use final_tool_calls_list from state
                # Validate the pre-computed list
                if all(call.get("id") and call.get("function", {}).get("name") for call in final_tool_calls_list):
                    logger.info(f"Attempting to save assistant message with {len(final_tool_calls_list)} tool calls (using pre-computed list)...")
                    try:
                        total_tokens_call = prompt_tokens + completion_tokens if first_stream_yielded_final else 0
                        tokens_per_second_call = completion_tokens / (time.time() - start_time) if first_stream_yielded_final and completion_tokens and (time.time() - start_time) > 0 else 0.0
                        assistant_message_db = ChatService.add_message(
                            db, chat_id, "assistant", content=full_content or "",
                            tool_calls=final_tool_calls_list, tokens=total_tokens_call, prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens, tokens_per_second=tokens_per_second_call,
                            model=current_model, provider=current_provider, finish_reason="tool_calls"
                        )
                        if assistant_message_db and assistant_message_db.id:
                            logger.info(f"Saved assistant message with tool calls (background). DB ID: {assistant_message_db.id}")
                            assistant_message_saved = True
                            current_messages.append({"role": "assistant", "content": full_content or None, "tool_calls": final_tool_calls_list})
                            saved_tool_calls_list = final_tool_calls_list # Use the validated list
                        else:
                            logger.error("Failed to save assistant message with tool calls to DB (background)!")
                    except Exception as save_err:
                         logger.exception(f"Error saving assistant message with tool calls (background): {save_err}")
                else:
                    logger.error("Assembled tool calls list failed validation (background). Not saving.")

            # --- Handle Stream End (Check new flag) ---
            elif not state.get("first_stream_completed_normally", False): # Check the new flag
                 logger.warning(f"First stream for chat {chat_id} did not complete normally (background).")
                 if full_content: # Save if content exists, even if stream didn't finish normally
                     ChatService.add_message(db, chat_id, "assistant", full_content, finish_reason=finish_reason or "incomplete", model=current_model, provider=current_provider)
                 return # Don't proceed to multi-turn

            # --- Save Simple Content Response ---
            elif full_content and not tool_call_occurred:
                logger.debug(f"Saving final simple content message for chat {chat_id} (background).")
                total_tokens_final = prompt_tokens + completion_tokens
                tokens_per_second_final = completion_tokens / (time.time() - start_time) if completion_tokens and (time.time() - start_time) > 0 else 0.0
                ChatService.add_message(
                    db, chat_id, "assistant", full_content,
                    tokens=total_tokens_final, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                    tokens_per_second=tokens_per_second_final, model=current_model, provider=current_provider,
                    context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                    finish_reason=finish_reason
                )
                assistant_message_saved = True # Mark as saved even if simple content
            elif not full_content and not tool_call_occurred:
                 logger.debug(f"No content and no tool calls generated in the first stream for chat {chat_id} (background), not saving message.")

            # --- Multi-Turn Logic: Execute Tools if Needed ---
            if tool_call_occurred and saved_tool_calls_list:
                if not assistant_message_saved:
                     logger.error("Cannot proceed with tool execution as assistant message failed to save (background).")
                     return

                logger.info(f"Proceeding with tool execution for {len(saved_tool_calls_list)} tool calls (background)...")

                # Execute Tools and Collect Results
                tool_results_messages = []
                if not user_id: # Should have been passed in state
                     logger.error("Cannot execute tools: user_id missing in state (background).")
                     return

                configs_map = {cfg.name.replace('-', '_'): cfg.id for cfg in get_configs_by_user(db, user_id)} # Use imported function
                tool_execution_tasks = []
                logger.debug(f"Preparing {len(saved_tool_calls_list)} tool execution tasks (background)...")
                for tool_call in saved_tool_calls_list:
                    tool_call_id = tool_call.get("id")
                    function_info = tool_call.get("function", {})
                    full_tool_name = function_info.get("name")
                    arguments_str = function_info.get("arguments", "{}")
                    if isinstance(arguments_str, dict): arguments_str = json.dumps(arguments_str)
                    elif not isinstance(arguments_str, str): arguments_str = "{}"

                    if not tool_call_id or not full_tool_name: continue
                    server_name_prefix = full_tool_name.split("__")[0]
                    config_id = configs_map.get(server_name_prefix)

                    if not config_id:
                        logger.error(f"Could not find MCP config matching tool name prefix: {server_name_prefix} (background)")
                        tool_result_content_str = json.dumps({"error": {"message": f"Configuration for tool '{full_tool_name}' not found."}})
                        tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                        tool_results_messages.append(tool_message_for_llm)
                        ChatService.add_message(db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                    else:
                        # Execute in thread within the async background task
                        tool_execution_tasks.append(
                            asyncio.to_thread(
                                execute_mcp_tool, # Use imported function
                                # db=db, # Let execute_mcp_tool handle session creation
                                config_id=config_id, tool_call_id=tool_call_id,
                                tool_name=full_tool_name, arguments_str=arguments_str
                            )
                        )

                if tool_execution_tasks:
                     logger.info(f"Awaiting asyncio.gather for {len(tool_execution_tasks)} tool execution tasks (background)...")
                     execution_outcomes = await asyncio.gather(*tool_execution_tasks, return_exceptions=True)
                     logger.info(f"asyncio.gather completed. Outcomes: {execution_outcomes}") # Log raw outcomes

                     # --- Map outcomes back to original tool calls ---
                     # Create a list of tool calls that actually resulted in a task being created
                     tasks_to_calls_map = [
                         tc for tc in saved_tool_calls_list
                         if configs_map.get(tc.get("function", {}).get("name", "").split("__")[0])
                     ]
                     # ---

                     for i, outcome in enumerate(execution_outcomes):
                         if i < len(tasks_to_calls_map):
                             original_call_info = tasks_to_calls_map[i]
                         else:
                             logger.error(f"Index {i} out of bounds for tasks_to_calls_map (len: {len(tasks_to_calls_map)}). Cannot map outcome. Outcome: {outcome}")
                             continue # Skip this outcome

                         tool_call_id = original_call_info["id"]
                         full_tool_name = original_call_info["function"]["name"]
                         logger.debug(f"Processing outcome for tool_call_id: {tool_call_id}, name: {full_tool_name}")

                         if isinstance(outcome, Exception):
                              logger.exception(f"Tool execution task for {full_tool_name} (ID: {tool_call_id}) resulted in an exception: {outcome}")
                              tool_result_content_str = json.dumps({"error": {"message": f"Unexpected error executing tool: {str(outcome)}"}})
                         else:
                              # Check if the outcome (which should be the dict from execute_mcp_tool) contains 'result'
                              if isinstance(outcome, dict) and "result" in outcome:
                                   tool_result_content_str = outcome["result"] # Use the result directly
                                   logger.debug(f"Tool {full_tool_name} (ID: {tool_call_id}) executed successfully. Result: {tool_result_content_str[:100]}...")
                              else:
                                   logger.error(f"Tool execution for {full_tool_name} (ID: {tool_call_id}) did not return a valid dictionary with 'result'. Outcome: {outcome}")
                                   tool_result_content_str = json.dumps({"error": {"message": "Tool execution failed to produce a valid result dictionary."}})

                         tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                         tool_results_messages.append(tool_message_for_llm)

                         # --- Add logging around saving tool message ---
                         logger.debug(f"Attempting to save tool message to DB for tool_call_id: {tool_call_id}")
                         try:
                             saved_tool_msg = ChatService.add_message(db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                             if saved_tool_msg and saved_tool_msg.id:
                                 logger.info(f"Successfully saved tool message to DB (ID: {saved_tool_msg.id}) for tool_call_id: {tool_call_id}")
                             else:
                                 logger.error(f"Failed to save tool message to DB for tool_call_id: {tool_call_id} (add_message returned None or no ID)")
                         except Exception as tool_save_err:
                             logger.exception(f"Error saving tool message to DB for tool_call_id: {tool_call_id}: {tool_save_err}")
                         # --- End logging ---

            # Start Second Streaming Call with Tool Results (Non-streaming in background)
            current_messages.extend(tool_results_messages)
            logger.info(f"Sending {len(tool_results_messages)} tool results back to LLM for chat {chat_id} (background).")

            # Need to recreate the LLM client for the second call
            # Use LLMConfigService to get the active config
            from app.services.llm_config import LLMConfigService # Add import
            llm_config = LLMConfigService.get_active_config(db) # Correct service and method
            if not llm_config:
                logger.error(f"Could not find active LLM config (background).") # Removed user_id from log
                return

            chat_client = LLMFactory.create_client( # Corrected call
                provider=llm_config.provider,
                model=llm_config.model,
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                # api_version is not a standard field in LLMConfig or needed by factory here
                user_id=user_id
            )
            
            second_generate_args = {
                "messages": current_messages, "temperature": temperature,
                "max_tokens": max_tokens, "stream": False # Non-streaming call
            }
        if isinstance(chat_client, (AnthropicClient, GoogleGeminiClient)):
             second_generate_args["system_prompt"] = system_prompt

        second_response = await chat_client.generate(**second_generate_args)
        logger.debug("Got second response (background)")

        # Process Second Response (Non-streaming)
        second_full_content = second_response.get("content", "")
        second_usage = second_response.get("usage", {})
        second_prompt_tokens = second_usage.get("prompt_tokens", 0)
        second_completion_tokens = second_usage.get("completion_tokens", 0)
        second_total_tokens = second_usage.get("total_tokens", second_prompt_tokens + second_completion_tokens)
        second_finish_reason = second_response.get("finish_reason")

        if second_full_content:
             logger.debug(f"Attempting to save final message after tool execution for chat {chat_id} (background).")
             try:
                 saved_final_msg = ChatService.add_message(
                     db, chat_id, "assistant", second_full_content,
                     tokens=second_total_tokens, prompt_tokens=second_prompt_tokens, completion_tokens=second_completion_tokens,
                     model=current_model, provider=current_provider, # Use model/provider from first call? Or second?
                     finish_reason=second_finish_reason
                 )
                 if saved_final_msg and saved_final_msg.id:
                      logger.info(f"Successfully saved final assistant message (ID: {saved_final_msg.id}) after tool execution for chat {chat_id} (background).")
                 else:
                      logger.error(f"Failed to save final assistant message after tool execution for chat {chat_id} (add_message returned None or no ID).")
             except Exception as final_save_err:
                  logger.exception(f"Error saving final assistant message after tool execution for chat {chat_id}: {final_save_err}")
        else:
            logger.warning("Second LLM call after tool execution resulted in no content (background).")

    except Exception as bg_err:
        # Add more detail to the final exception log
        logger.exception(f"Unhandled error in handle_stream_completion background task for chat {chat_id}. State: {state}. Error: {bg_err}")
        # Optionally, try to save an error message to the chat if possible
        try:
            with SessionLocal() as db_err:
                 ChatService.add_message(db_err, chat_id, "assistant", f"An internal error occurred while processing the tool results: {str(bg_err)}", finish_reason="error")
        except Exception as final_save_err:
            logger.error(f"Failed to save final error message to chat {chat_id} after background task failure: {final_save_err}")


@router.post("/{chat_id}/stream")
async def stream_from_llm(
    chat_id: str,
    message_in: MessageCreate,
    background_tasks: BackgroundTasks, # Added BackgroundTasks
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream a response from the LLM using POST, handling completion in background.
    """
    logger.debug(f"POST Stream request received for chat {chat_id}")

    chat = ChatService.get_chat(db, chat_id)
    if not chat:
        logger.error(f"Chat {chat_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Check if user owns the chat
    if chat.user_id != current_user.id:
        logger.error(f"User {current_user.id} does not own chat {chat_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    logger.debug(f"Initializing LLM service for streaming")
    # Initialize LLM service, passing user_id
    llm_service = LLMService(db, user_id=current_user.id) # <-- Pass user_id

    # Create async generator for streaming response
    async def response_generator():
        logger_inner = logging.getLogger(__name__) # Use local logger

        last_sent_time = time.time()
        keep_alive_interval = 15  # seconds
        # --- Create shared state dictionary ---
        completion_state = {} # Initialize the dictionary here
        # --- End create ---
        final_state_from_stream = None # Variable to store the final state

        try:
            logger_inner.debug(f"Starting chat stream for chat {chat_id}")

            # Send an initial message to establish the connection
            initial_chunk = {"content": "", "status": "processing", "done": False}
            yield f"data: {json.dumps(initial_chunk)}\n\n"

            # Get the chat stream from the LLM service
            try:
                # Get the stream generator and properly await it
                chat_stream_gen = llm_service.chat(
                    chat_id=chat_id,
                    user_message=message_in.content,
                    use_rag=True,
                    stream=True,
                    completion_state=completion_state # Pass state dict
                )
                # Properly await the stream generator
                chat_stream = await chat_stream_gen

                chunk_count = 0
                async for chunk in chat_stream:
                    chunk_count += 1
                    current_time = time.time()

                    # --- Capture internal final state ---
                    if chunk.get("type") == "internal_final_state":
                        logger_inner.debug(f"Captured internal_final_state chunk for chat {chat_id}")
                        final_state_from_stream = chunk.get("state") # Store the state
                        continue # Don't yield this chunk to the client
                    # --- End capture ---

                    # Yield other chunks to the client
                    yield f"data: {json.dumps(chunk)}\n\n"
                    last_sent_time = current_time # Update last sent time after yielding

                    if chunk_count % 10 == 0 or chunk.get("done", False): # Keep original logging condition
                        logger_inner.debug(f"Streaming chunk {chunk_count}: {chunk.get('content', '')[:30]}... (done: {chunk.get('done', False)})")

                    # Handle tool calls in stream (forwarding only)
                    if 'tool_calls_delta' in chunk or 'tool_calls' in chunk:
                        logger_inner.debug(f"Tool call chunk detected: {json.dumps(chunk)[:100]}...")

                    try:
                        yield f"data: {json.dumps(chunk)}\n\n"
                        last_sent_time = current_time
                    except Exception as json_error:
                        logger_inner.error(f"Error serializing chunk {chunk_count}: {str(json_error)}")
                        continue

                    # Minimal delay
                    await asyncio.sleep(0.001) # Reduced delay

                    # Keep-alive logic (simplified)
                    if current_time - last_sent_time > keep_alive_interval and not chunk.get("done", False):
                         yield ": keep-alive\n\n" # Simple SSE comment for keep-alive
                         last_sent_time = current_time

                logger_inner.debug(f"Finished streaming {chunk_count} chunks for chat {chat_id}")

                # Removed the check for completion_state["first_stream_yielded_final"]
                # The finally block below will handle yielding the internal state

            except asyncio.TimeoutError: # Catch timeout from underlying client if applicable
                logger_inner.error(f"Timeout during LLM interaction for chat {chat_id}")
                error_chunk = {"content": "The request timed out.", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                # Save error message directly here as background task won't run
                with SessionLocal() as db_bg:
                    ChatService.add_message(db_bg, chat_id, "assistant", "Error: Request timed out.", context_documents={"error": "timeout"})
            except Exception as chat_error:
                logger_inner.exception(f"Error getting chat stream for chat {chat_id}: {str(chat_error)}")
                error_chunk = {"content": f"An error occurred: {str(chat_error)}", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                # Save error message directly here as background task won't run
                with SessionLocal() as db_bg:
                    ChatService.add_message(db_bg, chat_id, "assistant", f"Error: {str(chat_error)}", context_documents={"error": str(chat_error)})

        except Exception as e:
            logger_inner.exception(f"Outer error in streaming response generator: {str(e)}\n{traceback.format_exc()}")
            error_chunk = {"content": f"An unexpected error occurred: {str(e)}", "error": True, "done": True}
            yield f"data: {json.dumps(error_chunk)}\n\n"
        finally:
            # --- Add background task after stream finishes/closes ---
            # Use the final_state_from_stream captured from the generator
            if final_state_from_stream:
                final_state_from_stream["chat_id"] = chat_id # Ensure chat_id is in state
                logger_inner.info(f"Adding background task handle_stream_completion for chat {chat_id} using final_state_from_stream: {final_state_from_stream}")
                background_tasks.add_task(handle_stream_completion, final_state_from_stream) # Pass the captured state
            else:
                logger_inner.warning(f"No final state captured from stream for chat {chat_id}, background task not added.")
            # --- End background task ---

    logger.debug(f"Returning StreamingResponse for chat {chat_id}")
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked"
        }
    )


# GET endpoint for EventSource compatibility
@router.get("/{chat_id}/stream")
async def stream_from_llm_get(
    request: Request, # Use Request object to get query params
    chat_id: str,
    background_tasks: BackgroundTasks, # Added BackgroundTasks
    # content: str, # Content will be a query parameter
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_stream), # Use stream-compatible auth
) -> StreamingResponse:
    """
    Stream a response from the LLM using GET (for EventSource).
    """
    logger.debug(f"GET Stream request received for chat {chat_id}")

    # Get content from query parameters
    content = request.query_params.get("content")
    if not content:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing 'content' query parameter")

    chat = ChatService.get_chat(db, chat_id)
    if not chat:
        logger.error(f"Chat {chat_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Check if user owns the chat
    if chat.user_id != current_user.id:
        logger.error(f"User {current_user.id} does not own chat {chat_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Save user message here as client/test relies on it
    ChatService.add_message(
        db,
        chat_id,
        "user",
        content # Use content from query param
    )

    logger.debug(f"Initializing LLM service for GET streaming") # Corrected log message
    # Initialize LLM service, passing user_id
    llm_service = LLMService(db, user_id=current_user.id) # <-- Pass user_id

    # Create async generator (same logic as POST endpoint, adapted for GET)
    async def response_generator():
        logger_inner = logging.getLogger(__name__) # Use local logger

        last_sent_time = time.time()
        keep_alive_interval = 15  # seconds
        # --- Create shared state dictionary ---
        completion_state = {} # Initialize the dictionary here
        # --- End create ---
        final_state_from_stream = None # Variable to store the final state

        try:
            logger_inner.debug(f"Starting chat stream for chat {chat_id} (GET)")

            # Send an initial message to establish the connection
            initial_chunk = {"content": "", "status": "processing", "done": False}
            yield f"data: {json.dumps(initial_chunk)}\n\n"

            # Get the chat stream from the LLM service
            try:
                # Get the stream generator and properly await it
                chat_stream_gen = llm_service.chat(
                    chat_id=chat_id,
                    user_message=content, # Use content from query param
                    use_rag=True,
                    stream=True,
                    completion_state=completion_state # Pass state dict
                )
                # Properly await the stream generator
                chat_stream = await chat_stream_gen

                chunk_count = 0
                async for chunk in chat_stream:
                    chunk_count += 1
                    current_time = time.time()

                    # --- Capture internal final state ---
                    if chunk.get("type") == "internal_final_state":
                        logger_inner.debug(f"Captured internal_final_state chunk for chat {chat_id} (GET)")
                        final_state_from_stream = chunk.get("state") # Store the state
                        continue # Don't yield this chunk to the client
                    # --- End capture ---

                    # Yield other chunks to the client
                    yield f"data: {json.dumps(chunk)}\n\n"
                    last_sent_time = current_time # Update last sent time after yielding

                    if chunk_count % 10 == 0 or chunk.get("done", False): # Keep original logging condition
                        logger_inner.debug(f"Streaming chunk {chunk_count} (GET): {chunk.get('content', '')[:30]}... (done: {chunk.get('done', False)})")

                    # Handle tool calls in stream (forwarding only)
                    if 'tool_calls_delta' in chunk or 'tool_calls' in chunk:
                        logger_inner.debug(f"Tool call chunk detected in GET stream: {json.dumps(chunk)[:100]}...")

                    try:
                        yield f"data: {json.dumps(chunk)}\n\n"
                        last_sent_time = current_time
                    except Exception as json_error:
                        logger_inner.error(f"Error serializing chunk {chunk_count} (GET): {str(json_error)}")
                        continue

                    # Minimal delay
                    await asyncio.sleep(0.001)

                    # Keep-alive logic
                    if current_time - last_sent_time > keep_alive_interval and not chunk.get("done", False):
                         yield ": keep-alive\n\n"
                         last_sent_time = current_time

                logger_inner.debug(f"Finished streaming {chunk_count} chunks for chat {chat_id} (GET)")

                # Removed the check for completion_state["first_stream_yielded_final"]
                # The finally block below will handle yielding the internal state

            except asyncio.TimeoutError:
                logger_inner.error(f"Timeout during LLM interaction for chat {chat_id} (GET)")
                error_chunk = {"content": "The request timed out.", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                # Save error message directly here
                with SessionLocal() as db_bg:
                    ChatService.add_message(db_bg, chat_id, "assistant", "Error: Request timed out.", context_documents={"error": "timeout"})
            except Exception as chat_error:
                logger_inner.exception(f"Error getting chat stream for chat {chat_id} (GET): {str(chat_error)}")
                error_chunk = {"content": f"An error occurred: {str(chat_error)}", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                # Save error message directly here
                with SessionLocal() as db_bg:
                    ChatService.add_message(db_bg, chat_id, "assistant", f"Error: {str(chat_error)}", context_documents={"error": str(chat_error)})

        except Exception as e:
            logger_inner.exception(f"Outer error in streaming response generator (GET): {str(e)}\n{traceback.format_exc()}")
            error_chunk = {"content": f"An unexpected error occurred: {str(e)}", "error": True, "done": True}
            yield f"data: {json.dumps(error_chunk)}\n\n"
        finally:
            # --- Add background task after stream finishes/closes ---
            # Use the final_state_from_stream captured from the generator
            if final_state_from_stream:
                final_state_from_stream["chat_id"] = chat_id # Ensure chat_id is in state
                logger_inner.info(f"Adding background task handle_stream_completion for chat {chat_id} (GET) using final_state_from_stream: {final_state_from_stream}")
                background_tasks.add_task(handle_stream_completion, final_state_from_stream) # Pass the captured state
            else:
                logger_inner.warning(f"No final state captured from stream for chat {chat_id} (GET), background task not added.")
            # --- End background task ---

    logger.debug(f"Returning StreamingResponse for chat {chat_id} (GET)")
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked"
        }
    )