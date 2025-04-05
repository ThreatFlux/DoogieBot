from typing import Any, Dict # Keep Dict import just in case
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.utils.deps import get_current_user
from app.schemas.chat import (
    MessageCreate,
    MessageResponse, # Use MessageResponse as response_model again
)
from app.services.chat import ChatService
from app.services.llm_service import LLMService

router = APIRouter()

# Revert response_model to MessageResponse
@router.post("/{chat_id}/llm", response_model=MessageResponse)
async def send_to_llm(
    chat_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Send a message to the LLM and get a response (non-streaming).
    Returns the final assistant message saved to the database after
    the full turn (including potential tool execution) completes.
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

    # Save the user message first
    # The test script expects this behavior for non-streaming calls.
    # Use add_message and extract relevant fields from message_in
    user_message_db = ChatService.add_message(
        db=db,
        chat_id=chat_id,
        role=message_in.role,
        content=message_in.content,
        # Pass optional tool-related fields if they exist in the input
        tool_calls=message_in.tool_calls,
        tool_call_id=message_in.tool_call_id,
        name=message_in.name
    )
    if not user_message_db:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save user message",
        )

    # Initialize LLM service, passing user_id
    llm_service = LLMService(db, user_id=current_user.id) # <-- Pass user_id

    # Send message to LLM and wait for the internal process (including tool calls) to complete.
    # The return value of the service call is ignored here.
    await llm_service.chat(
        chat_id=chat_id,
        user_message=message_in.content,
        use_rag=True, # Or determine based on request/config
        stream=False
    )

    # NOTE: Tool calls are handled directly in the LLM service for non-streaming requests.
    # We now fetch the final result from the database.

    # --- Restore database fetch logic ---
    # Get the last message (assistant's response)
    messages = ChatService.get_messages(db, chat_id)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get assistant response after LLM call",
        )

    # Return the assistant's message
    for message in reversed(messages):
        # Look for the *last* assistant message, which should be the final response
        # after any tool calls.
        if message.role == "assistant":
            # Ensure context_documents is correctly formatted if needed
            # (This check might be redundant if DB schema/service handles it)
            if message.context_documents is not None and not isinstance(message.context_documents, list):
                 message.context_documents = [] # Or handle conversion if format is known
            return message # Return the Message ORM model, FastAPI handles serialization

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to find final assistant response in database",
    )
    # --- End Restore ---