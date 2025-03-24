from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.tag import Tag, TagCreate, TagUpdate, ChatTagUpdate, PaginatedResponse, TagFilter
from app.services import tag as tag_service
from app.utils.deps import get_db, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Route with no trailing slash
@router.get("", response_model=List[Tag])
def get_user_tags_no_slash(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get all tags for the current user (no trailing slash version)
    """
    logger.debug(f"Getting tags for user {current_user.id} - skip: {skip}, limit: {limit} (no slash)")
    return tag_service.get_user_tags(db, current_user.id, skip, limit)

# Route with trailing slash
@router.get("/", response_model=List[Tag])
def get_user_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get all tags for the current user (simple list)
    """
    logger.debug(f"Getting tags for user {current_user.id} - skip: {skip}, limit: {limit}")
    return tag_service.get_user_tags(db, current_user.id, skip, limit)

# Search route with no trailing slash
@router.get("/search", response_model=PaginatedResponse)
def search_user_tags(
    search: Optional[str] = Query(None, description="Search term to filter tag names"),
    color: Optional[str] = Query(None, description="Filter by tag color"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Field to sort by: name, color, created_at"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search and filter tags with pagination
    """
    return tag_service.get_user_tags_paginated(
        db=db,
        user_id=current_user.id,
        search_term=search,
        color=color,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

# Search route with trailing slash
@router.get("/search/", response_model=PaginatedResponse)
def search_user_tags_with_slash(
    search: Optional[str] = Query(None, description="Search term to filter tag names"),
    color: Optional[str] = Query(None, description="Filter by tag color"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Field to sort by: name, color, created_at"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search and filter tags with pagination (trailing slash version)
    """
    return tag_service.get_user_tags_paginated(
        db=db,
        user_id=current_user.id,
        search_term=search,
        color=color,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

# Create tag with no trailing slash
@router.post("", response_model=Tag)
def create_tag_no_slash(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new tag (no trailing slash version)
    """
    logger.debug(f"Creating tag for user {current_user.id} - name: {tag_data.name}, color: {tag_data.color} (no slash)")
    try:
        tag = tag_service.create_tag(db, tag_data, current_user.id)
        logger.debug(f"Tag created with ID: {tag.id}")
        return tag
    except Exception as e:
        logger.error(f"Error creating tag: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tag: {str(e)}",
        )

# Create tag with trailing slash
@router.post("/", response_model=Tag)
def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new tag
    """
    logger.debug(f"Creating tag for user {current_user.id} - name: {tag_data.name}, color: {tag_data.color}")
    try:
        tag = tag_service.create_tag(db, tag_data, current_user.id)
        logger.debug(f"Tag created with ID: {tag.id}")
        return tag
    except Exception as e:
        logger.error(f"Error creating tag: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tag: {str(e)}",
        )

# Get tag with no trailing slash
@router.get("/{tag_id}", response_model=Tag)
def get_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific tag by ID
    """
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
        
    # Check if the tag belongs to the current user
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tag",
        )
        
    return tag

# Get tag with trailing slash
@router.get("/{tag_id}/", response_model=Tag)
def get_tag_with_slash(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific tag by ID (trailing slash version)
    """
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
        
    # Check if the tag belongs to the current user
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tag",
        )
        
    return tag

# Update tag with no trailing slash
@router.put("/{tag_id}", response_model=Tag)
def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a tag
    """
    # First check if the tag exists and belongs to the current user
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
        
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tag",
        )
    
    # Update the tag
    updated_tag = tag_service.update_tag(db, tag_id, tag_data)
    return updated_tag

# Update tag with trailing slash
@router.put("/{tag_id}/", response_model=Tag)
def update_tag_with_slash(
    tag_id: str,
    tag_data: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a tag (trailing slash version)
    """
    # First check if the tag exists and belongs to the current user
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
        
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tag",
        )
    
    # Update the tag
    updated_tag = tag_service.update_tag(db, tag_id, tag_data)
    return updated_tag

# Delete tag with no trailing slash
@router.delete("/{tag_id}", response_model=dict)
def delete_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a tag
    """
    # First check if the tag exists and belongs to the current user
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
        
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this tag",
        )
    
    # Delete the tag
    success = tag_service.delete_tag(db, tag_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag",
        )
    
    return {"detail": "Tag deleted successfully"}

# Delete tag with trailing slash
@router.delete("/{tag_id}/", response_model=dict)
def delete_tag_with_slash(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a tag (trailing slash version)
    """
    # First check if the tag exists and belongs to the current user
    tag = tag_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
        
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this tag",
        )
    
    # Delete the tag
    success = tag_service.delete_tag(db, tag_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag",
        )
    
    return {"detail": "Tag deleted successfully"}

# Get chat tags
@router.get("/chats/{chat_id}/tags", response_model=List[Tag])
def get_chat_tags(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all tags for a specific chat
    """
    # First verify the chat exists and belongs to the current user
    from app.services import chat as chat_service
    chat = chat_service.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
        
    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this chat",
        )
    
    return tag_service.get_chat_tags(db, chat_id)

# Get chat tags (trailing slash version)
@router.get("/chats/{chat_id}/tags/", response_model=List[Tag])
def get_chat_tags_with_slash(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all tags for a specific chat (trailing slash version)
    """
    # First verify the chat exists and belongs to the current user
    from app.services import chat as chat_service
    chat = chat_service.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
        
    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this chat",
        )
    
    return tag_service.get_chat_tags(db, chat_id)

# Update chat tags
@router.put("/chats/{chat_id}/tags", response_model=dict)
def update_chat_tags(
    chat_id: str,
    chat_tag_data: ChatTagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update tags for a chat
    """
    # First verify the chat exists and belongs to the current user
    from app.services import chat as chat_service
    chat = chat_service.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
        
    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this chat",
        )
    
    # Ensure all tags belong to the current user
    for tag_id in chat_tag_data.tags:
        tag = tag_service.get_tag(db, tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tag ID: {tag_id}",
            )
    
    # Update the chat tags
    success = tag_service.update_chat_tags(db, chat_id, chat_tag_data.tags)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat tags",
        )
    
    return {"detail": "Chat tags updated successfully"}

# Update chat tags (trailing slash version)
@router.put("/chats/{chat_id}/tags/", response_model=dict)
def update_chat_tags_with_slash(
    chat_id: str,
    chat_tag_data: ChatTagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update tags for a chat (trailing slash version)
    """
    # First verify the chat exists and belongs to the current user
    from app.services import chat as chat_service
    chat = chat_service.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
        
    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this chat",
        )
    
    # Ensure all tags belong to the current user
    for tag_id in chat_tag_data.tags:
        tag = tag_service.get_tag(db, tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tag ID: {tag_id}",
            )
    
    # Update the chat tags
    success = tag_service.update_chat_tags(db, chat_id, chat_tag_data.tags)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat tags",
        )
    
    return {"detail": "Chat tags updated successfully"}
