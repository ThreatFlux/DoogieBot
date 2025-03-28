import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
import json
import uuid
import time

from app.llm.base import LLMClient
from app.llm.anthropic_client import AnthropicClient
from app.llm.google_gemini_client import GoogleGeminiClient
# Removed ChatService and DB imports as saving is handled by background task
from app.core.config import settings
# Removed MCPConfigService import
from fastapi import HTTPException
# Removed SessionLocal import

logger = logging.getLogger(__name__)

async def stream_llm_response(
    chat_client: LLMClient,
    chat_id: str, # Keep for logging
    formatted_messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: Optional[int],
    context_documents: Optional[List[Dict[str, Any]]], # Context docs needed by background task
    system_prompt: Optional[str], # Needed by background task
    model: Optional[str], # Needed by background task
    provider: Optional[str], # Needed by background task
    completion_state: Dict[str, Any], # State dict to update
    user_id: Optional[str], # Pass user_id directly
    tools: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[Dict[str, Any], None]: # Return only the generator
    """
    Stream response from the LLM, updating the completion_state dictionary.
    Yields stream chunks and a final 'internal_final_state' chunk.
    """
    logger.debug(f"Starting streaming response generator for chat {chat_id}")

    current_model = model or settings.DEFAULT_CHAT_MODEL
    current_provider = provider
    # user_id is now passed directly as an argument
    # Removed local accumulated_tool_calls_dict

    # --- Initialize completion_state ---
    completion_state.update({
        "full_content": "",
        "final_tool_calls_list": [],
        "tool_call_occurred": False,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "finish_reason": None,
        "start_time": time.time(),
        "current_model": current_model,
        "current_provider": current_provider,
        "user_id": user_id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "system_prompt": system_prompt,
        "original_messages": formatted_messages,
        "context_documents": context_documents
    })
    # --- End Initialize ---

    # --- Main Generator Logic (no inner function) ---
    try:
        logger.debug(f"Requesting initial streaming response from LLM client for chat {chat_id}")
        generate_args = {
            "messages": formatted_messages, "temperature": temperature,
            "max_tokens": max_tokens, "stream": True,
            "tools": tools if tools else None, "tool_choice": "auto"
        }
        if isinstance(chat_client, (AnthropicClient, GoogleGeminiClient)):
            generate_args["system_prompt"] = system_prompt

        response_stream = await chat_client.generate(**generate_args)
        logger.debug(f"Got initial response_stream generator")

        yield {"type": "start", "role": "assistant", "model": completion_state["current_model"]}

        chunk_count = 0
        async for chunk in response_stream:
            chunk_count += 1
            chunk_type = chunk.get("type")

            # Don't yield internal state chunks
            if chunk_type == "internal_final_state":
                logger.warning("Received unexpected internal_final_state chunk type.")
                continue

            yield chunk # Yield the actual chunk to the caller

            # --- Update completion_state based on chunk ---
            if chunk_type == "delta":
                delta_content = chunk.get("content")
                delta_tool_calls = chunk.get("tool_calls_delta")
                if delta_content:
                    completion_state["full_content"] += delta_content
                if delta_tool_calls:
                    completion_state["tool_call_occurred"] = True
                    logger.debug(f"Accumulating tool calls delta: {json.dumps(delta_tool_calls)}")
                    for tool_call_delta in delta_tool_calls:
                        # Handle missing index - default to 0 for Ollama-like deltas
                        index = tool_call_delta.get("index")
                        if index is None:
                            logger.debug("Tool call delta missing index, assuming index 0.")
                            index = 0
                        # Use completion_state's accumulator with setdefault and add logging
                        accumulator = completion_state.setdefault("accumulated_tool_calls_dict", {})
                        if index not in accumulator:
                            generated_id = tool_call_delta.get("id") or f"call_{uuid.uuid4()}"
                            accumulator[index] = {"id": generated_id, "type": "function", "function": {"name": None, "arguments": ""}}
                            logger.debug(f"Initialized accumulator for index {index}: {accumulator[index]}") # Log initialization
                        call_part = accumulator[index]
                        if tool_call_delta.get("id") and call_part["id"].startswith("call_"):
                             call_part["id"] = tool_call_delta["id"]
                        if tool_call_delta.get("type"): call_part["type"] = tool_call_delta["type"]
                        func_delta = tool_call_delta.get("function", {})
                        if func_delta.get("name"): call_part["function"]["name"] = func_delta["name"]
                        # Assign arguments directly, as they seem to arrive as a dict
                        if func_delta.get("arguments"): call_part["function"]["arguments"] = func_delta["arguments"]
                        logger.debug(f"Updated accumulator for index {index}: {call_part}") # Log update

            elif chunk_type == "error": # Corrected indentation
                error_message = chunk.get("error", "Unknown streaming error")
                logger.error(f"Error during stream for chat {chat_id}: {error_message}")
                completion_state["finish_reason"] = "error" # Mark error state
                # Let the main function handle yielding the error chunk
                raise Exception(error_message) # Raise exception to exit loop and enter handler

            elif chunk_type == "start": # Corrected indentation
                completion_state["prompt_tokens"] = chunk.get("usage", {}).get("prompt_tokens", completion_state["prompt_tokens"])
                completion_state["current_model"] = chunk.get("model", completion_state["current_model"])
                completion_state["current_provider"] = chunk.get("provider", completion_state["current_provider"])

            elif chunk_type == "final" or chunk.get("done") is True: # Corrected indentation
                logger.debug(f"First stream final chunk received for chat {chat_id}")
                usage = chunk.get("usage", {})
                completion_state["prompt_tokens"] = usage.get("prompt_tokens", completion_state["prompt_tokens"])
                completion_state["completion_tokens"] = usage.get("completion_tokens", chunk_count) # Use local chunk_count
                completion_state["finish_reason"] = chunk.get("finish_reason")
                completion_state["current_model"] = chunk.get("model", completion_state["current_model"])
                completion_state["current_provider"] = chunk.get("provider", completion_state["current_provider"])
                if chunk.get("content"):
                    completion_state["full_content"] += chunk["content"]
                # Removed tool call finalization from here - it belongs in the finally block

                # Don't break here, let the stream naturally end
                pass

            await asyncio.sleep(0) # Corrected indentation
        # --- End of Stream Loop ---

        logger.debug(f"Stream generator finished normally for chat {chat_id}.")

    # --- Exception Handling ---
    except asyncio.TimeoutError:
        logger.error(f"Timeout occurred during initial generation call for chat {chat_id}")
        error_message = "The LLM took too long to respond initially. Please try again."
        completion_state["finish_reason"] = "error" # Mark error state
        yield {"content": error_message, "error": True, "done": True}
    except Exception as e:
        logger.exception(f"Core error caught in streaming response generator for chat {chat_id}:")
        generic_error_message = f"An unexpected error occurred during stream generation. Please check server logs. Error type: {type(e).__name__}"
        completion_state["finish_reason"] = "error" # Mark error state
        yield {"content": generic_error_message, "error": True, "done": True}
    # --- End Exception Handling ---
    finally:
        # --- Yield final state ---
        # Log state before assembly
        logger.debug(f"Finally block entered. accumulated_tool_calls_dict: {completion_state.get('accumulated_tool_calls_dict')}, completion_state['tool_call_occurred']: {completion_state.get('tool_call_occurred')}, completion_state['final_tool_calls_list']: {completion_state.get('final_tool_calls_list')}")

        # Ensure final tool calls list is assembled even if stream ends abruptly after tool calls started
        # Read from completion_state's accumulator
        local_accumulator = completion_state.get("accumulated_tool_calls_dict", {})
        if completion_state.get("tool_call_occurred") and not completion_state.get("final_tool_calls_list") and local_accumulator:
             try:
                 final_list = [local_accumulator[i] for i in sorted(local_accumulator.keys())]
                 completion_state["final_tool_calls_list"] = final_list
                 logger.debug(f"Finalized tool calls list in finally block: {final_list}")
             except Exception as finalize_err:
                 logger.error(f"Error finalizing tool calls list in finally block: {finalize_err}")
                 completion_state["final_tool_calls_list"] = [] # Ensure it's an empty list on error

        # If tool calls occurred, the actual finish reason is 'tool_calls'
        if completion_state["tool_call_occurred"]:
            completion_state["finish_reason"] = "tool_calls"

        # Add flag indicating normal completion of the first stream part
        completion_state["first_stream_completed_normally"] = True # Add this flag

        logger.info(f"Yielding final internal state for chat {chat_id}: {completion_state}")
        yield {"type": "internal_final_state", "state": completion_state}
        # --- End yield final state ---