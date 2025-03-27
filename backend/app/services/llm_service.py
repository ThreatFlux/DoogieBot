# backend/app/services/llm_service.py
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
from app.services.mcp_config_service import MCPConfigService # <-- Import MCP Service
from app.rag.hybrid_retriever import HybridRetriever
from app.core.config import settings
# Import the extracted functions
from .llm_rag import get_rag_context
from .llm_stream import stream_llm_response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MAX_TOOL_TURNS = 5 # Maximum number of LLM <-> Tool execution cycles per user message

# --- Define Schemas for Connected Servers ---
# Schemas based on the persona context for connected MCP servers
CONNECTED_SERVER_SCHEMAS = {
    "filesystem": {
        "read_file": {
            "description": "Read the complete contents of a file from the file system.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        },
        "write_file": {
            "description": "Create or overwrite a file with new content.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}
        },
        "list_directory": {
            "description": "Get a detailed listing of files and directories.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        },
        # Add other filesystem tools if needed (edit_file, create_directory, etc.)
    },
    "puppeteer": {
         "puppeteer_navigate": {
            "description": "Navigate to a URL",
            "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
        },
         "puppeteer_screenshot": {
            "description": "Take a screenshot",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "selector": {"type": "string"}, "width": {"type": "number"}, "height": {"type": "number"}}, "required": ["name"]}
        },
         "puppeteer_click": {
            "description": "Click an element",
            "parameters": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}
        },
         "puppeteer_fill": {
            "description": "Fill an input field",
            "parameters": {"type": "object", "properties": {"selector": {"type": "string"}, "value": {"type": "string"}}, "required": ["selector", "value"]}
        },
        # Add other puppeteer tools...
    },
    "github": {
        "get_file_contents": {
            "description": "Get the contents of a file or directory from a GitHub repository.",
            "parameters": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "path": {"type": "string"}, "branch": {"type": "string"}}, "required": ["owner", "repo", "path"]}
        },
        "search_repositories": {
            "description": "Search for GitHub repositories.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "page": {"type": "number"}, "perPage": {"type": "number"}}, "required": ["query"]}
        },
        "create_issue": {
            "description": "Create a new issue in a GitHub repository.",
            "parameters": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "labels": {"type": "array", "items": {"type": "string"}}}, "required": ["owner", "repo", "title"]}
        },
        # Add other github tools...
    },
    "kubernetes": {
         "list_pods": {
            "description": "List pods in a namespace.",
            "parameters": {"type": "object", "properties": {"namespace": {"type": "string", "default": "default"}}, "required": ["namespace"]}
        },
         "get_logs": {
            "description": "Get logs from pods, deployments, or jobs.",
            "parameters": {"type": "object", "properties": {"resourceType": {"type": "string", "enum": ["pod", "deployment", "job"]}, "name": {"type": "string"}, "namespace": {"type": "string", "default": "default"}, "container": {"type": "string"}, "tail": {"type": "number"}}, "required": ["resourceType", "name"]}
        },
        # Add other kubernetes tools...
    },
    "fetch": {
        "fetch": {
            "description": "Fetches a URL from the internet and optionally extracts its contents as markdown.",
            "parameters": {"type": "object", "properties": {"url": {"type": "string", "format": "uri"}, "max_length": {"type": "integer", "default": 5000}, "start_index": {"type": "integer", "default": 0}, "raw": {"type": "boolean", "default": False}}, "required": ["url"]}
        }
    },
    "sequential-thinking": { # Note: hyphen in name
        "sequentialthinking": {
            "description": "A detailed tool for dynamic and reflective problem-solving through thoughts.",
            "parameters": {"type": "object", "properties": {"thought": {"type": "string"}, "nextThoughtNeeded": {"type": "boolean"}, "thoughtNumber": {"type": "integer", "minimum": 1}, "totalThoughts": {"type": "integer", "minimum": 1}, "isRevision": {"type": "boolean"}, "revisesThought": {"type": "integer", "minimum": 1}, "branchFromThought": {"type": "integer", "minimum": 1}, "branchId": {"type": "string"}, "needsMoreThoughts": {"type": "boolean"}}, "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]}
        }
    },
    "memory": {
        "search_nodes": {
            "description": "Search for nodes in the knowledge graph based on a query.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        },
        "create_entities": {
            "description": "Create multiple new entities in the knowledge graph.",
            "parameters": {"type": "object", "properties": {"entities": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "entityType": {"type": "string"}, "observations": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "entityType", "observations"]}}}, "required": ["entities"]}
        },
        # Add other memory tools...
    },
    "time": {
        "get_current_time": {
            "description": "Get current time in a specific timezone.",
            "parameters": {"type": "object", "properties": {"timezone": {"type": "string", "description": "IANA timezone name"}}, "required": ["timezone"]}
        },
        "convert_time": {
            "description": "Convert time between timezones.",
            "parameters": {"type": "object", "properties": {"source_timezone": {"type": "string"}, "time": {"type": "string", "description": "HH:MM"}, "target_timezone": {"type": "string"}}, "required": ["source_timezone", "time", "target_timezone"]}
        }
    }
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
                    'base_url': chat_base_url_to_pass
                },
                embedding_config={
                    'provider': embedding_provider,
                    'model': self.embedding_model,
                    'api_key': embedding_api_key,
                    'base_url': embedding_base_url_to_pass
                }
            )
        else:
            client_result = LLMFactory.create_client(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                base_url=chat_base_url_to_pass,
                embedding_model=self.embedding_model,
                embedding_provider=embedding_provider
            )

        # Handle single client or separate clients
        if isinstance(client_result, tuple):
            self.chat_client, self.embedding_client = client_result
        else:
            self.chat_client = self.embedding_client = client_result

        # Create retriever for RAG
        self.retriever = HybridRetriever(db)


    async def chat(
        self,
        chat_id: str,
        user_message: str,
        use_rag: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = True
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Send a message to the LLM and get a response, orchestrating RAG and streaming.
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
                context_text += "Please use this information to help answer the user's question. If the information doesn't contain the answer, just say so."
                current_system_prompt += context_text
                logger.info(f"Added RAG context to system prompt. Combined length: {len(current_system_prompt)}")

        # --- Start Tool Fetching and Formatting ---
        tools = []
        enabled_mcp_configs = [] # Keep track of configs for later execution
        if self.user_id:
            try:
                enabled_mcp_configs = [c for c in MCPConfigService.get_configs_by_user(self.db, self.user_id) if c.enabled]
                logger.info(f"Found {len(enabled_mcp_configs)} enabled MCP servers for user {self.user_id}")
                for config in enabled_mcp_configs:
                    server_type_key = next((key for key in CONNECTED_SERVER_SCHEMAS if config.name.lower().startswith(key)), None)
                    if server_type_key:
                        server_tools = CONNECTED_SERVER_SCHEMAS[server_type_key]
                        logger.info(f"Found schema for server type '{server_type_key}' (config: {config.name})")
                        for tool_name, tool_info in server_tools.items():
                            unique_tool_name = f"{config.name.replace('-', '_')}__{tool_name}"
                            tools.append({"type": "function", "function": {"name": unique_tool_name, "description": tool_info.get("description"), "parameters": tool_info.get("parameters")}})
                    else:
                        logger.warning(f"No predefined schema for server '{config.name}'. Creating generic.")
                        tools.append({"type": "function", "function": {"name": config.name.replace("-", "_"), "description": f"Tool from '{config.name}' server.", "parameters": {"type": "object", "properties": {}}}})
                if tools: logger.info(f"Generated {len(tools)} tool schemas from connected server info.")
            except Exception as e: logger.error(f"Failed to fetch or format MCP tools: {e}"); tools = []
        else: logger.warning("No user_id provided, cannot fetch MCP tools."); tools = []
        # --- End Tool Fetching and Formatting ---

        # Format messages for the LLM, including history
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
        formatted_messages.append(self.chat_client.format_chat_message("user", user_message))

        # Logging
        roles = [msg["role"] for msg in formatted_messages]; logger.info(f"Sending {len(formatted_messages)} messages to LLM. Roles: {roles}")
        if settings.LLM_DEBUG_LOGGING:
            if context_documents: logger.info(f"RAG context included: {len(context_documents)} documents")
            if tools: logger.info(f"Tools included: {json.dumps(tools, indent=2)}")
        elif context_documents: logger.info(f"RAG context included: {len(context_documents)} documents")
        elif tools: logger.info(f"Tools included: {len(tools)} tools")

        # Generate response
        if stream:
            # Streaming logic (passes tools down)
            return stream_llm_response(
                db=self.db, chat_client=self.chat_client, chat_id=chat_id,
                formatted_messages=formatted_messages, temperature=temperature, max_tokens=max_tokens,
                context_documents=context_documents, system_prompt=current_system_prompt,
                model=self.model, provider=self.provider, tools=tools
            )
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
                        temperature=temperature, max_tokens=max_tokens,
                        stream=False, tools=send_tools, tool_choice=tool_choice_this_turn
                    )
                except Exception as llm_error:
                     logger.exception(f"LLM generation failed on turn {turn + 1}: {llm_error}")
                     error_content = f"An error occurred while communicating with the AI model: {str(llm_error)}"
                     # Save error message before returning
                     ChatService.add_message(self.db, chat_id, "assistant", error_content, finish_reason="error", model=self.model, provider=self.provider)
                     return {"content": error_content, "finish_reason": "error"}

                end_time = time.time(); duration = end_time - start_time

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

                # Add tokens_per_second for consistency, even if not used later
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
                    if not self.user_id: # Should have been checked earlier, but double-check
                         logger.error("Cannot execute tools: user_id missing.")
                         # Return the assistant message asking for tools, as we can't proceed
                         return current_response

                    tool_execution_tasks = []
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.get("id")
                        function_info = tool_call.get("function", {})
                        full_tool_name = function_info.get("name")
                        arguments_str = function_info.get("arguments", "{}")
                        if not tool_call_id or not full_tool_name: continue
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
                         execution_outcomes = await asyncio.gather(*tool_execution_tasks, return_exceptions=True)
                         for i, outcome in enumerate(execution_outcomes):
                             original_call_info = tool_calls[i] # Assumes order matches tasks
                             tool_call_id = original_call_info["id"]
                             full_tool_name = original_call_info["function"]["name"]
                             if isinstance(outcome, Exception):
                                  logger.exception(f"Error executing tool {full_tool_name}: {outcome}")
                                  tool_result_content_str = json.dumps({"error": {"message": f"Error executing tool: {str(outcome)}"}})
                             else: tool_result_content_str = outcome.get("result", '{"error": "Tool execution failed."}')
                             tool_message_for_llm = {"role": "tool", "tool_call_id": tool_call_id, "name": full_tool_name, "content": tool_result_content_str}
                             tool_results_messages.append(tool_message_for_llm)
                             ChatService.add_message(self.db, chat_id, "tool", content=tool_result_content_str, tool_call_id=tool_call_id, name=full_tool_name)

                    current_formatted_messages.extend(tool_results_messages) # Add results for the next LLM call
                    # Continue to the next iteration of the loop

                elif content:
                    # --- Handle Final Content Response ---
                    logger.info(f"Received final content response on turn {turn + 1}.")
                    ChatService.add_message(
                        self.db, chat_id, "assistant", content,
                        tokens=total_tokens, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                        tokens_per_second=tokens_per_second, model=response_model, provider=response_provider,
                        context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                        finish_reason=finish_reason
                    )
                    return current_response # Exit loop and return final response
                else:
                    # Handle unexpected empty response
                    logger.warning(f"LLM response had no content or tool_calls on turn {turn + 1}. Finish reason: {finish_reason}")
                    error_content = "I received an empty response from the AI model."
                    ChatService.add_message(self.db, chat_id, "assistant", error_content, finish_reason=finish_reason or "error", model=response_model, provider=response_provider)
                    current_response["content"] = error_content # Add error content
                    return current_response # Exit loop and return error response

            # If loop finishes without returning content (exceeded MAX_TOOL_TURNS)
            logger.error(f"Exceeded maximum tool turns ({MAX_TOOL_TURNS}).")
            error_content = "I could not complete the request after multiple tool uses. Please try rephrasing."
            ChatService.add_message(self.db, chat_id, "assistant", error_content, finish_reason="tool_loop_limit", model=self.model, provider=self.provider)
            # Return the last response received, but add error content
            if current_response: current_response["content"] = error_content
            else: current_response = {"content": error_content, "finish_reason": "tool_loop_limit"}
            return current_response


    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """ Get embeddings for a list of texts using the configured embedding client. """
        return await self.embedding_client.get_embeddings(texts)

    async def get_available_models(self) -> tuple[List[str], List[str]]:
        """ Get available models for the current provider. """
        # ... (implementation remains the same) ...
        chat_models = []
        embedding_models = []
        try:
            if hasattr(self.chat_client, 'list_models'):
                models_data = await self.chat_client.list_models()
                if self.provider == "ollama":
                    chat_models = models_data
                    embedding_models = models_data
                elif self.provider == "openrouter":
                     model_groups = {}
                     for model_info in models_data:
                         if model_info.get("id"):
                             provider_prefix = model_info["id"].split("/")[0] if "/" in model_info["id"] else "other"
                             if provider_prefix not in model_groups: model_groups[provider_prefix] = []
                             model_groups[provider_prefix].append(model_info["id"])
                     for provider_prefix in sorted(model_groups.keys()):
                         chat_models.extend(sorted(model_groups[provider_prefix]))
                     embedding_models = ["openai/text-embedding-ada-002"]
                else:
                     chat_models = models_data
                     embedding_models = []
            elif self.provider == "openai":
                chat_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
                embedding_models = ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
            elif self.provider == "anthropic":
                 chat_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-2.1", "claude-2.0", "claude-instant-1.2"]
                 embedding_models = []
            elif self.provider == "google_gemini":
                 try:
                     api_key_to_use = self.api_key or LLMConfigService.get_active_config(self.db).api_key
                     if api_key_to_use:
                         genai.configure(api_key=api_key_to_use)
                         all_models = genai.list_models()
                         for model in all_models:
                             if 'generateContent' in model.supported_generation_methods: chat_models.append(model.name)
                             if 'embedContent' in model.supported_generation_methods and 'aqa' not in model.name: embedding_models.append(model.name)
                         chat_models.sort(); embedding_models.sort()
                     else: raise ValueError("Google Gemini API key required.")
                 except Exception as e:
                     logger.error(f"Failed to list Google Gemini models dynamically: {e}. Using fallback.")
                     chat_models = ["models/gemini-pro", "models/gemini-1.5-pro-latest"]; embedding_models = ["models/embedding-001"]
            elif self.provider == "deepseek":
                 chat_models = ["deepseek-chat", "deepseek-coder"]; embedding_models = ["deepseek-embedding"]
            else: logger.warning(f"Model listing not implemented or failed for provider: {self.provider}")

            if self.embedding_client != self.chat_client and hasattr(self.embedding_client, 'list_models'):
                 try:
                     embedding_models_from_client = await self.embedding_client.list_models()
                     if embedding_models_from_client: embedding_models = embedding_models_from_client
                 except Exception as e: logger.error(f"Failed to list models from separate embedding client: {e}")

            return sorted(list(set(chat_models))), sorted(list(set(embedding_models)))
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return [], []