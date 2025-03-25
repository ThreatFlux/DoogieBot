from typing import List, Dict, Any, Optional, Union, AsyncGenerator
import aiohttp
import json
import time
import logging
import asyncio

from app.llm.base import LLMClient
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenRouterClient(LLMClient):
    """
    Client for OpenRouter API.
    """
    
    def __init__(
        self,
        model: str = "openai/gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = "https://openrouter.ai/api/v1",
        embedding_model: Optional[str] = None
    ):
        """
        Initialize the OpenRouter client.
        
        Args:
            model: Model name (e.g. "openai/gpt-3.5-turbo")
            api_key: OpenRouter API key
            base_url: Base URL for API
            embedding_model: Model to use for embeddings (if different from chat model)
        """
        super().__init__(model, api_key, base_url, embedding_model)
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Ensure base_url is set to default if None
        if self.base_url is None:
            self.base_url = "https://openrouter.ai/api/v1"
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate a response from OpenRouter.
        
        Args:
            messages: List of messages in the conversation
            temperature: Temperature for generation
            max_tokens: Maximum number of tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Response from OpenRouter or an async generator for streaming
        """
        # Ensure base_url is set
        if not self.base_url or not self.base_url.startswith("http"):
            self.base_url = "https://openrouter.ai/api/v1"
            
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.OPENROUTER_REFERRER or "https://github.com/rooveterinary/doogie",
            "X-Title": settings.OPENROUTER_APP_TITLE or "Doogie"
        }
        
        # Log the messages for debugging
        logger.info(f"Sending {len(messages)} messages to OpenRouter. First message role: {messages[0]['role'] if messages else 'none'}")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        # Log the full payload for debugging if LLM_DEBUG_LOGGING is enabled
        if settings.LLM_DEBUG_LOGGING:
            logger.info("Full OpenRouter request payload (LLM_DEBUG_LOGGING enabled):")
            try:
                # Log each message separately to avoid log size limitations
                for i, msg in enumerate(messages):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    
                    # For system messages that might contain RAG context, log in detail
                    if role == 'system':
                        logger.info(f"Message {i} - Role: {role}")
                        # Log the system message in chunks to avoid log size limitations
                        content_chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                        for j, chunk in enumerate(content_chunks):
                            logger.info(f"System message chunk {j}: {chunk}")
                    else:
                        # For non-system messages, log a preview
                        content_preview = content[:200] + "..." if len(content) > 200 else content
                        logger.info(f"Message {i} - Role: {role}, Content preview: {content_preview}")
                
                # Log other payload parameters
                logger.info(f"Model: {self.model}, Temperature: {temperature}, Stream: {stream}")
            except Exception as e:
                logger.error(f"Error logging payload: {str(e)}")
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        start_time = time.time()
        
        if stream:
            return self._stream_response(url, headers, payload, start_time)
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error: {error_text}")
                        raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # Calculate tokens per second
                    tokens = result.get("usage", {}).get("completion_tokens", 0)
                    tokens_per_second = self.calculate_tokens_per_second(start_time, tokens)
                    
                    return {
                        "content": result["choices"][0]["message"]["content"],
                        "model": self.model,
                        "provider": "openrouter",
                        "tokens": tokens,
                        "tokens_per_second": tokens_per_second
                    }
    
    async def _stream_response(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from OpenRouter.
        
        Args:
            url: API URL
            headers: Request headers
            payload: Request payload
            start_time: Start time for calculating tokens per second
            
        Yields:
            Chunks of the response
        """
        # Ensure URL is valid
        if not url.startswith("http"):
            # If base_url is not set or invalid, use the default
            if not self.base_url or not self.base_url.startswith("http"):
                self.base_url = "https://openrouter.ai/api/v1"
            
            # If url is just a path, prepend the base_url
            if url.startswith("/"):
                url = f"{self.base_url}{url}"
            else:
                url = f"{self.base_url}/{url}"
        
        logger.debug(f"Starting OpenRouter streaming request to {url}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {error_text}")
                    raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                
                logger.debug(f"OpenRouter streaming connection established with status {response.status}")
                
                # Initialize variables for streaming
                content = ""
                token_count = 0
                chunk_count = 0
                
                # Process the stream
                logger.debug(f"Starting to process OpenRouter stream")
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    # Skip empty lines or [DONE]
                    if not line or line == "data: [DONE]":
                        if line == "data: [DONE]":
                            logger.debug("Received [DONE] from OpenRouter stream")
                        continue
                    
                    # Remove "data: " prefix
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    try:
                        data = json.loads(line)
                        
                        # Extract delta content
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        delta_content = delta.get("content", "")
                        
                        if delta_content:
                            chunk_count += 1
                            content += delta_content
                            token_count += 1  # Approximate token count
                            
                            # Log every 10th chunk to avoid excessive logging
                            if chunk_count % 10 == 0:
                                logger.debug(f"Received chunk {chunk_count} from OpenRouter: '{delta_content}' (total: {len(content)} chars)")
                            
                            # Calculate tokens per second
                            tokens_per_second = self.calculate_tokens_per_second(start_time, token_count)
                            
                            logger.debug(f"Yielding chunk {chunk_count} at {time.time()}")
                            
                            # Yield immediately without any delay
                            yield {
                                "content": content,
                                "model": self.model,
                                "provider": "openrouter",
                                "tokens": token_count,
                                "tokens_per_second": tokens_per_second,
                                "done": False,
                                "timestamp": time.time()
                            }
                            
                            # Ensure the chunk is sent immediately
                            await asyncio.sleep(0)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse line: {line}")
                
                logger.debug(f"OpenRouter stream complete, yielding final chunk with done=True")
                # Final yield with done=True
                tokens_per_second = self.calculate_tokens_per_second(start_time, token_count)
                yield {
                    "content": content,
                    "model": self.model,
                    "provider": "openrouter",
                    "tokens": token_count,
                    "tokens_per_second": tokens_per_second,
                    "done": True
                }
                logger.debug(f"OpenRouter streaming complete, yielded {chunk_count} chunks")
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts using OpenRouter.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # OpenRouter doesn't currently support embeddings, so we'll use OpenAI's embeddings
        # through OpenRouter by specifying an OpenAI model
        
        # Ensure base_url is set
        if not self.base_url or not self.base_url.startswith("http"):
            self.base_url = "https://openrouter.ai/api/v1"
            
        url = f"{self.base_url}/embeddings"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.OPENROUTER_REFERRER or "https://github.com/rooveterinary/doogie",
            "X-Title": settings.OPENROUTER_APP_TITLE or "Doogie"
        }
        
        # Use the instance's embedding model or fall back to a default
        embedding_model = self.embedding_model
        if not embedding_model:
            embedding_model = "text-embedding-ada-002"  # Default OpenAI embedding model
        
        # Log the embedding request
        logger.info(f"Generating embeddings for {len(texts)} texts using OpenRouter model: {embedding_model}")
        
        try:
            payload = {
                "model": embedding_model,
                "input": texts
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error: {error_text}")
                        # Return empty embeddings instead of raising an exception
                        return [[0.0] * 1536 for _ in range(len(texts))]  # OpenAI embeddings are typically 1536 dimensions
                    
                    result = await response.json()
                    
                    # Extract embeddings
                    embeddings = [item["embedding"] for item in result["data"]]
                    
                    logger.info(f"Successfully generated {len(embeddings)} embeddings with OpenRouter")
                    if embeddings:
                        logger.debug(f"Embedding dimensions: {len(embeddings[0])}")
                    
                    return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings with OpenRouter: {str(e)}")
            logger.exception("Detailed embedding generation error:")
            # Return empty embeddings
            return [[0.0] * 1536 for _ in range(len(texts))]  # OpenAI embeddings are typically 1536 dimensions