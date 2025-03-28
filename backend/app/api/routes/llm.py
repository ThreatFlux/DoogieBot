from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio

from app.db.base import get_db
from app.models.user import User
from app.services.llm_service import LLMService
from app.services.llm_config import LLMConfigService
from app.services.embedding_config import EmbeddingConfigService
from app.services.reranking_config import RerankingConfigService
from app.schemas.llm import (
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    LLMProviderResponse,
    LLMProviderInfo,
    ModelsResponse
)
from app.schemas.embedding import (
    EmbeddingConfigCreate,
    EmbeddingConfigUpdate,
    EmbeddingConfigResponse
)
from app.schemas.reranking import (
    RerankingConfigCreate,
    RerankingConfigUpdate,
    RerankingConfigResponse
)
from app.utils.deps import get_current_user, get_current_admin_user
from app.core.config import settings

router = APIRouter()

@router.get("/providers", response_model=Dict[str, Any])
async def get_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get available LLM providers.
    """
    providers = LLMConfigService.get_available_providers(db)
    return providers

@router.get("/providers/{provider_id}/models", response_model=ModelsResponse)
async def get_provider_models(
    provider_id: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get available models for a specific provider.
    Requires API key for providers that need authentication.
    """
    try:
        # Create a temporary LLM service to get models
        llm_service = LLMService(
            db=db,
            provider=provider_id,
            api_key=api_key,
            base_url=base_url
        )
        
        # Get available models
        chat_models, embedding_models = await llm_service.get_available_models()
        
        return {
            "chat_models": chat_models,
            "embedding_models": embedding_models
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get models: {str(e)}"
        )

