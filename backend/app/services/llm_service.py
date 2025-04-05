from typing import List, Dict, Any, Optional, Union, AsyncGenerator
import logging
from sqlalchemy.orm import Session
import time
import json
import asyncio
import google.generativeai as genai # Import google library

from app.llm.factory import LLMFactory
from app.llm.base import LLMClient
# Import specific clients for type checking
from app.llm.anthropic_client import AnthropicClient
from app.llm.google_gemini_client import GoogleGeminiClient
from app.services.chat import ChatService
from app.services.llm_config import LLMConfigService
from app.services.embedding_config import EmbeddingConfigService
from app.services.reranking_config import RerankingConfigService
# Import MCP config service and functions
from app.services.mcp_config_service import MCPConfigService
from app.rag.hybrid_retriever import HybridRetriever
from app.core.config import settings
# Import the extracted functions
from .llm_rag import get_rag_context
from .llm_stream import stream_llm_response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MAX_TOOL_TURNS = 5 # Maximum number of LLM <-> Tool execution cycles per user message

# --- Define KNOWN Schemas for specific MCP Servers ---
# Used for servers that don't support dynamic mcp.describe
KNOWN_MCP_TOOL_SCHEMAS = {
    "fetch": [ # Server name matches config name
        {
            "name": "fetch", # Tool name
            "description": "Fetches a URL from the internet and optionally extracts its contents as markdown.",
            "input_schema": { # Use input_schema as per MCP spec
                "type": "object",
                "properties": {
                    "url": {
                        "description": "URL to fetch",
                        "format": "uri",
                        "minLength": 1,
                        "title": "Url",
                        "type": "string"
                    },
                    "max_length": {
                        "default": 5000,
                        "description": "Maximum number of characters to return.",
                        "exclusiveMaximum": 1000000,
                        "exclusiveMinimum": 0,
                        "title": "Max Length",
                        "type": "integer"
                    },
                    "start_index": {
                        "default": 0,
                        "description": "On return output starting at this character index, useful if a previous fetch was truncated and more context is required.",
                        "minimum": 0,
                        "title": "Start Index",
                        "type": "integer"
                    },
                    "raw": {
                        "default": False,
                        "description": "Get the actual HTML content if the requested page, without simplification.",
                        "title": "Raw",
                        "type": "boolean"
                    }
                },
                "required": ["url"],
                "title": "Fetch"
            }
        }
    ]
    # Add other known schemas here if needed
}
# ---

