import time
import logging
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.llm.base import LLMClient
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
if settings.LLM_DEBUG_LOGGING:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# Define retry mechanism for Google API calls (common transient errors)
retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((
        google_exceptions.ServerError,
        google_exceptions.ServiceUnavailable,
        google_exceptions.TooManyRequests,
        google_exceptions.ResourceExhausted, # Can sometimes be transient
    )),
    reraise=True
)

class GoogleGeminiClient(LLMClient):
    """
    Client for interacting with the Google Gemini API.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None, # Gemini doesn't use base_url
        embedding_model: Optional[str] = None
    ):
        # Use a default embedding model if not provided, specific to Gemini
        default_embedding_model = "models/embedding-001"
        effective_embedding_model = embedding_model or default_embedding_model
        
        super().__init__(model=model, api_key=api_key, base_url=base_url, embedding_model=effective_embedding_model)
        
        if not self.api_key:
            raise ValueError("Google Gemini API key is required.")
        
        genai.configure(api_key=self.api_key)
        
        # Verify the chat model exists
        try:
            self.chat_model_instance = genai.GenerativeModel(self.model)
            logger.info(f"Google Gemini client initialized with chat model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Gemini chat model '{self.model}': {e}", exc_info=True)
            raise ValueError(f"Invalid Google Gemini chat model specified: {self.model}") from e

        # Verify the embedding model exists
        try:
            # Check if embedding model is valid by trying to get info (no direct instance needed for embeddings API)
            genai.get_model(self.embedding_model)
            logger.info(f"Using Google Gemini embedding model: {self.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to validate Google Gemini embedding model '{self.embedding_model}': {e}", exc_info=True)
            # Fallback or raise error? Let's raise for clarity.
            raise ValueError(f"Invalid Google Gemini embedding model specified: {self.embedding_model}") from e
            
        if self.base_url:
            logger.warning("base_url is provided but not typically used by the Google Gemini client.")


    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Converts standard message format to Gemini's format."""
        gemini_messages = []
        
        # Handle system prompt if provided (Gemini prefers it as the first message or part of the first user message)
        if system_prompt:
             # Prepend system prompt as a separate 'user' message if no user message exists yet,
             # or combine with the first user message if it exists.
             if not messages or messages[0].get("role") != "user":
                 gemini_messages.append({'role': 'user', 'parts': [system_prompt]})
             else:
                 # Combine with the first user message
                 first_user_message_content = f"{system_prompt}\n\n{messages[0].get('content', '')}"
                 gemini_messages.append({'role': 'user', 'parts': [first_user_message_content]})
                 messages = messages[1:] # Remove the first message as it's now combined
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not role or not content:
                continue

            # Gemini uses 'user' and 'model' roles
            gemini_role = "user" if role == "user" else "model"
            
            # Ensure alternating roles if necessary (Gemini can be strict)
            if gemini_messages and gemini_messages[-1]['role'] == gemini_role:
                # If consecutive messages have the same role, merge content or handle appropriately
                # For simplicity, let's just append. Gemini might handle this, or we might need refinement.
                logger.warning(f"Consecutive messages with role '{gemini_role}'. Appending content.")
                # Or, potentially merge: gemini_messages[-1]['parts'].append(content)
                gemini_messages.append({'role': gemini_role, 'parts': [content]})
            else:
                 gemini_messages.append({'role': gemini_role, 'parts': [content]})
                 
        return gemini_messages

    @retry_decorator
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None, # Gemini uses max_output_tokens
        stream: bool = False,
        system_prompt: Optional[str] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate a response from the Google Gemini model.

        Args:
            messages: List of messages.
            temperature: Temperature for generation.
            max_tokens: Maximum number of tokens to generate (maps to max_output_tokens).
            stream: Whether to stream the response.
            system_prompt: System prompt to guide the model.

        Returns:
            Response dictionary or an async generator for streaming.
        """
        start_time = time.time()
        gemini_messages = self._convert_messages_to_gemini_format(messages, system_prompt)

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            # top_p, top_k can be added if needed
            max_output_tokens=max_tokens
        )

        request_params = {
            "contents": gemini_messages,
            "generation_config": generation_config,
            "stream": stream
        }
        
        logger.debug(f"Google Gemini request params: {request_params}")

        try:
            if stream:
                return self._generate_stream(request_params, start_time)
            else:
                response = await self.chat_model_instance.generate_content_async(**request_params)
                logger.debug(f"Google Gemini non-stream response: {response}")

                # Extract usage and content
                prompt_tokens = response.usage_metadata.prompt_token_count
                completion_tokens = response.usage_metadata.candidates_token_count
                total_tokens = response.usage_metadata.total_token_count
                tokens_per_second = self.calculate_tokens_per_second(start_time, completion_tokens)
                finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
                
                # Handle potential lack of content (e.g., safety settings block)
                content = ""
                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    content = response.candidates[0].content.parts[0].text
                elif response.prompt_feedback.block_reason:
                     content = f"Response blocked due to: {response.prompt_feedback.block_reason.name}"
                     logger.warning(f"Gemini response blocked: {response.prompt_feedback.block_reason.name}")
                     finish_reason = "BLOCKED" # Override finish reason

                return {
                    "role": "assistant",
                    "content": content,
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                    "tokens_per_second": tokens_per_second,
                    "finish_reason": finish_reason
                }
        except (google_exceptions.GoogleAPIError, ValueError) as e:
            logger.error(f"Google Gemini API error: {e}", exc_info=True)
            raise # Re-raise after logging and retries
        except Exception as e:
             logger.error(f"Unexpected error during Google Gemini generation: {e}", exc_info=True)
             raise

    async def _generate_stream(
        self,
        request_params: Dict[str, Any],
        start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Helper for generating streaming response."""
        completion_tokens = 0
        prompt_tokens = 0
        total_tokens = 0
        finish_reason = None
        
        try:
            response_stream = await self.chat_model_instance.generate_content_async(**request_params)
            
            # Yield start message (Gemini stream doesn't have an explicit start event type)
            # We can get prompt tokens from the first chunk's usage metadata if available
            first_chunk_processed = False
            
            async for chunk in response_stream:
                logger.debug(f"Google Gemini stream chunk: {chunk}")
                
                # Extract usage if available (often in the first or last chunk)
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    if chunk.usage_metadata.prompt_token_count > 0 and not first_chunk_processed:
                         prompt_tokens = chunk.usage_metadata.prompt_token_count
                         yield {
                             "type": "start",
                             "role": "assistant",
                             "system_fingerprint": None, # Gemini doesn't provide this
                             "usage": {"prompt_tokens": prompt_tokens}
                         }
                         first_chunk_processed = True
                    # Update completion/total tokens if present (usually at the end)
                    if chunk.usage_metadata.candidates_token_count > 0:
                         completion_tokens = chunk.usage_metadata.candidates_token_count
                    if chunk.usage_metadata.total_token_count > 0:
                         total_tokens = chunk.usage_metadata.total_token_count

                # Extract content delta
                delta_content = ""
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    delta_content = chunk.candidates[0].content.parts[0].text
                    # completion_tokens += 1 # Rough estimate if metadata isn't available per chunk
                
                # Check for finish reason
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    finish_reason = chunk.candidates[0].finish_reason.name

                # Check for blocking
                if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                     block_reason_name = chunk.prompt_feedback.block_reason.name
                     logger.warning(f"Gemini stream blocked: {block_reason_name}")
                     yield {
                         "type": "delta",
                         "role": "assistant",
                         "content": f"\n[STREAM BLOCKED DUE TO: {block_reason_name}]",
                     }
                     finish_reason = "BLOCKED" # Override finish reason
                     break # Stop processing stream if blocked

                if delta_content:
                    yield {
                        "type": "delta",
                        "role": "assistant",
                        "content": delta_content,
                    }

            # Ensure start event is sent if no usage metadata was found in the stream initially
            if not first_chunk_processed:
                 yield {
                     "type": "start",
                     "role": "assistant",
                     "system_fingerprint": None,
                     "usage": {"prompt_tokens": 0} # Unknown prompt tokens
                 }
                 logger.warning("Could not determine prompt tokens from Gemini stream.")

            # Yield final message after stream ends
            # Use final known token counts, calculate total if needed
            if total_tokens == 0 and prompt_tokens > 0 and completion_tokens > 0:
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
                "finish_reason": finish_reason or "UNKNOWN"
            }

        except (google_exceptions.GoogleAPIError, ValueError) as e:
            logger.error(f"Google Gemini API stream error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error during Google Gemini stream: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": "An unexpected error occurred during streaming."
            }

    @retry_decorator
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts using the configured Gemini embedding model.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        logger.debug(f"Requesting Gemini embeddings for {len(texts)} texts using model {self.embedding_model}")
        start_time = time.time()
        try:
            # Note: The async version of embed_content isn't directly available in the library as of some versions.
            # We might need to run the sync version in a thread pool executor if performance becomes an issue.
            # For now, using the sync version directly. Consider using asyncio.to_thread if needed.
            
            # Gemini API might have limits on batch size, handle potential splitting if needed
            # Example: Max 100 texts per call for 'models/embedding-001'
            batch_size = 100 
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                response = genai.embed_content(
                    model=self.embedding_model,
                    content=batch_texts,
                    task_type="retrieve_document" # Or "retrieval_query", "semantic_similarity", "classification"
                )
                all_embeddings.extend(response['embedding'])
                
            elapsed_time = time.time() - start_time
            logger.info(f"Generated Gemini embeddings for {len(texts)} texts in {elapsed_time:.2f} seconds.")
            return all_embeddings
            
        except (google_exceptions.GoogleAPIError, ValueError) as e:
            logger.error(f"Google Gemini embedding error: {e}", exc_info=True)
            raise
        except Exception as e:
             logger.error(f"Unexpected error during Google Gemini embedding: {e}", exc_info=True)
             raise