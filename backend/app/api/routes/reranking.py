from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter()

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