from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, computed_field # Import computed_field
from datetime import datetime

# Message schemas
class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    pass

class MessageUpdate(BaseModel):
    feedback: Optional[str] = None
    feedback_text: Optional[str] = None
    reviewed: Optional[bool] = None

class MessageResponse(MessageBase):
    id: str
    chat_id: str
    created_at: datetime
    tokens: Optional[int] = None
    tokens_per_second: Optional[float] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    feedback: Optional[str] = None
    feedback_text: Optional[str] = None
    reviewed: Optional[bool] = False
    context_documents: Optional[List[str]] = None
    related_question_content: Optional[str] = None # Reinstate simple field

    @field_validator('context_documents', mode='before')
    @classmethod
    def validate_context_documents(cls, v: Any) -> Optional[List[str]]:
        """Ensure context_documents is a list of strings or None."""
        if v is None:
            return None
        if isinstance(v, list):
            # Ensure all elements are strings, handling potential non-string items
            return [str(item) for item in v if item is not None]
        # Fallback: If it's not None or a list, return an empty list
        # This handles cases where the JSON might be stored differently unexpectedly
        return []

    # Reverted: Removed computed_field

    class Config:
        from_attributes = True

# Chat schemas
class ChatBase(BaseModel):
    title: Optional[str] = "New Chat"

class ChatCreate(ChatBase):
    pass

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None

class ChatResponse(ChatBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = None

    class Config:
        from_attributes = True

class ChatListResponse(ChatBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = None

    class Config:
        from_attributes = True

# Paginated response schemas
class PaginatedChatListResponse(BaseModel):
    items: List[ChatListResponse]
    total: int
    page: int
    size: int
    pages: int

class PaginatedMessageResponse(BaseModel):
    items: List[MessageResponse]
    total: int
    page: int
    size: int
    pages: int

# Feedback schemas
class FeedbackCreate(BaseModel):
    feedback: str = Field(..., description="Feedback type: 'positive' or 'negative'")
    feedback_text: Optional[str] = Field(None, description="Additional feedback text")

# LLM response schemas
class LLMResponseMetadata(BaseModel):
    tokens: int
    tokens_per_second: float
    model: str
    provider: str

class StreamingResponse(BaseModel):
    content: str
    metadata: Optional[LLMResponseMetadata] = None
    done: bool = False