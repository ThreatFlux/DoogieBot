from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas.embedding import (
    EmbeddingConfigCreate,
    EmbeddingConfigUpdate,
    EmbeddingConfigResponse
)
from app.services.embedding_config import EmbeddingConfigService
from app.utils.deps import get_db

router = APIRouter()

@router.post("/", response_model=EmbeddingConfigResponse)
def create_embedding_config(
    config: EmbeddingConfigCreate,
    db: Session = Depends(get_db)
):
    """Create a new embedding configuration."""
    return EmbeddingConfigService.create_config(db, config)

@router.get("/", response_model=List[EmbeddingConfigResponse])
def get_all_embedding_configs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all embedding configurations."""
    return EmbeddingConfigService.get_all_configs(db)[skip:skip + limit]

@router.get("/{config_id}", response_model=EmbeddingConfigResponse)
def get_embedding_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """Get an embedding configuration by ID."""
    config = EmbeddingConfigService.get_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Embedding configuration not found")
    return config

@router.get("/active", response_model=EmbeddingConfigResponse)
def get_active_embedding_config(db: Session = Depends(get_db)):
    """Get the active embedding configuration."""
    config = EmbeddingConfigService.get_active_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="No active embedding configuration found")
    return config

@router.put("/{config_id}", response_model=EmbeddingConfigResponse)
def update_embedding_config(
    config_id: str,
    config: EmbeddingConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update an embedding configuration."""
    updated_config = EmbeddingConfigService.update_config(db, config_id, config)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Embedding configuration not found")
    return updated_config

@router.post("/{config_id}/activate", response_model=EmbeddingConfigResponse)
def activate_embedding_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """Activate an embedding configuration."""
    activated_config = EmbeddingConfigService.set_active_config(db, config_id)
    if not activated_config:
        raise HTTPException(status_code=404, detail="Embedding configuration not found")
    return activated_config

@router.delete("/{config_id}")
def delete_embedding_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """Delete an embedding configuration."""
    if not EmbeddingConfigService.delete_config(db, config_id):
        raise HTTPException(status_code=404, detail="Embedding configuration not found")
    return {"message": "Embedding configuration deleted"}