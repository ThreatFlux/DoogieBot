from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import update
import logging

from app.models.llm_config import LLMConfig
from app.schemas.llm import LLMConfigCreate, LLMConfigUpdate
from app.llm.factory import LLMFactory
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMConfigService:
    """
    Service for managing LLM configurations.
    """
    @staticmethod
    def create_config(db: Session, config: LLMConfigCreate) -> LLMConfig:
        """
        Create a new LLM configuration.
        
        Args:
            db: Database session
            config: LLM configuration data
            
        Returns:
            Created LLM configuration
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Create new config with explicit datetime fields
        db_config = LLMConfig(
            provider=config.chat_provider,  # Set provider to chat_provider for backward compatibility
            chat_provider=config.chat_provider,
            embedding_provider=config.embedding_provider,
            model=config.model,
            embedding_model=config.embedding_model,
            system_prompt=config.system_prompt,
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
    def get_config(db: Session, config_id: str) -> Optional[LLMConfig]:
        """
        Get an LLM configuration by ID.
        
        Args:
            db: Database session
            config_id: LLM configuration ID
            
        Returns:
            LLM configuration or None if not found
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get config by ID
        config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
        
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
    def get_active_config(db: Session) -> Optional[LLMConfig]:
        """
        Get the active LLM configuration.
        
        Args:
            db: Database session
            
        Returns:
            Active LLM configuration or None if not found
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get active config
        config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
        
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
    def get_all_configs(db: Session) -> List[LLMConfig]:
        """
        Get all LLM configurations.
        
        Args:
            db: Database session
            
        Returns:
            List of LLM configurations
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get all configs
        configs = db.query(LLMConfig).all()
        
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
    def update_config(db: Session, config_id: str, config_update: LLMConfigUpdate) -> Optional[LLMConfig]:
        """
        Update an LLM configuration.
        
        Args:
            db: Database session
            config_id: LLM configuration ID
            config_update: LLM configuration update data
            
        Returns:
            Updated LLM configuration or None if not found
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Get existing config
        db_config = LLMConfigService.get_config(db, config_id)
        if not db_config:
            return None
        
        # Update fields
        update_data = config_update.model_dump(exclude_unset=True)
        
        # If setting this config as active, deactivate all other configs
        if update_data.get("is_active", False):
            db.execute(
                update(LLMConfig)
                .where(LLMConfig.id != config_id)
                .values(is_active=False)
            )
        
        # Update config
        for key, value in update_data.items():
            setattr(db_config, key, value)
            
            # If chat_provider is updated, also update provider for backward compatibility
            if key == "chat_provider":
                setattr(db_config, "provider", value)
        
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
        Delete an LLM configuration.
        
        Args:
            db: Database session
            config_id: LLM configuration ID
            
        Returns:
            True if deleted, False if not found
        """
        # Get existing config
        db_config = LLMConfigService.get_config(db, config_id)
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
    def set_active_config(db: Session, config_id: str) -> Optional[LLMConfig]:
        """
        Set an LLM configuration as active.
        
        Args:
            db: Database session
            config_id: LLM configuration ID
            
        Returns:
            Activated LLM configuration or None if not found
        """
        # Import datetime for explicit datetime fields
        from datetime import datetime
        
        # Deactivate all configs
        db.execute(
            update(LLMConfig)
            .values(is_active=False)
        )
        
        # Get config to activate
        db_config = LLMConfigService.get_config(db, config_id)
        if not db_config:
            return None
        
        # Activate config
        db_config.is_active = True
        
        # Explicitly set updated_at to ensure it's not None
        db_config.updated_at = datetime.now()
        
        # Ensure created_at is set if it's None
        if db_config.created_at is None:
            db_config.created_at = datetime.now()
            
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    def get_available_providers(db: Session) -> Dict[str, Any]:
        """
        Get available LLM providers.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary of available providers
        """
        # Get providers from factory
        providers = LLMFactory.get_available_providers()
        
        # Get active config - this will ensure datetime fields are set
        active_config = LLMConfigService.get_active_config(db)
        
        # Add active status to providers
        if active_config:
            for provider_id, provider_info in providers.items():
                provider_info["active"] = (provider_id == active_config.chat_provider)
        
        return providers
    
    @staticmethod
    def create_default_config_if_needed(db: Session) -> Optional[LLMConfig]:
        """
        Create a default LLM configuration if none exists.
        
        Args:
            db: Database session
            
        Returns:
            Created LLM configuration or None if already exists
        """
        # Check if any config exists
        existing_configs = db.query(LLMConfig).count()
        if existing_configs > 0:
            return None
        
        # Create default config with global system prompt
        default_config = LLMConfigCreate(
            chat_provider=settings.DEFAULT_LLM_PROVIDER,
            embedding_provider=settings.DEFAULT_LLM_PROVIDER,
            model=settings.DEFAULT_CHAT_MODEL,
            embedding_model=settings.DEFAULT_EMBEDDING_MODEL,
            system_prompt=settings.DEFAULT_SYSTEM_PROMPT  # Global system prompt for all providers
        )
        
        # Create and activate config
        db_config = LLMConfigService.create_config(db, default_config)
        LLMConfigService.set_active_config(db, db_config.id)
        
        logger.info(f"Created default LLM configuration with chat provider {db_config.chat_provider} and embedding provider {db_config.embedding_provider}")
        
        return db_config