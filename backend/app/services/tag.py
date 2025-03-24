from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import uuid4
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.tag import Tag, ChatTag
from app.models.chat import Chat
from app.schemas.tag import TagCreate, TagUpdate, PaginatedResponse


def get_tag(db: Session, tag_id: str) -> Optional[Tag]:
    """
    Get a single tag by ID
    """
    return db.query(Tag).filter(Tag.id == tag_id).first()


def get_user_tags(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Tag]:
    """
    Get all tags for a specific user with pagination
    """
    return db.query(Tag).filter(Tag.user_id == user_id).offset(skip).limit(limit).all()

def search_tags(
    db: Session,
    user_id: str,
    search_term: Optional[str] = None,
    color: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> Tuple[List[Tag], int]:
    """
    Search and filter tags with pagination
    
    Args:
        db: Database session
        user_id: ID of the user whose tags to search
        search_term: Optional term to search in tag names
        color: Optional color to filter by
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        sort_by: Field to sort by (name, color, created_at)
        sort_order: Sort direction (asc or desc)
        
    Returns:
        Tuple containing (list of tags, total count)
    """
    # Base query filtering by user_id
    query = db.query(Tag).filter(Tag.user_id == user_id)
    
    # Apply search term filter if provided
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(Tag.name.ilike(search_pattern))
    
    # Apply color filter if provided
    if color:
        query = query.filter(Tag.color == color)
    
    # Count total matching records (before pagination)
    total = query.count()
    
    # Apply sorting
    if sort_by == "name":
        order_column = Tag.name
    elif sort_by == "color":
        order_column = Tag.color
    elif sort_by == "created_at":
        order_column = Tag.created_at
    else:
        order_column = Tag.name  # Default to name
    
    # Apply sort direction
    if sort_order.lower() == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # Apply pagination
    tags = query.offset(skip).limit(limit).all()
    
    return tags, total

def get_user_tags_paginated(
    db: Session,
    user_id: str,
    search_term: Optional[str] = None,
    color: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "name",
    sort_order: str = "asc"
) -> PaginatedResponse[Tag]:
    """
    Get paginated tags for a specific user with optional filtering
    """
    skip = (page - 1) * page_size
    
    tags, total = search_tags(
        db=db,
        user_id=user_id,
        search_term=search_term,
        color=color,
        skip=skip,
        limit=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    # Convert SQLAlchemy models to dictionaries that can be validated by Pydantic
    tag_dicts = []
    for tag in tags:
        tag_dict = {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "user_id": tag.user_id,
            "created_at": tag.created_at,
            "updated_at": tag.updated_at
        }
        tag_dicts.append(tag_dict)
    
    # Use the dictionaries directly with PaginatedResponse
    return PaginatedResponse(
        items=tag_dicts,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages
    )


def create_tag(db: Session, tag_data: TagCreate, user_id: str) -> Tag:
    """
    Create a new tag for a user
    """
    tag_id = str(uuid4())
    tag = Tag(
        id=tag_id,
        name=tag_data.name,
        color=tag_data.color,
        user_id=user_id,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: str, tag_data: TagUpdate) -> Optional[Tag]:
    """
    Update an existing tag
    """
    tag = get_tag(db, tag_id)
    if not tag:
        return None
    
    # Update tag attributes if provided
    if tag_data.name is not None:
        tag.name = tag_data.name
    if tag_data.color is not None:
        tag.color = tag_data.color
    
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: str) -> bool:
    """
    Delete a tag
    """
    tag = get_tag(db, tag_id)
    if not tag:
        return False
    
    db.delete(tag)
    db.commit()
    return True


def get_chat_tags(db: Session, chat_id: str) -> List[Tag]:
    """
    Get all tags for a specific chat
    """
    return (
        db.query(Tag)
        .join(ChatTag, ChatTag.tag_id == Tag.id)
        .filter(ChatTag.chat_id == chat_id)
        .all()
    )


def update_chat_tags(db: Session, chat_id: str, tag_ids: List[str]) -> bool:
    """
    Update the tags for a chat
    """
    # First check if the chat exists
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return False
    
    # Remove existing chat-tag associations
    db.query(ChatTag).filter(ChatTag.chat_id == chat_id).delete()
    
    # Add new chat-tag associations
    for tag_id in tag_ids:
        # Verify the tag exists
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if tag:
            chat_tag = ChatTag(chat_id=chat_id, tag_id=tag_id)
            db.add(chat_tag)
    
    db.commit()
    return True
