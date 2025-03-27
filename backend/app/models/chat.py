from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Text, Integer, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base

class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool" # Add TOOL role

class FeedbackType(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at") # Add order_by
    chat_tags = relationship("ChatTag", back_populates="chat", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="chat_tags", back_populates="chats", overlaps="chat_tags")

    def __repr__(self):
        return f"<Chat {self.id}>"

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False) # Uses MessageRole enum values
    content = Column(Text, nullable=True) # Allow content to be nullable for tool calls
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # LLM metadata
    tokens = Column(Integer, nullable=True) # Total tokens for the LLM call that generated this message
    prompt_tokens = Column(Integer, nullable=True) # Prompt tokens for the call
    completion_tokens = Column(Integer, nullable=True) # Completion tokens for the call
    tokens_per_second = Column(Float, nullable=True)
    model = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    finish_reason = Column(String, nullable=True) # Add finish_reason

    # Tool Call / Result Data
    tool_calls = Column(JSON, nullable=True) # For assistant message requesting tool calls (stores list of tool call dicts)
    tool_call_id = Column(String, nullable=True) # For tool message providing result, links to assistant's tool_call id
    name = Column(String, nullable=True) # For tool message, the name of the function called

    # Feedback
    feedback = Column(String, nullable=True) # Uses FeedbackType enum values
    feedback_text = Column(Text, nullable=True)
    reviewed = Column(Boolean, default=False)

    # RAG metadata
    context_documents = Column(JSON, nullable=True)

    # Relationships
    chat = relationship("Chat", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id}>"

# Removed duplicate Tag and ChatTag definitions - they belong in tag.py
