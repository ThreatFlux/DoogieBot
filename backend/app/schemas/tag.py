from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')


# Schemas for Tag
class TagBase(BaseModel):
    name: str
    color: str


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class TagInDB(TagBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True  # Pydantic V2 way of setting orm_mode=True
    }


class Tag(TagInDB):
    """Tag schema that is returned to the client"""
    pass

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int
    
    model_config = {
        "arbitrary_types_allowed": True
    }

class TagFilter(BaseModel):
    """Query parameters for tag filtering"""
    search: Optional[str] = None
    color: Optional[str] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "name"
    sort_order: str = "asc"


# Schemas for modifying chat tags
class ChatTagUpdate(BaseModel):
    tags: List[str] = Field(..., description="List of tag IDs to associate with the chat")
