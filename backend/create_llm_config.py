import sys
import os
import logging
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import get_db, Base, engine
from app.services.llm_config import LLMConfigService
from app.schemas.llm import LLMConfigCreate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ollama_config():
    """Create an Ollama LLM configuration and set it as active."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if there's already an active config
        active_config = LLMConfigService.get_active_config(db)
        if active_config:
            logger.info(f"Active config already exists: {active_config.provider} / {active_config.model} / {active_config.embedding_model}")
            
            # Update the existing config to use Ollama
            active_config.provider = "ollama"
            active_config.model = "llama2"
            active_config.embedding_model = "llama2"
            db.commit()
            logger.info(f"Updated active config to use Ollama")
            return
        
        # Create Ollama config
        config = LLMConfigCreate(
            provider="ollama",
            model="llama2",
            embedding_model="llama2",
            system_prompt="You are a helpful AI assistant.",
            api_key=None,
            base_url="http://localhost:11434",
            config=None
        )
        
        # Create and activate config
        db_config = LLMConfigService.create_config(db, config)
        LLMConfigService.set_active_config(db, db_config.id)
        
        logger.info(f"Created and activated Ollama LLM configuration")
    except Exception as e:
        logger.error(f"Error creating Ollama config: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_ollama_config()
    print("Ollama LLM configuration created and activated.")