import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session
import json
import uuid
import time # Added for timing

from app.llm.base import LLMClient
from app.llm.anthropic_client import AnthropicClient
from app.llm.google_gemini_client import GoogleGeminiClient
from app.services.chat import ChatService
from app.core.config import settings
from app.services.mcp_config_service import MCPConfigService # Import MCP service
from fastapi import HTTPException # Import for handling tool execution errors

logger = logging.getLogger(__name__)

async def stream_llm_response(
    db: Session,
    chat_client: LLMClient,
    chat_id: str,
    formatted_messages: List[Dict[str, str]], # Initial messages list
    temperature: float,
    max_tokens: Optional[int],
    context_documents: Optional[List[Dict[str, Any]]],
    system_prompt: Optional[str],
    model: Optional[str],
    provider: Optional[str],
    tools: Optional[List[Dict[str, Any]]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream response from the LLM, save messages, and handle multi-turn tool calls.
    """
    logger.debug(f"Starting streaming response for chat {chat_id}")

    # --- Initial Call State ---
    current_model = model or settings.DEFAULT_CHAT_MODEL
    current_provider = provider
    current_messages = list(formatted_messages) # Make a copy for potential multi-turn
    user_id = getattr(chat_client, 'user_id', None) # Try to get user_id if stored on client

    # --- First LLM Call ---
    try:
        logger.debug(f"Requesting initial streaming response from LLM client for chat {chat_id}")
        generate_args = {
            "messages": current_messages, "temperature": temperature,
            "max_tokens": max_tokens, "stream": True,
            "tools": tools if tools else None, "tool_choice": "auto"
        }
        if isinstance(chat_client, (AnthropicClient, GoogleGeminiClient)):
            generate_args["system_prompt"] = system_prompt

        response_stream = await chat_client.generate(**generate_args)
        logger.debug(f"Got initial response_stream generator")

        # --- Process First Stream ---
        full_content = ""
        accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}
        final_tool_calls_list: Optional[List[Dict[str, Any]]] = None
        prompt_tokens = 0
        completion_tokens = 0 # For first call
        finish_reason = None
        start_time = time.time()
        chunk_count = 0
        first_stream_yielded_final = False

        yield {"type": "start", "role": "assistant", "model": current_model}

        async for chunk in response_stream:
            chunk_count += 1
            chunk_type = chunk.get("type")
            yield chunk # Yield raw chunk

            if chunk_type == "delta":
                delta_content = chunk.get("content")
                delta_tool_calls = chunk.get("tool_calls_delta")
                if delta_content: full_content += delta_content
                if delta_tool_calls:
                    for tool_call_delta in delta_tool_calls:
                        index = tool_call_delta.get("index")
                        if index is None: continue
                        if index not in accumulated_tool_calls:
                            accumulated_tool_calls[index] = {"id": None, "type": "function", "function": {"name": None, "arguments": ""}}
                        call_part = accumulated_tool_calls[index]
                        if tool_call_delta.get("id"): call_part["id"] = tool_call_delta["id"]
                        if tool_call_delta.get("type"): call_part["type"] = tool_call_delta["type"]
                        func_delta = tool_call_delta.get("function", {})
                        if func_delta.get("name"): call_part["function"]["name"] = func_delta["name"]
                        if func_delta.get("arguments"): call_part["function"]["arguments"] += func_delta["arguments"]

            elif chunk_type == "error":
                error_message = chunk.get("error", "Unknown streaming error")
                logger.error(f"Error during stream for chat {chat_id}: {error_message}")
                ChatService.add_message(db, chat_id, "assistant", f"An error occurred: {error_message}", model=current_model, provider=current_provider, finish_reason="error")
                return

            elif chunk_type == "start":
                prompt_tokens = chunk.get("usage", {}).get("prompt_tokens", prompt_tokens)
                current_model = chunk.get("model", current_model)
                current_provider = chunk.get("provider", current_provider)

            elif chunk_type == "final" or chunk.get("done") is True:
                first_stream_yielded_final = True
                logger.debug(f"First stream final chunk received for chat {chat_id}")
                usage = chunk.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                completion_tokens = usage.get("completion_tokens", chunk_count)
                finish_reason = chunk.get("finish_reason")
                current_model = chunk.get("model", current_model)
                current_provider = chunk.get("provider", current_provider)
                if chunk.get("content"): full_content += chunk["content"]

                if chunk.get("tool_calls"): final_tool_calls_list = chunk["tool_calls"]
                elif accumulated_tool_calls:
                     final_tool_calls_list = [accumulated_tool_calls[i] for i in sorted(accumulated_tool_calls.keys())]
                     for call in final_tool_calls_list:
                         if call["function"]["arguments"] and not (call["function"]["arguments"].startswith("{") and call["function"]["arguments"].endswith("}")): call["function"]["arguments"] = "{" + call["function"]["arguments"] + "}"
                         try: json.loads(call["function"]["arguments"])
                         except json.JSONDecodeError: logger.warning(f"Could not parse final tool call arguments: {call['function']['arguments']}")
                else: final_tool_calls_list = None
                break # Exit first stream loop

            await asyncio.sleep(0)

        # --- Handle First Stream Completion ---
        if not first_stream_yielded_final:
             logger.warning(f"First stream for chat {chat_id} ended unexpectedly.")
             yield {"type": "final", "done": True, "content": full_content, "finish_reason": finish_reason or "incomplete"}
             if full_content: ChatService.add_message(db, chat_id, "assistant", full_content, finish_reason=finish_reason or "incomplete", model=current_model, provider=current_provider)
             return

        # --- Multi-Turn Logic: Execute Tools if Needed ---
        # NOTE: This streaming implementation currently handles only ONE round of tool execution.
        # If the second LLM call also returns tool_calls, they will not be executed.
        # This simplifies streaming but differs from the non-streaming multi-turn loop.
        if final_tool_calls_list:
            logger.info(f"Tool calls received ({len(final_tool_calls_list)}), executing...")
            total_tokens_first_call = prompt_tokens + completion_tokens
            tokens_per_second_first_call = completion_tokens / (time.time() - start_time) if completion_tokens and (time.time() - start_time) > 0 else 0.0

            # 1. Save Assistant Message with Tool Calls
            assistant_message_db = ChatService.add_message(
                db, chat_id, "assistant", content=full_content if full_content else None,
                tool_calls=final_tool_calls_list, tokens=total_tokens_first_call, prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens, tokens_per_second=tokens_per_second_first_call,
                model=current_model, provider=current_provider, finish_reason="tool_calls"
            )
            # Append the assistant message dict to history for the next call
            current_messages.append({
                 "role": "assistant", "content": full_content, "tool_calls": final_tool_calls_list
            })

            # 2. Execute Tools and Collect Results
            tool_results_messages = []
            if not user_id:
                 # Attempt to get user_id from the chat object if not on client
                 chat = ChatService.get_chat(db, chat_id)
                 if chat: user_id = chat.user_id

            if not user_id:
                 logger.error("Cannot execute tools: user_id is missing.")
                 yield {"type": "error", "error": "Internal configuration error: user context lost.", "done": True}
                 return # Stop generation

            configs_map = {cfg.name.replace('-', '_'): cfg.id for cfg in MCPConfigService.get_configs_by_user(db, user_id)}

            tool_execution_tasks = []
            original_tool_calls_map = {}
            for tool_call in final_tool_calls_list:
                tool_call_id = tool_call.get("id")
                function_info = tool_call.get("function", {})
                full_tool_name = function_info.get("name")
                arguments_str = function_info.get("arguments", "{}")

                if not tool_call_id or not full_tool_name: continue
                original_tool_calls_map[tool_call_id] = tool_call

                server_name_prefix = full_tool_name.split("__")[0]
                config_id = configs_map.get(server_name_prefix)

                if not config_id:
                    logger.error(f"Could not find MCP config matching tool name prefix: {server_name_prefix}")
                    tool_result_content_str = json.dumps({"error": {"message": f"Configuration for tool '{full_tool_name}' not found."}})
                    tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                    tool_results_messages.append(tool_message_for_llm)
                    ChatService.add_message(db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                else:
                    tool_execution_tasks.append(
                        asyncio.to_thread(
                            MCPConfigService.execute_mcp_tool,
                            db=db, config_id=config_id, tool_call_id=tool_call_id,
                            tool_name=full_tool_name, arguments_str=arguments_str
                        )
                    )

            if tool_execution_tasks:
                 execution_outcomes = await asyncio.gather(*tool_execution_tasks, return_exceptions=True)
                 for i, outcome in enumerate(execution_outcomes):
                     # Find the original tool call info - requires careful mapping if errors occurred
                     # This assumes the order matches or we can retrieve by ID if needed
                     # A more robust way would be to map outcomes back using tool_call_id if execute_mcp_tool returned it
                     original_call_info = final_tool_calls_list[i] # Adjust if filtering happened
                     tool_call_id = original_call_info["id"]
                     full_tool_name = original_call_info["function"]["name"]

                     if isinstance(outcome, Exception):
                          logger.exception(f"Unexpected error executing tool {full_tool_name}: {outcome}")
                          tool_result_content_str = json.dumps({"error": {"message": f"Unexpected error executing tool: {str(outcome)}"}})
                     else:
                          # outcome is the dict {"result": "json_string"}
                          tool_result_content_str = outcome.get("result", '{"error": "Tool execution failed to produce result."}')

                     tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                     tool_results_messages.append(tool_message_for_llm)
                     ChatService.add_message(db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)

            # 3. Start Second Streaming Call with Tool Results
            current_messages.extend(tool_results_messages)
            logger.info(f"Sending {len(tool_results_messages)} tool results back to LLM for chat {chat_id}.")

            second_generate_args = {
                "messages": current_messages, "temperature": temperature,
                "max_tokens": max_tokens, "stream": True
                # NO tools/tool_choice
            }
            if isinstance(chat_client, (AnthropicClient, GoogleGeminiClient)):
                 second_generate_args["system_prompt"] = system_prompt

            second_response_stream = await chat_client.generate(**second_generate_args)
            logger.debug("Got second response_stream generator")

            # --- Process Second Stream ---
            second_full_content = ""
            second_completion_tokens = 0
            second_finish_reason = None
            second_start_time = time.time()
            second_chunk_count = 0
            second_stream_yielded_final = False
            second_prompt_tokens = 0

            async for second_chunk in second_response_stream:
                second_chunk_count += 1
                yield second_chunk # Yield chunks directly

                if second_chunk.get("type") == "delta" and second_chunk.get("content"):
                    second_full_content += second_chunk["content"]
                if second_chunk.get("done") is True or second_chunk.get("type") == "final":
                    second_stream_yielded_final = True
                    second_usage = second_chunk.get("usage", {})
                    second_prompt_tokens = second_usage.get("prompt_tokens", 0)
                    second_completion_tokens = second_usage.get("completion_tokens", second_chunk_count)
                    second_total_tokens = second_usage.get("total_tokens", second_prompt_tokens + second_completion_tokens)
                    second_tokens_per_second = second_chunk.get("tokens_per_second", 0.0)
                    second_finish_reason = second_chunk.get("finish_reason")
                    if second_chunk.get("content"): second_full_content += second_chunk["content"]

                    if second_full_content:
                         logger.debug(f"Saving final message after tool execution for chat {chat_id}.")
                         ChatService.add_message(
                             db, chat_id, "assistant", second_full_content,
                             tokens=second_total_tokens, prompt_tokens=second_prompt_tokens, completion_tokens=second_completion_tokens,
                             tokens_per_second=second_tokens_per_second, model=current_model, provider=current_provider,
                             finish_reason=second_finish_reason
                         )
                    else: logger.warning("Second LLM call after tool execution resulted in no content.")
                    break

            if not second_stream_yielded_final:
                 logger.warning(f"Second stream for chat {chat_id} ended without a final 'done' chunk.")
                 yield {"type": "final", "done": True, "content": second_full_content or "[Error: Incomplete final response after tool execution]", "finish_reason": second_finish_reason or "incomplete"}
                 if second_full_content: ChatService.add_message(db, chat_id, "assistant", second_full_content, finish_reason=second_finish_reason or "incomplete", model=current_model, provider=current_provider)

            return # End the generator function after handling the second stream
            # --- End Multi-Turn Tool Execution ---

        elif full_content:
            # --- Handle Simple Content Response (No Tool Calls in First Stream) ---
            logger.debug(f"Saving final content message for chat {chat_id} (no tool calls).")
            total_tokens_final = prompt_tokens + completion_tokens
            tokens_per_second_final = completion_tokens / (time.time() - start_time) if completion_tokens and (time.time() - start_time) > 0 else 0.0
            ChatService.add_message(
                db, chat_id, "assistant", full_content,
                tokens=total_tokens_final, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                tokens_per_second=tokens_per_second_final, model=current_model, provider=current_provider,
                context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                finish_reason=finish_reason
            )
        else:
             logger.debug(f"No content or tool calls in final chunk for chat {chat_id}, not saving message.")


    # Handle outer errors (e.g., initial connection failure)
    except asyncio.TimeoutError: # Indented
        logger.error(f"Timeout occurred during initial generation call for chat {chat_id}")
        error_message = "The LLM took too long to respond initially. Please try again."
        error_chunk = {"content": error_message, "error": True, "done": True}
        yield error_chunk
        ChatService.add_message(db, chat_id, "assistant", error_message, model=current_model, provider=current_provider, context_documents=[doc["id"] for doc in context_documents] if context_documents else None, finish_reason="error")
    except Exception as e:
        logger.exception(f"Error in streaming response for chat {chat_id}: {str(e)}")
        if "context length" in str(e).lower(): error_message = "The request exceeded the model's context limit."
        elif "rate limit" in str(e).lower(): error_message = "The request was rate-limited by the AI provider."
        else: error_message = f"An unexpected error occurred: {str(e)}"
        error_chunk = {"content": error_message, "error": True, "done": True}
        yield error_chunk
        ChatService.add_message(db, chat_id, "assistant", error_message, model=current_model, provider=current_provider, context_documents=[doc["id"] for doc in context_documents] if context_documents else None, finish_reason="error")