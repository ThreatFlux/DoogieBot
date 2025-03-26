from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.sqlite import JSON
import uuid

from app.db.base import Base

class EmbeddingConfig(Base):
    """
    Model for storing embedding configuration.
    Each configuration can be independently activated.
    """
    __tablename__ = "embedding_config"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    base_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Additional configuration stored as JSON
    config = Column(JSON, nullable=True)