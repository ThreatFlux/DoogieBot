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
from app.services.reranking_config import RerankingConfigService # Added import
from app.rag.hybrid_retriever import HybridRetriever
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    """
    Service for interacting with LLMs.
    """
    
    def __init__(
        self,
        db: Session,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize the LLM service.
        
        Args:
            db: Database session
            provider: LLM provider name (optional, uses active config if not provided)
            model: Model name (optional, uses active config if not provided)
            system_prompt: Global system prompt (optional, uses active config if not provided)
                       This prompt is used for all LLM providers
            api_key: API key (optional, uses active config if not provided)
            base_url: Base URL (optional, uses active config if not provided)
            embedding_model: Embedding model name (optional, uses active config if not provided)
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
        
        # Embedding configuration
        self.embedding_model = embedding_model or (embedding_config.model if embedding_config else None)
        embedding_provider = embedding_config.provider if embedding_config else None
        embedding_api_key = embedding_config.api_key if embedding_config else None
        embedding_base_url = embedding_config.base_url if embedding_config else None
        
        # Determine correct base URLs to pass based on provider.
        # Only pass the configured base_url if the provider explicitly requires it (e.g., Ollama).
        # For others (OpenAI, Anthropic, OpenRouter), pass None to use their default endpoints.
        
        # Chat client base URL
        chat_base_url_to_pass = None
        if self.provider == 'ollama': # Only pass base_url for Ollama
            chat_base_url_to_pass = self.base_url
            logger.info(f"Using configured base_url '{chat_base_url_to_pass}' for Ollama chat client.")
        else:
            logger.info(f"Ignoring configured base_url for non-Ollama chat provider '{self.provider}'. Using default.")
            
        # Embedding client base URL
        embedding_base_url_to_pass = None
        if embedding_provider == 'ollama': # Only pass base_url for Ollama
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
                    'base_url': chat_base_url_to_pass # Use determined URL
                },
                embedding_config={
                    'provider': embedding_provider,
                    'model': self.embedding_model,
                    'api_key': embedding_api_key, # Use fetched key
                    'base_url': embedding_base_url_to_pass # Use determined URL
                }
            )
        else:
            # Fallback to legacy method if either config is missing
            # Note: create_client's base_url param primarily affects the chat client.
            # The factory's internal logic handles the embedding base URL based on embedding_provider.
            client_result = LLMFactory.create_client(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                base_url=chat_base_url_to_pass, # Use determined URL for chat
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
        Send a message to the LLM and get a response.
        
        Args:
            chat_id: Chat ID
            user_message: User message
            use_rag: Whether to use RAG for context
            temperature: Temperature for generation
            max_tokens: Maximum number of tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Response from the LLM or an async generator for streaming
        """
        # Get chat history
        messages = ChatService.get_messages(self.db, chat_id)
        
        # Prepare system prompt
        system_message = self.system_prompt
        logger.info(f"Using system prompt: {system_message[:100]}...")
        
        # Add RAG context if enabled
        context_documents = None
        if use_rag:
            # Get relevant documents
            context_documents = await self._get_rag_context(user_message)
            
            if context_documents:
                # Create context message and append to system prompt
                context_text = "\n\nHere is some relevant information that may help you answer the user's question:\n\n"
                for i, doc in enumerate(context_documents):
                    context_text += f"[{i+1}] {doc['content']}\n\n"
                
                context_text += "Please use this information to help answer the user's question. If the information doesn't contain the answer, just say so."
                
                # Combine with system prompt
                system_message += context_text
                logger.info(f"Added RAG context to system prompt. Combined length: {len(system_message)}")
        
        # Format messages for the LLM
        formatted_messages = [
            self.chat_client.format_chat_message("system", system_message)
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
        
        # Log the full prompt including context for debugging if LLM_DEBUG_LOGGING is enabled
        if settings.LLM_DEBUG_LOGGING:
            logger.info("Full prompt with context (LLM_DEBUG_LOGGING enabled):")
            for i, msg in enumerate(formatted_messages):
                # Log each message separately to avoid log size limitations
                logger.info(f"Message {i} - Role: {msg['role']}")
                
                # For system messages that might contain RAG context, log in detail
                if msg['role'] == 'system' and context_documents:
                    # Log the system message in chunks to avoid log size limitations
                    content_chunks = [msg['content'][i:i+1000] for i in range(0, len(msg['content']), 1000)]
                    for j, chunk in enumerate(content_chunks):
                        logger.info(f"System message chunk {j}: {chunk}")
                    
                    # Log RAG hits specifically
                    logger.info(f"RAG context included in prompt: {len(context_documents)} documents")
                    for i, doc in enumerate(context_documents):
                        logger.info(f"RAG hit {i+1}: ID={doc.get('id', 'unknown')}, Source={doc.get('source', 'unknown')}, Score={doc.get('score', 0)}")
                        # Log a preview of the content
                        content = doc.get('content', '')
                        logger.info(f"RAG hit {i+1} content preview: {content[:200]}...")
                else:
                    # For non-system messages or when no RAG context, log a preview
                    content_preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                    logger.info(f"Content preview: {content_preview}")
        else:
            # Even if detailed logging is disabled, still log basic RAG information
            if context_documents:
                logger.info(f"RAG context included in prompt: {len(context_documents)} documents")
                for i, doc in enumerate(context_documents):
                    logger.info(f"RAG hit {i+1}: ID={doc.get('id', 'unknown')}, Source={doc.get('source', 'unknown')}, Score={doc.get('score', 0)}")
        
        # Note: We don't add the user message to the database here
        # because it's already added in the stream_from_llm_get function
        # in backend/app/api/routes/chats.py
        
        # Start time for calculating tokens per second
        start_time = time.time()
        
        # Generate response
        if stream:
            return self._stream_response(
                chat_id, 
                formatted_messages, 
                temperature, 
                max_tokens, 
                context_documents
            )
        else:
            # Get response from LLM
            response = await self.chat_client.generate(
                formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            # Save assistant message to database
            ChatService.add_message(
                self.db,
                chat_id,
                "assistant",
                response["content"],
                tokens=response.get("tokens"),
                tokens_per_second=response.get("tokens_per_second"),
                model=response.get("model"),
                provider=response.get("provider"),
                context_documents=[doc["id"] for doc in context_documents] if context_documents else None
            )

            return response

    async def _stream_response(
        self,
        chat_id: str,
        formatted_messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        context_documents: Optional[List[Dict[str, Any]]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from the LLM.
        
        Args:
            chat_id: Chat ID
            formatted_messages: Formatted messages for the LLM
            temperature: Temperature for generation
            max_tokens: Maximum number of tokens to generate
            context_documents: Context documents from RAG
            
        Yields:
            Chunks of the response
        """
        logger.debug(f"Starting streaming response for chat {chat_id}")
        
        # Initialize variables for tracking the response
        full_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        tokens_per_second = 0.0
        finish_reason = None
        model = self.model or settings.DEFAULT_CHAT_MODEL # Start with configured model
        provider = self.provider
        chunk_count = 0
        error_occurred = False
        error_message = ""
        
        try:
            # Get streaming response from LLM client
            logger.debug(f"Requesting streaming response from LLM client for chat {chat_id}")
            
            # Prepare arguments for the generate call
            generate_args = {
                "messages": formatted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            # Conditionally add system_prompt for clients that support it as a separate argument
            if isinstance(self.chat_client, (AnthropicClient, GoogleGeminiClient)):
                generate_args["system_prompt"] = self.system_prompt
                logger.debug("Passing system_prompt as a separate argument to generate()")
            else:
                 # For other clients (like OpenAI), system prompt is expected in messages list
                 logger.debug("System prompt included in messages list for generate()")


            # Await the generate call to get the async generator
            response_stream = await self.chat_client.generate(**generate_args)

            logger.debug(f"Got response_stream generator from LLM client")
            logger.debug(f"Starting to iterate through response_stream chunks")

            async for chunk in response_stream:
                chunk_count += 1
                chunk_type = chunk.get("type")
                
                logger.debug(f"Received chunk {chunk_count} of type '{chunk_type}' for chat {chat_id}")

                # Yield the raw chunk immediately
                yield chunk

                # Process chunk based on type
                if chunk_type == "start":
                    prompt_tokens = chunk.get("usage", {}).get("prompt_tokens", 0)
                    # Potentially update model/provider if provided in start event
                    model = chunk.get("model", model)
                    provider = chunk.get("provider", provider)
                elif chunk_type == "delta":
                    delta_content = chunk.get("content", "")
                    if delta_content:
                        full_content += delta_content
                elif chunk_type == "end":
                    usage = chunk.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens) # Use final prompt tokens if available
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens) # Calculate if not provided
                    tokens_per_second = chunk.get("tokens_per_second", 0.0)
                    finish_reason = chunk.get("finish_reason")
                    # Potentially update model/provider if provided in end event
                    model = chunk.get("model", model)
                    provider = chunk.get("provider", provider)
                    logger.debug(f"Stream ended for chat {chat_id}. Finish reason: {finish_reason}")
                    logger.debug(f"Stream ended for chat {chat_id}. Finish reason: {finish_reason}")

                    # Save the final message BEFORE yielding the final chunk
                    logger.debug(f"Saving final message for chat {chat_id} before yielding end chunk.")
                    ChatService.add_message(
                        self.db,
                        chat_id,
                        "assistant",
                        full_content, # Save accumulated content
                        tokens=total_tokens,
                        tokens_per_second=tokens_per_second,
                        model=model,
                        provider=provider,
                        context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                    )
                    logger.debug(f"Final message saved for chat {chat_id}")
                    # Yield the final chunk now that saving is done
                    yield chunk
                    break # Exit loop after processing and saving end event

                elif chunk_type == "error":
                    error_message = chunk.get("error", "Unknown streaming error")
                    logger.error(f"Error received during stream for chat {chat_id}: {error_message}")
                    error_occurred = True
                    full_content = f"An error occurred: {error_message}" # Set content to error message

                    # Save the error message BEFORE yielding the error chunk
                    logger.debug(f"Saving error message for chat {chat_id} before yielding error chunk.")
                    ChatService.add_message(
                        self.db,
                        chat_id,
                        "assistant",
                        full_content, # Save error message
                        model=model,
                        provider=provider,
                        context_documents=[doc["id"] for doc in context_documents] if context_documents else None,
                    )
                    logger.debug(f"Error message saved for chat {chat_id}")
                    # Yield the error chunk now that saving is done
                    yield chunk
                    break # Exit loop on error

                # Add a small delay to prevent overwhelming the client, less frequently
                if chunk_count % 20 == 0:
                    await asyncio.sleep(0.01)
                else:
                    await asyncio.sleep(0) # Yield control briefly

            # Message saving is now handled within the loop before yielding final/error chunks
            # logger.debug(f"Saving final message/error for chat {chat_id}. Error occurred: {error_occurred}")
            # ChatService.add_message(...) # Removed from here

        except asyncio.TimeoutError: # This corresponds to the generate call timeout, less likely now
            logger.error(f"Timeout occurred during initial generation call for chat {chat_id}")
            error_message = "The LLM took too long to respond initially. Please try again."
            error_chunk = {
                "content": error_message,
                "error": True,
                "done": True
            }
            yield error_chunk
            # Save the error message to the chat
            ChatService.add_message(
                self.db, chat_id, "assistant", error_message, model=model, provider=provider,
                context_documents=[doc["id"] for doc in context_documents] if context_documents else None
            )
            return # Stop the generator

        # This outer except block handles broader errors during the streaming process itself
        except Exception as e:
            logger.exception(f"Error in streaming response for chat {chat_id}: {str(e)}")
            error_message = "The response took too long to generate. This might be due to high server load or complexity of the query with RAG processing."
            error_chunk = {
                "content": error_message,
                "error": True,
                "done": True
            }
            yield error_chunk

            # Save the error message to the chat
            ChatService.add_message(
                self.db,
                chat_id,
                "assistant",
                error_message,
                model=model,
                provider=provider,
                context_documents=[doc["id"] for doc in context_documents] if context_documents else None
            )

        except Exception as e:
            logger.exception(f"Error in streaming response for chat {chat_id}: {str(e)}")
            error_message = f"An error occurred while generating the response: {str(e)}"
            error_chunk = {
                "content": error_message,
                "error": True,
                "done": True
            }
            yield error_chunk

            # Save the error message to the chat
            ChatService.add_message(
                self.db,
                chat_id,
                "assistant",
                error_message,
                model=model,
                provider=provider,
                context_documents=[doc["id"] for doc in context_documents] if context_documents else None
            )
    
    async def _get_rag_context(self, query: str, top_k: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get relevant context for RAG.
        
        Args:
            query: User query
            top_k: Number of results to return (optional, uses config value if not provided)
            
        Returns:
            List of relevant documents or None if no results
        """
        # Get top_k from config if not provided
        active_config = LLMConfigService.get_active_config(self.db)
        if top_k is None:
            # Check if there's a top_k value in the active config
            if active_config and active_config.config and 'rag_top_k' in active_config.config:
                top_k = active_config.config.get('rag_top_k')
            else:
                # Default to 3 if not configured
                top_k = 3
        try:
            # Generate query embedding using the embedding client
            logger.info(f"Generating embedding for query: {query[:50]}...")
            query_embedding = None
            try:
                # Get embedding for the query
                embeddings = await self.embedding_client.get_embeddings([query])
                if embeddings and len(embeddings) > 0:
                    query_embedding = embeddings[0]
                    logger.info(f"Successfully generated query embedding with dimension {len(query_embedding)}")
                else:
                    logger.warning("Failed to generate query embedding: empty result")
            except Exception as embed_error:
                logger.error(f"Error generating query embedding: {str(embed_error)}")
                # Continue with keyword search even if embedding fails
            
            # Retrieve relevant documents
            results = await self.retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            if not results:
                return None
            
            # Format results for context
            context = []
            for result in results:
                context.append({
                    "id": result.get("id"),
                    "content": result.get("content"),
                    "score": result.get("score", 0),
                    "source": result.get("source")
                })
            
            # Apply reranking if enabled
            use_reranking = active_config and active_config.config and active_config.config.get('use_reranking', False)
            if use_reranking and context:
                # Fetch the dedicated active reranking configuration
                reranking_config = RerankingConfigService.get_active_config(self.db)

                if reranking_config:
                    # Find the specific LLM config for the reranker's provider to get API key/base URL
                    # TODO: Consider adding a more direct get_config_by_provider method if performance is an issue
                    all_llm_configs = LLMConfigService.get_all_configs(self.db)
                    llm_config_for_reranker = next((c for c in all_llm_configs if c.provider == reranking_config.provider), None)

                    if llm_config_for_reranker:
                        logger.info(f"Reranking results using dedicated config: {reranking_config.provider}/{reranking_config.model}")
                        try:
                            # Create a reranking client using dedicated reranking config and its corresponding LLM config details
                            # Use _create_single_client directly to avoid legacy logic mixing embedding models
                            reranking_client = LLMFactory._create_single_client(
                                provider=reranking_config.provider,
                                model=reranking_config.model,
                                api_key=llm_config_for_reranker.api_key,
                                base_url=llm_config_for_reranker.base_url
                            )

                            if not reranking_client:
                                logger.warning("Failed to create reranking client using _create_single_client")
                                # Continue without reranking if client creation fails
                            else:
                                # Extract document contents and prepare for reranking
                                documents = [doc["content"] for doc in context]

                                # Get reranked scores
                                reranked_scores = await self._rerank_documents(reranking_client, query, documents)

                                # Update scores in context
                                if reranked_scores and len(reranked_scores) == len(context):
                                    for i, score in enumerate(reranked_scores):
                                        context[i]["score"] = score

                                    # Sort by new scores (descending)
                                    context.sort(key=lambda x: x["score"], reverse=True)

                                    logger.info(f"Successfully reranked {len(context)} documents")
                                else:
                                    logger.warning(f"Reranking returned {len(reranked_scores) if reranked_scores else 0} scores for {len(context)} documents. Using original ranking.")
                        except Exception as e:
                            logger.error(f"Error during reranking process: {str(e)}")
                            # Continue with original ranking if reranking fails
                    else:
                        logger.warning(f"Reranking enabled, active reranking config found ({reranking_config.provider}/{reranking_config.model}), but no matching LLM config found for provider '{reranking_config.provider}'. Cannot get API key/base URL. Skipping reranking.")
                else:
                    # Only log warning if use_reranking was explicitly true in the main LLM config, but no dedicated reranking config exists
                    if active_config and active_config.config and active_config.config.get('use_reranking', False):
                         logger.warning("Reranking enabled in main LLM config, but no active dedicated reranking configuration found in the database. Skipping reranking.")
            
            return context
        except Exception as e:
            logger.error(f"Error getting RAG context: {str(e)}")
            return None
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        return await self.embedding_client.get_embeddings(texts)
    
    async def _rerank_documents(self, reranking_client, query: str, documents: List[str]) -> List[float]:
        """
        Rerank documents based on their relevance to the query.
        
        Args:
            reranking_client: LLM client for reranking
            query: User query
            documents: List of document contents to rerank
            
        Returns:
            List of relevance scores for each document
        """
        if not documents:
            return []
        
        try:
            # If the reranking client has a specific rerank method, use it
            if hasattr(reranking_client, 'rerank'):
                scores = await reranking_client.rerank(query, documents)
                return scores
            
            # Check if the client has embedding capabilities
            if hasattr(reranking_client, 'get_embeddings'):
                # Use embeddings to calculate similarity
                try:
                    query_embedding = await reranking_client.get_embeddings([query])
                    if not query_embedding or len(query_embedding) == 0:
                        logger.warning("Failed to generate query embedding for reranking")
                        return []
                    
                    query_embedding = query_embedding[0]
                    
                    # Get embeddings for all documents
                    doc_embeddings = await reranking_client.get_embeddings(documents)
                    if not doc_embeddings or len(doc_embeddings) != len(documents):
                        logger.warning(f"Failed to generate document embeddings for reranking: got {len(doc_embeddings) if doc_embeddings else 0} for {len(documents)} documents")
                        return []
                except Exception as e:
                    logger.warning(f"Error using embeddings for reranking: {str(e)}")
                    # Return empty scores, will fall back to original ranking
                    return []
            else:
                logger.warning("Reranking client does not support embeddings, falling back to original ranking")
                return []
            
            # Calculate cosine similarity between query and each document
            scores = []
            for doc_embedding in doc_embeddings:
                # Normalize embeddings
                query_norm = sum(x*x for x in query_embedding) ** 0.5
                doc_norm = sum(x*x for x in doc_embedding) ** 0.5
                
                if query_norm == 0 or doc_norm == 0:
                    scores.append(0.0)
                    continue
                
                # Calculate dot product
                dot_product = sum(q*d for q, d in zip(query_embedding, doc_embedding))
                
                # Calculate cosine similarity
                similarity = dot_product / (query_norm * doc_norm)
                scores.append(similarity)
            
            return scores
        except Exception as e:
            logger.error(f"Error during document reranking: {str(e)}")
            return []
    
    async def get_available_models(self) -> tuple[List[str], List[str]]:
        """
        Get available models for the current provider.
        
        Returns:
            Tuple of (chat_models, embedding_models)
        """
        chat_models = []
        embedding_models = []
        
        try:
            # OpenAI models
            if self.provider == "openai":
                chat_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
                embedding_models = ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
            
            # Ollama models - use the client to get actual models
            elif self.provider == "ollama":
                if hasattr(self.chat_client, 'list_models'):
                    models = await self.chat_client.list_models()
                    # For Ollama, all models can be used for both chat and embeddings
                    chat_models = models
                    embedding_models = models
                else:
                    # Fallback if list_models is not implemented
                    chat_models = ["llama2", "llama3", "mistral", "mixtral"]
                    embedding_models = ["llama2", "llama3"]
            
            # Anthropic models
            elif self.provider == "anthropic":
                # Provide a more comprehensive list of recent models
                chat_models = [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                    "claude-2.1",
                    "claude-2.0",
                    "claude-instant-1.2"
                ]
                embedding_models = [] # Anthropic client doesn't handle embeddings directly
            
            # Google Gemini models
            elif self.provider == "google_gemini":
                try:
                    # Configure API key before listing models. Prioritize direct key, then active config.
                    api_key_to_use = self.api_key
                    if not api_key_to_use:
                        # Attempt to get key from active config if not passed directly
                        active_config = LLMConfigService.get_active_config(self.db)
                        if active_config and active_config.api_key:
                            api_key_to_use = active_config.api_key
                    
                    if api_key_to_use:
                        genai.configure(api_key=api_key_to_use)
                    else:
                        logger.warning("Google Gemini API key not configured. Cannot list models.")
                        raise ValueError("Google Gemini API key required to list models.")

                    all_models = genai.list_models()
                    for model in all_models:
                        # Check supported methods for chat ('generateContent') and embedding ('embedContent')
                        if 'generateContent' in model.supported_generation_methods:
                            chat_models.append(model.name)
                        if 'embedContent' in model.supported_generation_methods:
                             # Exclude the 'aqa' model which is specialized
                             if 'aqa' not in model.name:
                                embedding_models.append(model.name)
                    
                    # Sort models for consistency
                    chat_models.sort()
                    embedding_models.sort()
                    
                except Exception as e:
                    logger.error(f"Failed to list Google Gemini models dynamically: {e}. Using fallback list.")
                    # Fallback list based on user-provided image and common models
                    chat_models = [
                        "gemini-1.5-flash-002",
                        "gemini-1.5-flash-exp-0827",
                        "gemini-2.0-flash-001",
                        "gemini-2.0-flash-exp",
                        "gemini-2.0-flash-lite-preview-02-05",
                        "gemini-2.0-flash-thinking-exp-01-21",
                        "gemini-2.0-flash-thinking-exp-1219",
                        "gemini-2.0-pro-exp-02-05",
                        "gemini-2.5-pro-exp-03-25",
                        "models/gemini-pro", # Standard model
                        "models/gemini-1.5-pro-latest", # Standard model
                    ]
                    embedding_models = ["models/embedding-001"] # Standard embedding model
                    chat_models.sort() # Keep it sorted

            # OpenRouter models - fetch from API and group by provider
            elif self.provider == "openrouter":
                if hasattr(self.chat_client, 'list_models'):
                    try:
                        models = await self.chat_client.list_models()
                        logger.info(f"Received {len(models)} models from OpenRouter")
                        logger.info(f"OpenRouter models type: {type(models)}")
                        logger.info(f"First few OpenRouter models: {models[:3] if len(models) > 3 else models}")
                        
                        # Group models by provider prefix
                        model_groups = {}
                        for model in models:
                            logger.info(f"Processing model: {model}")
                            if model.get("id"):
                                provider = model["id"].split("/")[0] if "/" in model["id"] else "other"
                                if provider not in model_groups:
                                    model_groups[provider] = []
                                model_groups[provider].append(model["id"])
                        
                        # Sort groups and models alphabetically
                        chat_models = []
                        for provider in sorted(model_groups.keys()):
                            chat_models.extend(sorted(model_groups[provider]))
                        
                        logger.info(f"Processed {len(chat_models)} chat models from OpenRouter")
                        logger.info(f"Final OpenRouter chat models: {chat_models}")
                        
                        # Embedding models (OpenRouter mostly uses OpenAI embeddings)
                        embedding_models = ["openai/text-embedding-ada-002"]
                    except Exception as e:
                        logger.error(f"Error processing OpenRouter models: {str(e)}")
                        # Fallback if there's an error
                        chat_models = ["openai/gpt-3.5-turbo", "openai/gpt-4", "anthropic/claude-2"]
                        embedding_models = ["openai/text-embedding-ada-002"]
                else:
                    # Fallback if list_models is not implemented
                    chat_models = ["openai/gpt-3.5-turbo", "openai/gpt-4", "anthropic/claude-2"]
                    embedding_models = ["openai/text-embedding-ada-002"]
            
            # Deepseek models
            elif self.provider == "deepseek":
                chat_models = ["deepseek-chat", "deepseek-coder"]
                embedding_models = ["deepseek-embedding"]
            
            return chat_models, embedding_models
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return [], []