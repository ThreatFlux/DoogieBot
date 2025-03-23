from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.sqlite import JSON
import uuid

from app.db.base import Base

class RAGConfig(Base):
    """
    Model for storing RAG component configuration.
    This stores the enabled/disabled state of each RAG component.
    """
    __tablename__ = "rag_config"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bm25_enabled = Column(Boolean, default=True)
    faiss_enabled = Column(Boolean, default=True)
    graph_enabled = Column(Boolean, default=True)
    graph_implementation = Column(String, default="networkx")  # 'networkx' or 'graphrag'
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Additional configuration stored as JSON
    config = Column(JSON, nullable=True)