from typing import Dict, Any, Optional, Type, Union, Tuple
import logging

from app.llm.base import LLMClient
from app.llm.openai_client import OpenAIClient
from app.llm.ollama_client import OllamaClient
from app.llm.openrouter_client import OpenRouterClient
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import other LLM clients as needed
# Uncomment these when the actual client implementations are available
# from app.llm.anthropic_client import AnthropicClient
# from app.llm.openrouter_client import OpenRouterClient
# from app.llm.deepseek_client import DeepseekClient
# from app.llm.lmstudio_client import LMStudioClient

class LLMFactory:
    """
    Factory for creating LLM clients.
    """
    
    # Registry of LLM providers and their client classes
    _registry: Dict[str, Type[LLMClient]] = {
        "openai": OpenAIClient,
        "ollama": OllamaClient,
        # These are placeholders - they will use OpenAIClient until proper implementations are available
        "anthropic": OpenAIClient,  # Placeholder using OpenAIClient
        "openrouter": OpenRouterClient,
        # "deepseek": DeepseekClient,
        # "lmstudio": LMStudioClient,
    }
    
    @classmethod
    def create_separate_clients(
        cls,
        chat_config: Dict[str, Any],
        embedding_config: Dict[str, Any]
    ) -> Tuple[LLMClient, LLMClient]:
        """
        Create separate chat and embedding clients from their respective configs.
        
        Args:
            chat_config: Dictionary containing chat provider configuration
            embedding_config: Dictionary containing embedding provider configuration
            
        Returns:
            Tuple of (chat_client, embedding_client)
            
        Raises:
            ValueError: If any provider is not supported
        """
        chat_provider = chat_config.get('provider', '').lower()
        embedding_provider = embedding_config.get('provider', '').lower()
        
        # Check if providers are supported
        if chat_provider not in cls._registry:
            raise ValueError(f"Unsupported chat LLM provider: {chat_provider}")
        if embedding_provider not in cls._registry:
            raise ValueError(f"Unsupported embedding LLM provider: {embedding_provider}")
            
        try:
            # Create chat client
            chat_client = cls._create_single_client(
                provider=chat_provider,
                model=chat_config.get('model'),
                api_key=chat_config.get('api_key'),
                base_url=chat_config.get('base_url')
            )
            
            # Create embedding client
            embedding_client = cls._create_single_client(
                provider=embedding_provider,
                model=embedding_config.get('model'),
                api_key=embedding_config.get('api_key'),
                base_url=embedding_config.get('base_url')
            )
            
            return (chat_client, embedding_client)
            
        except Exception as e:
            logger.error(f"Error creating separate clients: {str(e)}")
            raise

    @classmethod
    def _create_single_client(
        cls,
        provider: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> LLMClient:
        """
        Internal method to create a single client instance.
        """
        provider = provider.lower()
        if provider not in cls._registry:
            raise ValueError(f"Unsupported provider: {provider}")
            
        if not model:
            model = cls._get_default_model(provider)
            
        # Set provider-specific base URLs
        if provider == "ollama":
            base_url = base_url if base_url else settings.OLLAMA_BASE_URL
        elif provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
            
        client_class = cls._registry[provider]
        client = client_class(
            model=model,
            api_key=api_key,
            base_url=base_url
        )
        logger.info(f"Created {provider} client with model {model}")
        return client

    @classmethod
    def create_client(
        cls,
        provider: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_provider: Optional[str] = None
    ) -> Union[LLMClient, Tuple[LLMClient, LLMClient]]:
        """
        Create an LLM client for the specified provider (legacy method).
        If embedding_provider is different from provider, returns a tuple of (chat_client, embedding_client).
        
        Args:
            provider: Chat LLM provider name
            model: Chat model name (optional, uses default if not provided)
            api_key: API key (optional, uses default if not provided)
            base_url: Base URL for API (optional, uses default if not provided)
            embedding_model: Embedding model name (optional)
            embedding_provider: Embedding provider name (optional, uses chat provider if not provided)
            
        Returns:
            LLM client instance or tuple of (chat_client, embedding_client)
            
        Raises:
            ValueError: If any provider is not supported
        """
        # Convert providers to lowercase for case-insensitive matching
        provider = provider.lower()
        embedding_provider = (embedding_provider or provider).lower()
        
        # Check if providers are supported
        if provider not in cls._registry:
            raise ValueError(f"Unsupported chat LLM provider: {provider}")
        if embedding_provider not in cls._registry:
            raise ValueError(f"Unsupported embedding LLM provider: {embedding_provider}")
        
        # Use default models if not provided
        if not model:
            model = cls._get_default_model(provider)
        if not embedding_model:
            embedding_model = cls._get_default_model(embedding_provider)
        
        try:
            # Create chat client
            chat_client = cls._create_single_client(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url
            )
            
            # If same provider, return single client with embedding model set
            if provider == embedding_provider:
                chat_client.embedding_model = embedding_model
                logger.info(f"Using same client for embeddings with model {embedding_model}")
                return chat_client
                
            # Create separate embedding client
            embedding_client = cls._create_single_client(
                provider=embedding_provider,
                model=embedding_model,
                api_key=api_key,
                base_url=base_url
            )
            
            return (chat_client, embedding_client)
            
        except Exception as e:
            logger.error(f"Error creating LLM client(s): {str(e)}")
            raise
            
        # Convert providers to lowercase for case-insensitive matching
        provider = provider.lower()
        embedding_provider = (embedding_provider or provider).lower()
        
        # Check if providers are supported
        if provider not in cls._registry:
            raise ValueError(f"Unsupported chat LLM provider: {provider}")
        if embedding_provider not in cls._registry:
            raise ValueError(f"Unsupported embedding LLM provider: {embedding_provider}")
        
        # Get client classes
        chat_client_class = cls._registry[provider]
        embedding_client_class = cls._registry[embedding_provider]
        
        # Use default models if not provided
        if not model:
            model = cls._get_default_model(provider)
        if not embedding_model:
            embedding_model = cls._get_default_model(embedding_provider)
        
        try:
            # Set provider-specific base URLs - always use the correct base URL for each provider
            if provider == "ollama":
                # Ollama always needs its specific base URL
                chat_base_url = base_url if base_url else settings.OLLAMA_BASE_URL
            elif provider == "openai":
                # OpenAI uses default API URL if not specified
                chat_base_url = None
            elif provider == "openrouter":
                # OpenRouter always uses its specific API URL
                chat_base_url = "https://openrouter.ai/api/v1"
            else:
                # For other providers, use the provided base URL
                chat_base_url = base_url
            
            # Create chat client with provider-specific base URL
            chat_client = chat_client_class(
                model=model,
                api_key=api_key,
                base_url=chat_base_url
            )
            logger.info(f"Created {provider} chat client with model {model} and base URL {chat_base_url}")
            
            # If same provider, return single client
            if provider == embedding_provider:
                chat_client.embedding_model = embedding_model
                logger.info(f"Using same client for embeddings with model {embedding_model}")
                return chat_client
            
            # Set provider-specific base URL for embedding client - always use the correct base URL
            if embedding_provider == "ollama":
                # For Ollama, use the provided base URL (from the database) or fall back to the default
                embedding_base_url = base_url if base_url else settings.OLLAMA_BASE_URL
                logger.info(f"Using Ollama base URL for embeddings: {embedding_base_url}")
            elif embedding_provider == "openai":
                # OpenAI uses default API URL if not specified
                embedding_base_url = None
            elif embedding_provider == "openrouter":
                # OpenRouter always uses its specific API URL
                embedding_base_url = "https://openrouter.ai/api/v1"
            else:
                # For other providers, use the provided base URL
                embedding_base_url = base_url
            
            logger.info(f"Creating embedding client with provider {embedding_provider}, model {embedding_model}, and base URL {embedding_base_url}")
            
            embedding_client = embedding_client_class(
                model=embedding_model,
                api_key=api_key,
                base_url=embedding_base_url
            )
            logger.info(f"Created separate {embedding_provider} embedding client with model {embedding_model}")
            return (chat_client, embedding_client)
            
        except Exception as e:
            logger.error(f"Error creating LLM client(s): {str(e)}")
            raise
    
    @classmethod
    def _get_default_model(cls, provider: str) -> str:
        """
        Get the default model for a provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            Default model name
        """
        if provider == "openai":
            return settings.DEFAULT_CHAT_MODEL
        elif provider == "ollama":
            return "llama2"
        elif provider == "anthropic":
            return "claude-2"
        elif provider == "openrouter":
            return "openai/gpt-3.5-turbo"
        elif provider == "deepseek":
            return "deepseek-chat"
        elif provider == "lmstudio":
            return "lmstudio-model"
        else:
            return "gpt-3.5-turbo"  # Default fallback
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Any]:
        """
        Get a list of available LLM providers.
        
        Returns:
            Dictionary of available providers and their status
        """
        providers = {}
        
        # Check OpenAI
        providers["openai"] = {
            "available": bool(settings.OPENAI_API_KEY),
            "default_model": settings.DEFAULT_CHAT_MODEL,
            "requires_api_key": True,
            "requires_base_url": False
        }
        
        # Check Ollama
        providers["ollama"] = {
            "available": bool(settings.OLLAMA_BASE_URL),
            "default_model": "llama2",
            "requires_api_key": False,
            "requires_base_url": True
        }
        
        # Check Anthropic
        providers["anthropic"] = {
            "available": bool(settings.ANTHROPIC_API_KEY),
            "default_model": "claude-2",
            "requires_api_key": True,
            "requires_base_url": False
        }
        
        # Check OpenRouter
        providers["openrouter"] = {
            "available": bool(settings.OPENROUTER_API_KEY),
            "default_model": "openai/gpt-3.5-turbo",
            "requires_api_key": True,
            "requires_base_url": False
        }
        
        # Check other providers as they are implemented
        # providers["deepseek"] = {
        #     "available": bool(settings.DEEPSEEK_API_KEY),
        #     "default_model": "deepseek-chat",
        #     "requires_api_key": True,
        #     "requires_base_url": False
        # }
        
        # providers["lmstudio"] = {
        #     "available": bool(settings.LM_STUDIO_BASE_URL),
        #     "default_model": "lmstudio-model",
        #     "requires_api_key": False,
        #     "requires_base_url": True
        # }
        
        return providers