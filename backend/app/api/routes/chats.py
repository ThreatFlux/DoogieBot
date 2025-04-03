from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Import routers from the new modules within the 'chat' subdirectory
from .chat import admin, crud, llm, messages, stream
# Import specific functions that were previously at the root path
from .chat.crud import create_chat_func, read_chats_func

# Import necessary dependencies and schemas for the root routes
from app.db.base import get_db
from app.models.user import User
from app.utils.deps import get_current_user
from app.schemas.chat import ChatCreate, ChatResponse, ChatListResponse

router = APIRouter()

# Admin endpoints first (more specific routes)
@router.get("/admin/chats/flagged", response_model=PaginatedChatListResponse)
async def get_flagged_chats(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get paginated chats with negative feedback. Admin only.
    """
    chats, total = ChatService.get_flagged_chats(db, skip=skip, limit=limit)
    
    # Serialize chats to ensure all required fields are included
    return {
        "items": [
            {
                "id": chat.id,
                "user_id": chat.user_id,
                "title": chat.title,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "messages": [
                    {
                        "id": msg.id,
                        "chat_id": msg.chat_id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at,
                        "tokens": msg.tokens,
                        "tokens_per_second": msg.tokens_per_second,
                        "model": msg.model,
                        "provider": msg.provider,
                        "feedback": msg.feedback,
                        "feedback_text": msg.feedback_text,
                        "reviewed": msg.reviewed,
                        "context_documents": msg.context_documents if msg.context_documents is None else [str(doc_id) for doc_id in msg.context_documents]
                    }
                    for msg in chat.messages
                ] if chat.messages else None
            }
            for chat in chats
        ],
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "size": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 1
    }

@router.get("/admin/feedback") # REMOVED response_model, will construct manually
def read_feedback_messages(
    db: Session = Depends(get_db),
    feedback_type: str = None,
    reviewed: bool = None,
    skip: int = 0, # Add skip parameter
    limit: int = 100, # Add limit parameter
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get paginated messages with feedback. Admin only.
    """
    messages, total = ChatService.get_feedback_messages(
        db, feedback_type, reviewed, skip=skip, limit=limit # Pass skip and limit
    )
    
    # Manually construct response items to include related_question_content
    response_items = []
    for msg in messages:
        related_content = None
        if hasattr(msg, 'related_question') and msg.related_question:
            related_content = msg.related_question.content
            
        response_items.append({
            "id": msg.id,
            "chat_id": msg.chat_id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(), # Ensure ISO format for JSON
            "tokens": msg.tokens,
            "tokens_per_second": msg.tokens_per_second,
            "model": msg.model,
            "provider": msg.provider,
            "feedback": msg.feedback,
            "feedback_text": msg.feedback_text,
            "reviewed": msg.reviewed,
            "context_documents": msg.context_documents, # Assuming this is already JSON serializable
            "related_question_content": related_content
        })
        
    # Construct final paginated response
    page = skip // limit + 1 if limit > 0 else 1
    pages = (total + limit - 1) // limit if limit > 0 else 1
    
    return {
        "items": response_items, # Use the manually constructed list
        "total": total,
        "page": page,
        "size": limit,
        "pages": pages
    }

@router.put("/admin/messages/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: str,
    message_in: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Update a message. Admin only.
    """
    if message_in.reviewed is not None:
        message = ChatService.mark_as_reviewed(db, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )
        return message
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No valid update fields provided",
    )

# Regular chat endpoints
@router.post("", response_model=ChatResponse, tags=["chat_crud"])
    chat_in: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """ Create a new chat. """
    return create_chat_func(chat_in=chat_in, db=db, current_user=current_user)

@router.get("", response_model=List[ChatListResponse], tags=["chat_crud"])
def read_chats_endpoint(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    """ Retrieve user's chats. """
    return read_chats_func(db=db, skip=skip, limit=limit, current_user=current_user)


# Include the routers from the submodules
# Note: crud.router now only contains routes with non-empty paths like /{chat_id}
router.include_router(admin.router, tags=["chat_admin"])
router.include_router(crud.router, tags=["chat_crud"]) # Includes /{chat_id}, PUT, DELETE etc.
router.include_router(messages.router, tags=["chat_messages"])
router.include_router(llm.router, tags=["chat_llm"])
router.include_router(stream.router, tags=["chat_stream"])