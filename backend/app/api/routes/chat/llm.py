from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.utils.deps import get_current_user
from app.schemas.chat import (
    MessageCreate,
    MessageResponse,
)
from app.services.chat import ChatService
from app.services.llm_service import LLMService

router = APIRouter()

@router.post("/{chat_id}/llm", response_model=MessageResponse)
async def send_to_llm(
    chat_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Send a message to the LLM and get a response (non-streaming).
    """
    chat = ChatService.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Check if user owns the chat
    if chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # DO NOT save user message here; it should be saved by the client/test before calling

    # Initialize LLM service, passing user_id
    llm_service = LLMService(db, user_id=current_user.id) # <-- Pass user_id

    # Send message to LLM and get response
    response = await llm_service.chat(
        chat_id=chat_id,
        user_message=message_in.content,
        use_rag=True,
        stream=False
    )

    # NOTE: Tool calls are now handled directly in the LLM service for non-streaming requests

    # Get the last message (assistant's response)
    messages = ChatService.get_messages(db, chat_id)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get assistant response",
        )

    # Return the assistant's message
    for message in reversed(messages):
        if message.role == "assistant":
            # Ensure context_documents is correctly formatted if needed
            if message.context_documents is not None and not isinstance(message.context_documents, list):
                 message.context_documents = [] # Or handle conversion if format is known
            return message

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to get assistant response",
    )