class LLMService:
    """
    Service for interacting with LLMs. Orchestrates RAG and streaming.
    """

    def __init__(
        self,
        db: Session,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        temperature: Optional[float] = None, # Added temperature to init args (optional)
        user_id: Optional[str] = None # <-- Add user_id
    ):
        """
        Initialize the LLM service.
        """
        self.db = db
        self.user_id = user_id # <-- Store user_id

        # Get active configurations from database
        chat_config = LLMConfigService.get_active_config(db)
        embedding_config = EmbeddingConfigService.get_active_config(db)

        # Use provided values or fall back to active config or defaults
        self.provider = provider or (chat_config.chat_provider if chat_config else settings.DEFAULT_LLM_PROVIDER)
        self.model = model or (chat_config.model if chat_config else settings.DEFAULT_CHAT_MODEL)
        self.system_prompt = system_prompt or (chat_config.system_prompt if chat_config else settings.DEFAULT_SYSTEM_PROMPT)
        self.api_key = api_key or (chat_config.api_key if chat_config else None)
        self.base_url = base_url or (chat_config.base_url if chat_config else None)
        # Fetch temperature from config or use provided/default
        self.temperature = temperature if temperature is not None else (chat_config.temperature if chat_config and chat_config.temperature is not None else 0.7)

        # Embedding configuration
        self.embedding_model = embedding_model or (embedding_config.model if embedding_config else None)
        embedding_provider = embedding_config.provider if embedding_config else None
        embedding_api_key = embedding_config.api_key if embedding_config else None
        embedding_base_url = embedding_config.base_url if embedding_config else None

        # Determine correct base URLs to pass based on provider.
        chat_base_url_to_pass = None
        if self.provider == 'ollama':
            chat_base_url_to_pass = self.base_url
            logger.info(f"Using configured base_url '{chat_base_url_to_pass}' for Ollama chat client.")
        else:
            logger.info(f"Ignoring configured base_url for non-Ollama chat provider '{self.provider}'. Using default.")

        embedding_base_url_to_pass = None
        if embedding_provider == 'ollama':
            embedding_base_url_to_pass = embedding_base_url
            logger.info(f"Using configured base_url '{embedding_base_url_to_pass}' for Ollama embedding client.")
        else:
            logger.info(f"Ignoring configured base_url for non-Ollama embedding provider '{embedding_provider}'. Using default.")

        # Create LLM clients using separate configurations
        if chat_config and embedding_config:
            client_result = LLMFactory.create_separate_clients(
                chat_config={
                    'provider': self.provider,
                    'model': self.model,
                    'api_key': self.api_key,
                    'base_url': chat_base_url_to_pass,
                },
                embedding_config={
                    'provider': embedding_provider,
                    'model': self.embedding_model,
                    'api_key': embedding_api_key,
                    'base_url': embedding_base_url_to_pass,
                },
                user_id=self.user_id # Pass user_id here
            )
        else:
            client_result = LLMFactory.create_client(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                base_url=chat_base_url_to_pass,
                embedding_model=self.embedding_model,
                embedding_provider=embedding_provider,
                user_id=self.user_id # Pass user_id here
            )

        # Handle single client or separate clients
        if isinstance(client_result, tuple):
            self.chat_client, self.embedding_client = client_result
        else:
            self.chat_client = self.embedding_client = client_result

        # Log user_id immediately after client assignment
        logger.debug(f"LLMService.__init__: Assigned chat_client with user_id={getattr(self.chat_client, 'user_id', 'MISSING')}")

        # Create retriever for RAG
        self.retriever = HybridRetriever(db)


    async def chat(
        self,
        chat_id: str,
        user_message: str,
        use_rag: bool = True,
        max_tokens: Optional[int] = None,
        stream: bool = True,
        completion_state: Dict[str, Any] = None # Added state dict parameter
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Send a message to the LLM and get a response orchestrating RAG and streaming.
        If streaming updates the provided completion_state dictionary.
        """
        # Get chat history
        messages = ChatService.get_messages(self.db, chat_id)

        # Prepare system prompt
        current_system_prompt = self.system_prompt # Use the instance's system prompt
        logger.info(f"Using system prompt: {current_system_prompt[:100]}...")

        # Add RAG context if enabled
        context_documents = None
        if use_rag:
            context_documents = await get_rag_context(
                db=self.db, embedding_client=self.embedding_client,
                retriever=self.retriever, query=user_message
            )
            if context_documents:
                context_text = "\n\nHere is some relevant information that may help you answer the user's question:\n\n"
                for i, doc in enumerate(context_documents): context_text += f"[{i+1}] {doc['content']}\n\n"
                context_text += "Please use this information to help answer the user's question. If the information doesn't contain the answer just say so."
                current_system_prompt += context_text
                logger.info(f"Added RAG context to system prompt. Combined length: {len(current_system_prompt)}")

        # --- Start Tool Fetching and Formatting ---
        tools = []
        enabled_mcp_configs = [] # Keep track of configs for later execution

        if self.user_id:
            try:
                # Get all enabled MCP configs for this user
                enabled_mcp_configs = [c for c in MCPConfigService.get_configs_by_user(self.db, self.user_id) if c.config and c.config.get('enabled', False)]
                logger.info(f"Found {len(enabled_mcp_configs)} enabled MCP servers for user {self.user_id}")

                # First try to format tools using KNOWN_MCP_TOOL_SCHEMAS
                for config in enabled_mcp_configs:
                    server_name = config.name.lower() # Use lower case for matching
                    if server_name in KNOWN_MCP_TOOL_SCHEMAS:
                        known_schemas = KNOWN_MCP_TOOL_SCHEMAS[server_name]
                        logger.info(f"Using known schema for server '{config.name}'. Found {len(known_schemas)} tool(s).")
                        for tool_schema in known_schemas:
                            tool_name = tool_schema.get("name")
                            description = tool_schema.get("description")
                            input_schema = tool_schema.get("input_schema")

                            if tool_name and description and input_schema:
                                # Create a unique name combining server and tool name
                                unique_tool_name = f"{config.name.replace('-', '_')}__{tool_name}"
                                formatted_tool = {
                                    "type": "function", # Standard type for LLM tools
                                    "function": {
                                        "name": unique_tool_name,
                                        "description": description,
                                        "parameters": input_schema # Pass MCP input_schema as 'parameters'
                                    }
                                }
                                tools.append(formatted_tool)
                                logger.debug(f"Formatted tool: {unique_tool_name}")
                            else:
                                logger.warning(f"Skipping invalid known tool schema for server '{config.name}': {tool_schema}")
                    else:
                        # Process each config and collect tool information directly from servers
                        # For servers without known schemas, we use a generic approach
                        try:
                            # First check if the server is running
                            server_status = MCPConfigService.get_config_status(self.db, config.id)
                            if not server_status or server_status.status != "running":
                                logger.warning(f"MCP server {config.name} is not running, starting it...")
                                server_status = MCPConfigService.start_server(self.db, config.id)

                            if server_status and server_status.status == "running":
                                logger.info(f"MCP server {config.name} is running, collecting tools...")

                                # Here we would use MCP client to request tool definitions
                                # For now we create a simple unique prefix name for all tools from this server
                                prefix = config.name.replace('-', '_')

                                # If tool information isn't directly available now, we pass a generic parameter schema
                                # that the LLM can use and the actual validation happens when executing the tool
                                tools.append({
                                    "type": "function",
                                    "function": {
                                        "name": f"{prefix}__call_tool",
                                        "description": f"Call a tool from the {config.name} MCP server",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "tool_name": {
                                                    "type": "string",
                                                    "description": f"The name of the tool to call on the {config.name} server"
                                                },
                                                "arguments": {
                                                    "type": "object",
                                                    "description": "The arguments to pass to the tool"
                                                }
                                            },
                                            "required": ["tool_name"]
                                        }
                                    }
                                })
                            else:
                                logger.error(f"Failed to start MCP server {config.name}: {server_status.error_message if server_status else 'Unknown error'}")
                        except Exception as e:
                            logger.error(f"Error processing MCP server {config.name}: {e}")

                if tools:
                    logger.info(f"Generated {len(tools)} tool schemas from MCP servers")
            except Exception as e:
                logger.error(f"Failed to fetch or format MCP tools: {e}")
                tools = []
        else:
            logger.warning("No user_id provided, cannot fetch MCP tools.")
            tools = []
        # --- End Tool Fetching and Formatting ---

        # Explicitly log the final tools list being passed regardless of debug settings
        logger.info(f"[MCP Tool Check] Final tools list prepared for LLM: {json.dumps(tools, indent=2)}")

        # Format messages for the LLM including history
        formatted_messages = [self.chat_client.format_chat_message("system", current_system_prompt)]
        for msg in messages:
            # Format message based on role and add tool data if present
            if msg.role == "tool" and msg.tool_call_id:
                # Format tool result message
                formatted_messages.append(self.chat_client.format_chat_message(
                    "tool",
                    msg.content,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name
                ))
            elif msg.role == "assistant" and msg.tool_calls:
                # Format assistant message with tool calls
                formatted_messages.append(self.chat_client.format_chat_message(
                    "assistant",
                    msg.content,
                    tool_calls=msg.tool_calls
                ))
            else:
                # Regular message formatting
                formatted_messages.append(self.chat_client.format_chat_message(msg.role, msg.content))
        # Remove duplicate append; user message is now saved by API route and fetched by get_messages
        # formatted_messages.append(self.chat_client.format_chat_message("user", user_message))

        # Logging
        roles = [msg["role"] for msg in formatted_messages]
        logger.info(f"Sending {len(formatted_messages)} messages to LLM. Roles: {roles}")
        if settings.LLM_DEBUG_LOGGING:
            if context_documents: logger.info(f"RAG context included: {len(context_documents)} documents")
            if tools: logger.info(f"Tools included: {json.dumps(tools, indent=2)}")
        elif context_documents: logger.info(f"RAG context included: {len(context_documents)} documents")
        elif tools: logger.info(f"Tools included: {len(tools)} tools")

        # Generate response
        if stream:
            # Log the user_id attribute of the client being passed
            logger.debug(f"LLMService.chat: Passing chat_client with user_id={getattr(self.chat_client, 'user_id', 'MISSING')}")
            # Return awaitable generator to be awaited by the caller
            stream_generator = stream_llm_response(
                db=self.db,
                chat_client=self.chat_client,
                chat_id=chat_id,
                formatted_messages=formatted_messages,
                temperature=self.temperature,
                max_tokens=max_tokens,
                context_documents=context_documents,
                system_prompt=current_system_prompt,
                model=self.model,
                provider=self.provider,
                tools=tools # <-- Pass tools to the streaming function
            )
            return stream_generator # Return the awaitable generator directly
        else:
            # --- Non-Streaming Multi-Turn Logic ---
            current_response = None
            # Make a copy of messages to modify within the loop
            current_formatted_messages = list(formatted_messages)
            # Keep track of enabled configs for tool execution mapping
            configs_map = {cfg.name.replace('-', '_'): cfg.id for cfg in enabled_mcp_configs}

            for turn in range(MAX_TOOL_TURNS):
                logger.info(f"Non-Streaming Tool Turn {turn + 1}/{MAX_TOOL_TURNS}")
                start_time = time.time()
                # Only send tools/tool_choice on the first turn
                send_tools = tools if turn == 0 else None
                tool_choice_this_turn = "auto" if turn == 0 else None

                try:
                    current_response = await self.chat_client.generate(
                        current_formatted_messages, # Use the potentially updated message list
                        temperature=self.temperature, max_tokens=max_tokens,
                        stream=False, tools=send_tools, tool_choice=tool_choice_this_turn
                    )
                except Exception as llm_error:
                    logger.exception(f"LLM generation failed on turn {turn + 1}: {llm_error}")
                    error_content = f"An error occurred while communicating with the AI model: {str(llm_error)}"
                    # Save error message before returning
                    ChatService.add_message(self.db, chat_id, "assistant", error_content, finish_reason="error", model=self.model, provider=self.provider)
                    return {"content": error_content, "finish_reason": "error"}

                end_time = time.time()
                duration = end_time - start_time

                tool_calls = current_response.get("tool_calls")
                content = current_response.get("content")
                usage = current_response.get("usage", {})
                completion_tokens = usage.get("completion_tokens", len(content.split()) if content else (len(json.dumps(tool_calls)) // 4 if tool_calls else 0))
                prompt_tokens = usage.get("prompt_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                tokens_per_second = completion_tokens / duration if completion_tokens and duration > 0 else 0.0
                finish_reason = current_response.get("finish_reason")
                response_model = current_response.get("model", self.model)
                response_provider = current_response.get("provider", self.provider)

                # Add tokens_per_second for consistency even if not used later
                if "tokens_per_second" not in current_response: current_response["tokens_per_second"] = tokens_per_second

                if tool_calls:
                    logger.info(f"Received tool_calls response: {tool_calls}")
                    # 1. Save Assistant Message with Tool Calls
                    assistant_message_db = ChatService.add_message(
                         self.db, chat_id, "assistant", content=content, # Save potential preceding content
                         tool_calls=tool_calls, tokens=total_tokens, prompt_tokens=prompt_tokens,
                         completion_tokens=completion_tokens, tokens_per_second=tokens_per_second,
                         model=response_model, provider=response_provider,
                         finish_reason="tool_calls"
                    )
                    # Append assistant message dict to history
                    current_formatted_messages.append(self.chat_client.format_chat_message("assistant", content, tool_calls=tool_calls))

                    # 2. Execute Tools and Collect Results
                    tool_results_messages = []
                    if not self.user_id: # Should have been checked earlier but double-check
                         logger.error("Cannot execute tools: user_id missing.")
                         # Return the assistant message asking for tools as we can't proceed
                         return current_response

                    tool_execution_tasks = []
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.get("id")
                        function_info = tool_call.get("function", {})
                        full_tool_name = function_info.get("name")
                        arguments_str = function_info.get("arguments", "{}")

                        if not tool_call_id or not full_tool_name:
                            continue

                        # Handle special case for the generic call_tool function
                        if full_tool_name.endswith("__call_tool"):
                            try:
                                # Parse arguments to extract the real tool name and arguments
                                args = json.loads(arguments_str)
                                real_tool_name = args.get("tool_name")
                                tool_args = args.get("arguments", {})

                                if real_tool_name:
                                    # Create correct format for the MCP execution
                                    server_name_prefix = full_tool_name.split("__")[0]
                                    config_id = configs_map.get(server_name_prefix)

                                    if config_id:
                                        actual_tool_name = f"{server_name_prefix}__{real_tool_name}"
                                        logger.info(f"Processing call_tool request: {actual_tool_name} with args: {tool_args}")

                                        # Execute the actual tool
                                        tool_execution_tasks.append(
                                            asyncio.to_thread(
                                                MCPConfigService.execute_mcp_tool,
                                                db=self.db, config_id=config_id, tool_call_id=tool_call_id,
                                                tool_name=actual_tool_name, arguments_str=json.dumps(tool_args)
                                            )
                                        )
                                    else:
                                        error_msg = f"Config for server '{server_name_prefix}' not found"
                                        logger.error(error_msg)
                                        tool_result_content_str = json.dumps({"error": {"message": error_msg}})
                                        tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                                        tool_results_messages.append(tool_message_for_llm)
                                        ChatService.add_message(self.db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                                else:
                                    error_msg = "Missing tool_name in call_tool arguments"
                                    logger.error(error_msg)
                                    tool_result_content_str = json.dumps({"error": {"message": error_msg}})
                                    tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                                    tool_results_messages.append(tool_message_for_llm)
                                    ChatService.add_message(self.db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                            except json.JSONDecodeError as e:
                                error_msg = f"Invalid JSON in call_tool arguments: {e}"
                                logger.error(error_msg)
                                tool_result_content_str = json.dumps({"error": {"message": error_msg}})
                                tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                                tool_results_messages.append(tool_message_for_llm)
                                ChatService.add_message(self.db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                        else:
                            # Handle direct tool calls (when specific tools are exposed)
                            server_name_prefix = full_tool_name.split("__")[0]
                            config_id = configs_map.get(server_name_prefix)
                            if not config_id:
                                logger.error(f"Could not find MCP config for tool: {server_name_prefix}")
                                tool_result_content_str = json.dumps({"error": {"message": f"Config for tool '{full_tool_name}' not found."}})
                                tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                                tool_results_messages.append(tool_message_for_llm)
                                ChatService.add_message(self.db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)
                            else:
                                tool_execution_tasks.append(
                                    asyncio.to_thread( # Run sync execute_mcp_tool in thread
                                        MCPConfigService.execute_mcp_tool,
                                        db=self.db, config_id=config_id, tool_call_id=tool_call_id,
                                        tool_name=full_tool_name, arguments_str=arguments_str
                                    )
                                )

                    if tool_execution_tasks:
                        # Execute all tool calls concurrently
                        tool_results = await asyncio.gather(*tool_execution_tasks)

                        # Process results and save them
                        for result in tool_results:
                            tool_call_id = result.get("tool_call_id")
                            tool_name = result.get("tool_name") # The name used in the LLM request
                            tool_result_content_str = result.get("content") # JSON string

                            if tool_call_id and tool_name and tool_result_content_str:
                                # Save tool result message to DB
                                ChatService.add_message(
                                    self.db, chat_id, "tool", content=tool_result_content_str,
                                    tool_call_id=tool_call_id, name=tool_name
                                )
                                # Prepare message for next LLM turn
                                tool_message_for_llm = self.chat_client.format_chat_message(
                                    "tool",
                                    tool_result_content_str,
                                    tool_call_id=tool_call_id,
                                    name=tool_name
                                )
                                tool_results_messages.append(tool_message_for_llm)
                            else:
                                logger.error(f"Incomplete tool result received: {result}")

                    # Append all tool result messages to the history for the next turn
                    current_formatted_messages.extend(tool_results_messages)
                    # Continue to the next turn
                    continue
                else:
                    # No tool calls, this is the final response for this user message
                    logger.info(f"No tool calls in response. Finish reason: {finish_reason}")
                    # Save the final assistant message
                    ChatService.add_message(
                        self.db, chat_id, "assistant", content=content,
                        tokens=total_tokens, prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens, tokens_per_second=tokens_per_second,
                        model=response_model, provider=response_provider,
                        context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                        finish_reason=finish_reason
                    )
                    # Return the final response dictionary
                    return current_response

            # If loop finishes without returning (e.g., MAX_TOOL_TURNS reached)
            logger.warning(f"Reached maximum tool turns ({MAX_TOOL_TURNS}). Returning last response.")
            # Save the last assistant message if it wasn't saved already
            if current_response and not tool_calls:
                 ChatService.add_message(
                     self.db, chat_id, "assistant", content=current_response.get("content"),
                     tokens=total_tokens, prompt_tokens=prompt_tokens,
                     completion_tokens=completion_tokens, tokens_per_second=tokens_per_second,
                     model=response_model, provider=response_provider,
                     context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                     finish_reason="length" # Indicate max turns reached
                 )
            return current_response or {"content": "Maximum tool interaction limit reached.", "finish_reason": "length"}


    async def get_available_models(self) -> tuple[List[str], List[str]]:
        """
        Get available chat and embedding models from the factory.
        """
        try:
            chat_models = await LLMFactory.get_available_chat_models()
            embedding_models = await LLMFactory.get_available_embedding_models()
            return chat_models, embedding_models
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return [], []