@router.post("/chat/{chat_id}")
async def chat(
    chat_id: str,
    message: str,
    use_rag: bool = True,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,  # Global system prompt for all providers
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stream: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Send a message to the LLM and get a response.
    Uses the active LLM configuration if no provider/model is specified.
    The system_prompt parameter is global and applies to all LLM providers.
    """
    # Create LLM service with optional overrides
    # If not provided, it will use the active configuration from the database
    llm_service = LLMService(
        db=db,
        provider=provider,
        model=model,
        system_prompt=system_prompt
    )
    
    # Handle streaming response
    if stream:
        return StreamingResponse(
            stream_chat_response(llm_service, chat_id, message, use_rag, temperature, max_tokens),
            media_type="text/event-stream"
        )
    else:
        # Get response from LLM
        response = await llm_service.chat(
            chat_id=chat_id,
            user_message=message,
            use_rag=use_rag,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )
        
        return response

async def stream_chat_response(
    llm_service: LLMService,
    chat_id: str,
    message: str,
    use_rag: bool,
    temperature: float,
    max_tokens: Optional[int]
):
    """
    Stream chat response as server-sent events.
    """
    try:
        # Get streaming response from LLM
        async for chunk in llm_service.chat(
            chat_id=chat_id,
            user_message=message,
            use_rag=use_rag,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        ):
            # Format as server-sent event
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Add a small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)
        
        # End of stream
        yield "data: [DONE]\n\n"
    except Exception as e:
        # Send error as event
        error_data = {
            "error": str(e),
            "done": True
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"

@router.post("/embeddings", response_model=List[List[float]])
async def get_embeddings(
    texts: List[str],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get embeddings for a list of texts.
    """
    # Use default provider if not specified
    provider = provider or settings.DEFAULT_LLM_PROVIDER
    
    # Create LLM service
    llm_service = LLMService(
        db=db,
        provider=provider,
        model=model
    )
    
    # Get embeddings
    embeddings = await llm_service.get_embeddings(texts)
    return embeddings

@router.post("/admin/config", response_model=LLMConfigResponse)
async def create_llm_config(
    config: LLMConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Create a new LLM configuration. Admin only.
    """
    db_config = LLMConfigService.create_config(db, config)
    return db_config

@router.put("/admin/config/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: str,
    config: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Update an existing LLM configuration. Admin only.
    """
    db_config = LLMConfigService.update_config(db, config_id, config)
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return db_config

@router.get("/admin/config", response_model=List[LLMConfigResponse])
async def get_all_llm_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get all LLM configurations. Admin only.
    """
    configs = LLMConfigService.get_all_configs(db)
    return configs

@router.get("/admin/config/active", response_model=LLMConfigResponse)
async def get_active_llm_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get the active LLM configuration. Admin only.
    """
    config = LLMConfigService.get_active_config(db)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active configuration found"
        )
    return config

@router.post("/admin/config/{config_id}/activate", response_model=LLMConfigResponse)
async def activate_llm_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Set an LLM configuration as active. Admin only.
    """
    config = LLMConfigService.set_active_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

@router.delete("/admin/config/{config_id}", response_model=Dict[str, Any])
async def delete_llm_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Delete an LLM configuration. Admin only.
    Cannot delete the active configuration.
    """
    try:
        success = LLMConfigService.delete_config(db, config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        return {"status": "success", "message": "Configuration deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
# Embedding Configuration Endpoints
# These endpoints are kept in the LLM router to maintain compatibility with the frontend
@router.post("/admin/embedding/config", response_model=EmbeddingConfigResponse)
async def create_embedding_config(
    config: EmbeddingConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Create a new embedding configuration. Admin only.
    """
    db_config = EmbeddingConfigService.create_config(db, config)
    return db_config

@router.put("/admin/embedding/config/{config_id}", response_model=EmbeddingConfigResponse)
async def update_embedding_config(
    config_id: str,
    config: EmbeddingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Update an existing embedding configuration. Admin only.
    """
    db_config = EmbeddingConfigService.update_config(db, config_id, config)
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return db_config

@router.get("/admin/embedding/config", response_model=List[EmbeddingConfigResponse])
async def get_all_embedding_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get all embedding configurations. Admin only.
    """
    configs = EmbeddingConfigService.get_all_configs(db)
    return configs

@router.get("/admin/embedding/config/active", response_model=EmbeddingConfigResponse)
async def get_active_embedding_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get the active embedding configuration. Admin only.
    """
    config = EmbeddingConfigService.get_active_config(db)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active configuration found"
        )
    return config

@router.post("/admin/embedding/config/{config_id}/activate", response_model=EmbeddingConfigResponse)
async def activate_embedding_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Set an embedding configuration as active. Admin only.
    """
    config = EmbeddingConfigService.set_active_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

@router.delete("/admin/embedding/config/{config_id}", response_model=Dict[str, Any])
async def delete_embedding_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Delete an embedding configuration. Admin only.
    Cannot delete the active configuration.
    """
    try:
        success = EmbeddingConfigService.delete_config(db, config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        return {"status": "success", "message": "Configuration deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Reranking Configuration Endpoints
# These endpoints are added to the LLM router to maintain consistency with embedding endpoints
@router.post("/admin/reranking/config", response_model=RerankingConfigResponse)
async def create_reranking_config(
    config: RerankingConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Create a new reranking configuration. Admin only.
    """
    db_config = RerankingConfigService.create_config(db, config)
    return db_config

@router.put("/admin/reranking/config/{config_id}", response_model=RerankingConfigResponse)
async def update_reranking_config(
    config_id: str,
    config: RerankingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Update an existing reranking configuration. Admin only.
    """
    db_config = RerankingConfigService.update_config(db, config_id, config)
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return db_config

@router.get("/admin/reranking/config", response_model=List[RerankingConfigResponse])
async def get_all_reranking_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get all reranking configurations. Admin only.
    """
    configs = RerankingConfigService.get_all_configs(db)
    return configs

@router.get("/admin/reranking/config/active", response_model=RerankingConfigResponse)
async def get_active_reranking_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get the active reranking configuration. Admin only.
    """
    config = RerankingConfigService.get_active_config(db)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active configuration found"
        )
    return config

@router.post("/admin/reranking/config/{config_id}/activate", response_model=RerankingConfigResponse)
async def activate_reranking_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Set a reranking configuration as active. Admin only.
    """
    config = RerankingConfigService.set_active_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

@router.delete("/admin/reranking/config/{config_id}", response_model=Dict[str, Any])
async def delete_reranking_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Delete a reranking configuration. Admin only.
    Cannot delete the active configuration.
    """
    try:
        success = RerankingConfigService.delete_config(db, config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        return {"status": "success", "message": "Configuration deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
            )