import time
import logging
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from anthropic import AsyncAnthropic, APIError, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.llm.base import LLMClient
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
if settings.LLM_DEBUG_LOGGING:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# Define retry mechanism for Anthropic API calls
retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((APIError, APIStatusError)),
    reraise=True
)

class AnthropicClient(LLMClient):
    """
    Client for interacting with the Anthropic API (Claude models).
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None, # Anthropic doesn't typically use base_url
        embedding_model: Optional[str] = None
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, embedding_model=embedding_model)
        if not self.api_key:
            raise ValueError("Anthropic API key is required.")
        
        # Base URL is not typically used for Anthropic's main API, but allow if provided
        client_args = {"api_key": self.api_key}
        if self.base_url:
            client_args["base_url"] = self.base_url
            
        self.async_client = AsyncAnthropic(**client_args)
        logger.info(f"Anthropic client initialized with model: {self.model}")
        if self.base_url:
             logger.info(f"Using custom Anthropic base URL: {self.base_url}")

    @retry_decorator
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1024, # Default for Claude
        stream: bool = False,
        system_prompt: Optional[str] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate a response from the Anthropic model.

        Args:
            messages: List of messages (user/assistant roles).
            temperature: Temperature for generation.
            max_tokens: Maximum number of tokens to generate.
            stream: Whether to stream the response.
            system_prompt: The system prompt to use (required by Anthropic).

        Returns:
            Response dictionary or an async generator for streaming.
        """
        start_time = time.time()
        
        if not system_prompt:
             # Use default if not provided, but log a warning as it's important for Claude
            system_prompt = settings.DEFAULT_SYSTEM_PROMPT
            logger.warning("System prompt not explicitly provided for Anthropic, using default.")

        # Filter out system messages from the main list if present, use the dedicated param
        conversation_messages = [msg for msg in messages if msg.get("role") != "system"]

        request_params = {
            "model": self.model,
            "messages": conversation_messages,
            "system": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens or 1024, # Ensure a default if None
        }
        
        logger.debug(f"Anthropic request params: {request_params}")

        try:
            if stream:
                return self._generate_stream(request_params, start_time)
            else:
                response = await self.async_client.messages.create(**request_params)
                
                logger.debug(f"Anthropic non-stream response: {response}")

                total_tokens = response.usage.input_tokens + response.usage.output_tokens
                tokens_per_second = self.calculate_tokens_per_second(start_time, response.usage.output_tokens)
                
                return {
                    "role": "assistant",
                    "content": response.content[0].text,
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        "total_tokens": total_tokens,
                    },
                    "tokens_per_second": tokens_per_second,
                    "finish_reason": response.stop_reason
                }
        except (APIError, APIStatusError) as e:
            logger.error(f"Anthropic API error: {e}", exc_info=True)
            raise  # Re-raise after logging and retries

    async def _generate_stream(
        self,
        request_params: Dict[str, Any],
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Helper for generating streaming response."""
        completion_tokens = 0
        prompt_tokens = 0 # Anthropic sends usage stats at the end or in message_start
        finish_reason = None
        
        try:
            async with self.async_client.messages.stream(**request_params) as stream_obj:
                async for event in stream_obj:
                    logger.debug(f"Anthropic stream event: {event.type}")
                    
                    if event.type == "message_start":
                        prompt_tokens = event.message.usage.input_tokens
                        yield {
                            "type": "start",
                            "role": "assistant",
                            "system_fingerprint": None, # Anthropic doesn't provide this
                            "usage": {"prompt_tokens": prompt_tokens}
                        }
                    elif event.type == "content_block_delta":
                        completion_tokens += 1 # Rough estimate, Anthropic doesn't give token count per delta
                        yield {
                            "type": "delta",
                            "role": "assistant",
                            "content": event.delta.text,
                        }
                    elif event.type == "message_delta":
                         # Contains final usage stats sometimes
                        if hasattr(event, 'usage') and hasattr(event.usage, 'output_tokens'):
                            completion_tokens = event.usage.output_tokens # Update with actual count
                        finish_reason = event.delta.stop_reason
                    elif event.type == "message_stop":
                        # Final event, get the complete message to extract final usage
                        final_message = await stream_obj.get_final_message()
                        if final_message and final_message.usage:
                             prompt_tokens = final_message.usage.input_tokens
                             completion_tokens = final_message.usage.output_tokens
                        
                # Yield final message after stream ends
                # Ensure total_tokens is calculated correctly using potentially updated completion_tokens
                total_tokens = prompt_tokens + completion_tokens
                tokens_per_second = self.calculate_tokens_per_second(start_time, completion_tokens)
                
                yield {
                    "type": "end",
                    "role": "assistant",
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                    "tokens_per_second": tokens_per_second,
                    "finish_reason": finish_reason
                }

        except (APIError, APIStatusError) as e:
            logger.error(f"Anthropic API stream error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error during Anthropic stream: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": "An unexpected error occurred during streaming."
            }


    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts.
        NOTE: Anthropic's primary Python client library does not support embeddings directly.
              This method raises NotImplementedError. Configure a different embedding_provider.
        """
        logger.warning("Anthropic client does not support embeddings directly. Configure a different embedding_provider.")
        raise NotImplementedError("Anthropic client does not support embeddings directly.")