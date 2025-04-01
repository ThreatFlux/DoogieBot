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
from app.rag.hybrid_retriever import HybridRetriever
from app.core.config import settings
# Import the extracted functions
from .llm_rag import get_rag_context
from .llm_stream import stream_llm_response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        temperature: Optional[float] = None # Added temperature to init args (optional)
    ):
        """
        Initialize the LLM service.
        """
        self.db = db

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
        # temperature: float = 0.7, # Removed temperature parameter
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
            # Call the extracted RAG function
            context_documents = await get_rag_context(
                db=self.db,
                embedding_client=self.embedding_client,
                retriever=self.retriever,
                query=user_message
                # top_k is handled within get_rag_context using config
            )

            if context_documents:
                # Create context message and append to system prompt
                context_text = "\n\nHere is some relevant information that may help you answer the user's question:\n\n"
                for i, doc in enumerate(context_documents):
                    context_text += f"[{i+1}] {doc['content']}\n\n"

                context_text += "Please use this information to help answer the user's question. If the information doesn't contain the answer, just say so."

                # Combine with system prompt
                current_system_prompt += context_text
                logger.info(f"Added RAG context to system prompt. Combined length: {len(current_system_prompt)}")

        # Format messages for the LLM
        formatted_messages = [
            self.chat_client.format_chat_message("system", current_system_prompt)
        ]

        # Add chat history
        for msg in messages:
            formatted_messages.append(
                self.chat_client.format_chat_message(msg.role, msg.content)
            )

        # Add user message
        formatted_messages.append(
            self.chat_client.format_chat_message("user", user_message)
        )

        # Log message count and roles for debugging
        roles = [msg["role"] for msg in formatted_messages]
        logger.info(f"Sending {len(formatted_messages)} messages to LLM. Roles: {roles}")

        # Log prompt details if debug logging is enabled
        if settings.LLM_DEBUG_LOGGING:
            # Simplified logging for brevity in refactored file
            logger.info("Full prompt logging enabled (details omitted here, check original file if needed)")
            if context_documents:
                 logger.info(f"RAG context included: {len(context_documents)} documents")
        elif context_documents:
             logger.info(f"RAG context included: {len(context_documents)} documents")


        # Generate response
        if stream:
            # Call the extracted streaming function
            return stream_llm_response(
                db=self.db,
                chat_client=self.chat_client,
                chat_id=chat_id,
                formatted_messages=formatted_messages,
                temperature=self.temperature, # Use instance temperature
                max_tokens=max_tokens,
                context_documents=context_documents,
                system_prompt=current_system_prompt, # Pass the potentially modified system prompt
                model=self.model, # Pass instance model
                provider=self.provider # Pass instance provider
            )
        else:
            # Non-streaming generation
            start_time = time.time()
            response = await self.chat_client.generate(
                formatted_messages,
                temperature=self.temperature, # Use instance temperature
                max_tokens=max_tokens,
                stream=False
            )
            end_time = time.time()
            duration = end_time - start_time

            # Calculate tokens per second if possible
            tokens = response.get("tokens")
            tokens_per_second = tokens / duration if tokens and duration > 0 else 0.0

            # Save assistant message to database
            ChatService.add_message(
                self.db,
                chat_id,
                "assistant",
                response["content"],
                tokens=tokens,
                tokens_per_second=tokens_per_second,
                model=response.get("model", self.model), # Use model from response or instance
                provider=response.get("provider", self.provider), # Use provider from response or instance
                context_documents=[doc["id"] for doc in context_documents] if context_documents else None
            )

            # Add tokens_per_second to the response dict if not already present
            if "tokens_per_second" not in response:
                 response["tokens_per_second"] = tokens_per_second

            return response

    # Removed _stream_response method - now in llm_stream.py
    # Removed _get_rag_context method - now in llm_rag.py
    # Removed _rerank_documents method - now in llm_rag.py

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts using the configured embedding client.
        """
        return await self.embedding_client.get_embeddings(texts)

    async def get_available_models(self) -> tuple[List[str], List[str]]:
        """
        Get available models for the current provider.
        Attempts dynamic fetching, falls back to static lists.
        """
        chat_models = []
        embedding_models = []

        try:
            # Use chat_client if it has list_models capability (covers Ollama, OpenRouter)
            if hasattr(self.chat_client, 'list_models'):
                models_data = await self.chat_client.list_models()
                if self.provider == "ollama":
                    chat_models = models_data
                    embedding_models = models_data # Ollama uses same models for both
                elif self.provider == "openrouter":
                     # Process OpenRouter response (assuming it's a list of dicts with 'id')
                     model_groups = {}
                     for model_info in models_data:
                         if model_info.get("id"):
                             provider_prefix = model_info["id"].split("/")[0] if "/" in model_info["id"] else "other"
                             if provider_prefix not in model_groups:
                                 model_groups[provider_prefix] = []
                             model_groups[provider_prefix].append(model_info["id"])
                     # Sort and flatten
                     for provider_prefix in sorted(model_groups.keys()):
                         chat_models.extend(sorted(model_groups[provider_prefix]))
                     embedding_models = ["openai/text-embedding-ada-002"] # Default for OpenRouter
                else:
                     # Generic handling if other providers implement list_models
                     chat_models = models_data
                     # Assume no embedding models unless specified
                     embedding_models = []

            # Specific provider logic if list_models isn't available on chat_client
            elif self.provider == "openai":
                chat_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
                embedding_models = ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
            elif self.provider == "anthropic":
                 chat_models = [
                     "claude-3-opus-20240229", "claude-3-sonnet-20240229",
                     "claude-3-haiku-20240307", "claude-2.1", "claude-2.0",
                     "claude-instant-1.2"
                 ]
                 embedding_models = []
            elif self.provider == "google_gemini":
                 try:
                     # Configure API key
                     api_key_to_use = self.api_key or LLMConfigService.get_active_config(self.db).api_key
                     if api_key_to_use:
                         genai.configure(api_key=api_key_to_use)
                         all_models = genai.list_models()
                         for model in all_models:
                             if 'generateContent' in model.supported_generation_methods:
                                 chat_models.append(model.name)
                             if 'embedContent' in model.supported_generation_methods and 'aqa' not in model.name:
                                 embedding_models.append(model.name)
                         chat_models.sort()
                         embedding_models.sort()
                     else:
                         raise ValueError("Google Gemini API key required.")
                 except Exception as e:
                     logger.error(f"Failed to list Google Gemini models dynamically: {e}. Using fallback.")
                     # Fallback list
                     chat_models = ["models/gemini-pro", "models/gemini-1.5-pro-latest"]
                     embedding_models = ["models/embedding-001"]
            elif self.provider == "deepseek":
                 chat_models = ["deepseek-chat", "deepseek-coder"]
                 embedding_models = ["deepseek-embedding"]
            else:
                 logger.warning(f"Model listing not implemented or failed for provider: {self.provider}")

            # Ensure embedding models are listed if using a separate embedding client
            if self.embedding_client != self.chat_client and hasattr(self.embedding_client, 'list_models'):
                 try:
                     embedding_models_from_client = await self.embedding_client.list_models()
                     # Use these if available, otherwise keep potentially derived list
                     if embedding_models_from_client:
                          embedding_models = embedding_models_from_client
                 except Exception as e:
                      logger.error(f"Failed to list models from separate embedding client: {e}")

            return sorted(list(set(chat_models))), sorted(list(set(embedding_models)))

        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return [], []