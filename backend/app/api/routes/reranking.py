from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel # Add BaseModel import
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.schemas.reranking import (
    RerankingConfigCreate,
    RerankingConfigUpdate,
    RerankingConfigResponse
)
from app.services.reranking_config import RerankingConfigService
from app.utils.deps import get_db, get_current_admin_user
from app.models.user import User
from app.llm.factory import LLMFactory # Needed to get other providers


router = APIRouter()
print("--- DEBUG: Initializing reranking.py router ---") # Add print

@router.post("/", response_model=RerankingConfigResponse)
def create_reranking_config(
    config: RerankingConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new reranking configuration. Admin only."""
    return RerankingConfigService.create_config(db, config)

@router.get("/", response_model=List[RerankingConfigResponse])
def get_all_reranking_configs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all reranking configurations. Admin only."""
    return RerankingConfigService.get_all_configs(db)[skip:skip + limit]

@router.get("/active", response_model=RerankingConfigResponse)
def get_active_reranking_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get the active reranking configuration. Admin only."""
    config = RerankingConfigService.get_active_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="No active reranking configuration found")
    return config

@router.get("/{config_id}", response_model=RerankingConfigResponse)
def get_reranking_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get a reranking configuration by ID. Admin only."""
    config = RerankingConfigService.get_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Reranking configuration not found")
    return config

@router.put("/{config_id}", response_model=RerankingConfigResponse)
def update_reranking_config(
    config_id: str,
    config: RerankingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update a reranking configuration. Admin only."""
    updated_config = RerankingConfigService.update_config(db, config_id, config)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Reranking configuration not found")
    return updated_config

@router.post("/{config_id}/activate", response_model=RerankingConfigResponse)
def activate_reranking_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Activate a reranking configuration. Admin only."""
    activated_config = RerankingConfigService.set_active_config(db, config_id)
    if not activated_config:
        raise HTTPException(status_code=404, detail="Reranking configuration not found")
    return activated_config

@router.delete("/{config_id}", response_model=Dict[str, Any])
def delete_reranking_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a reranking configuration. Admin only."""
    if not RerankingConfigService.delete_config(db, config_id):
        raise HTTPException(status_code=404, detail="Reranking configuration not found")
    return {"message": "Reranking configuration deleted"}


# Define a simple response model for providers
class RerankingProviderInfo(BaseModel):
    id: str
    name: str
    requires_api_key: bool
    requires_base_url: bool

class RerankingProviderResponse(BaseModel):
    providers: List[RerankingProviderInfo]

@router.get("/providers", response_model=RerankingProviderResponse)
def get_reranking_providers(
    current_user: User = Depends(get_current_admin_user)
):
    """Get available reranking providers."""
    # Start with providers known to have rerank APIs (or potential ones)
    # Example: Add Cohere if/when implemented
    known_providers = {
        # "cohere": {"name": "Cohere", "requires_api_key": True, "requires_base_url": False},
    }

    # Add our special "local" provider for sentence-transformers
    known_providers["local"] = {
        "name": "Local (SentenceTransformers)",
        "requires_api_key": False, # Not needed for local loading
        "requires_base_url": False # Not needed for local loading
    }

    # Optionally include providers from LLMFactory if they *might* support reranking via embeddings/future methods
    # Or keep it strictly to known/intended rerankers
    # For now, let's just list 'local' and potential dedicated ones
    # llm_providers = LLMFactory.get_available_providers()
    # for provider_id, details in llm_providers.items():
    #     if provider_id not in known_providers:
    #         # Decide if we want to list general LLM providers here too
    #         pass


    provider_list = [
        RerankingProviderInfo(
            id=pid,
            name=pinfo["name"],
            requires_api_key=pinfo["requires_api_key"],
            requires_base_url=pinfo["requires_base_url"]
        ) for pid, pinfo in known_providers.items()
    ]

    return RerankingProviderResponse(providers=provider_list)