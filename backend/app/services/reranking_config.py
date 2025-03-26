from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import update
import logging

from app.models.reranking_config import RerankingConfig
from app.schemas.reranking import RerankingConfigCreate, RerankingConfigUpdate
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RerankingConfigService:
    """
    Service for managing reranking configurations.
    """
    
    @staticmethod
    def create_config(db: Session, config: RerankingConfigCreate) -> RerankingConfig:
        """
        Create a new reranking configuration.
        
        Args:
            db: Database session
            config: Reranking configuration data
            
        Returns:
            Created reranking configuration
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Create config with explicit datetime fields
        db_config = RerankingConfig(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            config=config.config,
            is_active=False,  # New configs are not active by default
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    def get_config(db: Session, config_id: str) -> Optional[RerankingConfig]:
        """
        Get a reranking configuration by ID.
        
        Args:
            db: Database session
            config_id: Reranking configuration ID
            
        Returns:
            Reranking configuration or None if not found
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get config by ID
        config = db.query(RerankingConfig).filter(RerankingConfig.id == config_id).first()
        
        # If config exists but has None for datetime fields, set them
        if config:
            if config.created_at is None:
                config.created_at = datetime.now()
                
            if config.updated_at is None:
                config.updated_at = datetime.now()
                
            # Commit the changes to ensure the fields are saved
            db.commit()
            
        return config
    
    @staticmethod
    def get_active_config(db: Session) -> Optional[RerankingConfig]:
        """
        Get the active reranking configuration.
        
        Args:
            db: Database session
            
        Returns:
            Active reranking configuration or None if not found
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get active config
        config = db.query(RerankingConfig).filter(RerankingConfig.is_active == True).first()
        
        # If config exists but has None for datetime fields, set them
        if config:
            if config.created_at is None:
                config.created_at = datetime.now()
                
            if config.updated_at is None:
                config.updated_at = datetime.now()
                
            # Commit the changes to ensure the fields are saved
            db.commit()
            
        return config
    
    @staticmethod
    def get_all_configs(db: Session) -> List[RerankingConfig]:
        """
        Get all reranking configurations.
        
        Args:
            db: Database session
            
        Returns:
            List of reranking configurations
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get all configs
        configs = db.query(RerankingConfig).all()
        
        # Check each config for None datetime fields
        for config in configs:
            if config.created_at is None:
                config.created_at = datetime.now()
                
            if config.updated_at is None:
                config.updated_at = datetime.now()
        
        # If any configs were updated, commit the changes
        if configs and any(config.created_at is None or config.updated_at is None for config in configs):
            db.commit()
            
        return configs
    
    @staticmethod
    def update_config(db: Session, config_id: str, config_update: RerankingConfigUpdate) -> Optional[RerankingConfig]:
        """
        Update a reranking configuration.
        
        Args:
            db: Database session
            config_id: Reranking configuration ID
            config_update: Reranking configuration update data
            
        Returns:
            Updated reranking configuration or None if not found
        """
        # Get existing config
        db_config = RerankingConfigService.get_config(db, config_id)
        if not db_config:
            return None
        
        # Update fields
        update_data = config_update.model_dump(exclude_unset=True)
        
        # If setting this config as active, deactivate all other configs
        if update_data.get("is_active", False):
            db.execute(
                update(RerankingConfig)
                .where(RerankingConfig.id != config_id)
                .values(is_active=False)
            )
        
        # Update config
        for key, value in update_data.items():
            setattr(db_config, key, value)
        
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Explicitly set updated_at to ensure it's not None
        db_config.updated_at = datetime.now()
        
        # Ensure created_at is set if it's None
        if db_config.created_at is None:
            db_config.created_at = datetime.now()
        
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    def delete_config(db: Session, config_id: str) -> bool:
        """
        Delete a reranking configuration.
        
        Args:
            db: Database session
            config_id: Reranking configuration ID
            
        Returns:
            True if deleted, False if not found
        """
        # Get existing config
        db_config = RerankingConfigService.get_config(db, config_id)
        if not db_config:
            return False
        
        # Cannot delete active config
        if db_config.is_active:
            raise ValueError("Cannot delete active configuration")
        
        # Delete config
        db.delete(db_config)
        db.commit()
        
        return True
    
    @staticmethod
    def set_active_config(db: Session, config_id: str) -> Optional[RerankingConfig]:
        """
        Set a reranking configuration as active.
        
        Args:
            db: Database session
            config_id: Reranking configuration ID
            
        Returns:
            Activated reranking configuration or None if not found
        """
        # Deactivate all configs
        db.execute(
            update(RerankingConfig)
            .values(is_active=False)
        )
        
        # Get config to activate
        db_config = RerankingConfigService.get_config(db, config_id)
        if not db_config:
            return None
        
        # Activate config
        db_config.is_active = True
        
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Explicitly set updated_at to ensure it's not None
        db_config.updated_at = datetime.now()
        
        # Ensure created_at is set if it's None
        if db_config.created_at is None:
            db_config.created_at = datetime.now()
            
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    def create_default_config_if_needed(db: Session) -> Optional[RerankingConfig]:
        """
        Create a default reranking configuration if none exists.
        
        Args:
            db: Database session
            
        Returns:
            Created reranking configuration or None if already exists
        """
        # Check if any config exists
        existing_configs = db.query(RerankingConfig).count()
        if existing_configs > 0:
            return None
        
        # Create default config
        default_config = RerankingConfigCreate(
            provider=settings.DEFAULT_LLM_PROVIDER,
            model=settings.DEFAULT_CHAT_MODEL  # Use chat model as default for reranking
        )
        
        # Create and activate config
        db_config = RerankingConfigService.create_config(db, default_config)
        RerankingConfigService.set_active_config(db, db_config.id)
        
        logger.info(f"Created default reranking configuration with provider {db_config.provider} and model {db_config.model}")
        
        return db_config