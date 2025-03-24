from sqlalchemy import Column, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.base import Base

class Tag(Base):
    """
    Tag model for user-defined tags to categorize chats
    """
    __tablename__ = "tags"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    color = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="tags")
    chat_tags = relationship("ChatTag", back_populates="tag", cascade="all, delete-orphan")


class ChatTag(Base):
    """
    Association table for many-to-many relationship between chats and tags
    """
    __tablename__ = "chat_tags"

    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="chat_tags")
    tag = relationship("Tag", back_populates="chat_tags")
