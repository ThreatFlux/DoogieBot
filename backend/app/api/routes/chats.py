from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.utils.deps import get_current_user, get_current_user_stream, get_current_admin_user
from app.schemas.chat import (
    ChatCreate,
    ChatUpdate,
    ChatResponse,
    ChatListResponse,
    PaginatedChatListResponse,
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    FeedbackCreate,
    PaginatedMessageResponse, # Import the new schema
)
from app.services.chat import ChatService
from app.services.llm_service import LLMService
# Removed duplicate import: from app.utils.deps import get_current_user, get_current_admin_user

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

@router.get("/admin/feedback", response_model=PaginatedMessageResponse) # Update response model
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

    # Construct paginated response
    page = skip // limit + 1 if limit > 0 else 1
    pages = (total + limit - 1) // limit if limit > 0 else 1

    # Let FastAPI handle serialization using the response_model and from_attributes=True
    return {
        "items": messages, # Return the list of SQLAlchemy Message objects directly
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
@router.post("", response_model=ChatResponse)
def create_chat(
    chat_in: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new chat.
    """
    chat = ChatService.create_chat(db, current_user.id, chat_in.title)
    return chat

@router.get("", response_model=List[ChatListResponse])
def read_chats(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve user's chats.
    """
    chats = ChatService.get_user_chats(db, current_user.id, skip=skip, limit=limit)

    # Ensure context_documents is properly formatted for each message
    for chat in chats:
        if chat.messages:
            for message in chat.messages:
                if message.context_documents is not None and not isinstance(message.context_documents, list):
                    # If it's a dict with a 'documents' key containing a list of objects with 'id' fields
                    if isinstance(message.context_documents, dict) and 'documents' in message.context_documents:
                        docs = message.context_documents['documents']
                        if isinstance(docs, list) and all(isinstance(doc, dict) and 'id' in doc for doc in docs):
                            message.context_documents = [doc['id'] for doc in docs]
                        else:
                            message.context_documents = []
                    else:
                        # For other non-list formats, convert to empty list
                        message.context_documents = []

    return chats

@router.get("/{chat_id}", response_model=ChatResponse)
def read_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific chat by id.
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

    # Get messages for the chat
    chat.messages = ChatService.get_messages(db, chat_id)
    for message in chat.messages:
        if message.context_documents is not None and not isinstance(message.context_documents, list):
            message.context_documents = [str(doc_id) for doc_id in message.context_documents]
    return chat

@router.put("/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: str,
    chat_in: ChatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a chat.
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

    # If tags are provided, update them separately
    # This is done first to ensure both the title and tags get updated
    if chat_in.tags is not None:
        from app.services.tag import update_chat_tags
        success = update_chat_tags(db, chat_id, chat_in.tags)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update chat tags",
            )

    # Update chat title
    if chat_in.title is not None:
        chat = ChatService.update_chat(db, chat_id, chat_in.title)

    # Get the updated chat with associated messages
    chat.messages = ChatService.get_messages(db, chat_id)
    return chat

@router.delete("/{chat_id}", response_model=bool)
def delete_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete a chat.
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

    result = ChatService.delete_chat(db, chat_id)
    return result

@router.post("/{chat_id}/messages", response_model=MessageResponse)
def add_message(
    chat_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Add a message to a chat.
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

    message = ChatService.add_message(
        db,
        chat_id,
        message_in.role,
        message_in.content
    )
    return message

@router.post("/{chat_id}/llm", response_model=MessageResponse)
async def send_to_llm(
    chat_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Send a message to the LLM and get a response.
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

    # Add user message to the chat
    ChatService.add_message(
        db,
        chat_id,
        "user",
        message_in.content
    )

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
    # The service takes care of:
    # 1. Executing the tools
    # 2. Sending results back to the LLM
    # 3. Continuing the conversation until a final content response is received
    # No additional handling is needed here as that logic is now in LLMService.chat()

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

@router.post("/{chat_id}/stream")
async def stream_from_llm(
    chat_id: str,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream a response from the LLM using POST.
    """
    import logging
    from app.core.config import settings

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if settings.LLM_DEBUG_LOGGING else logging.INFO)

    logger.debug(f"POST Stream request received for chat {chat_id}")

    chat = ChatService.get_chat(db, chat_id)
    if not chat:
        logger.error(f"Chat {chat_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Check if user owns the chat
    if chat.user_id != current_user.id:
        logger.error(f"User {current_user.id} does not own chat {chat_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Add user message to the chat
    ChatService.add_message(
        db,
        chat_id,
        "user",
        message_in.content
    )

    logger.debug(f"Initializing LLM service for streaming")
    # Initialize LLM service, passing user_id
    llm_service = LLMService(db, user_id=current_user.id) # <-- Pass user_id

    # Create async generator for streaming response
    async def response_generator():
        import json
        import asyncio
        import logging
        import time
        import traceback

        logger = logging.getLogger(__name__) # Use local logger

        last_sent_time = time.time()
        keep_alive_interval = 15  # seconds

        try:
            logger.debug(f"Starting chat stream for chat {chat_id}")

            # Send an initial message to establish the connection
            initial_chunk = {"content": "", "status": "processing", "done": False}
            yield f"data: {json.dumps(initial_chunk)}\n\n"

            # Get the chat stream from the LLM service
            try:
                chat_stream = llm_service.chat( # No need for wait_for here, handled in service
                    chat_id=chat_id,
                    user_message=message_in.content,
                    use_rag=True,
                    stream=True
                )

                chunk_count = 0
                async for chunk in chat_stream:
                    chunk_count += 1
                    current_time = time.time()

                    if chunk_count % 10 == 0 or chunk.get("done", False):
                        logger.debug(f"Streaming chunk {chunk_count}: {chunk.get('content', '')[:30]}... (done: {chunk.get('done', False)})")

                    # Handle tool calls in stream
                    if 'tool_calls_delta' in chunk or 'tool_calls' in chunk:
                        # Just forward the chunk as-is - frontend will handle visualization
                        # The chunk format follows the OpenAI API format for tool calls
                        logger.debug(f"Tool call chunk detected: {json.dumps(chunk)[:100]}...")
                        # We don't need special processing - the chunk already contains the necessary data

                    try:
                        yield f"data: {json.dumps(chunk)}\n\n"
                        last_sent_time = current_time
                    except Exception as json_error:
                        logger.error(f"Error serializing chunk {chunk_count}: {str(json_error)}")
                        continue

                    # Minimal delay
                    await asyncio.sleep(0.001) # Reduced delay

                    # Keep-alive logic (simplified)
                    if current_time - last_sent_time > keep_alive_interval and not chunk.get("done", False):
                         yield ": keep-alive\n\n" # Simple SSE comment for keep-alive
                         last_sent_time = current_time

                logger.debug(f"Finished streaming {chunk_count} chunks for chat {chat_id}")

                # Ensure a final 'done' message if stream ends unexpectedly
                if chunk_count == 0 or not chunk.get("done", False):
                     final_chunk = {"content": "Response processing finished.", "done": True}
                     yield f"data: {json.dumps(final_chunk)}\n\n"

            except asyncio.TimeoutError: # Catch timeout from underlying client if applicable
                logger.error(f"Timeout during LLM interaction for chat {chat_id}")
                error_chunk = {"content": "The request timed out.", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                ChatService.add_message(db, chat_id, "assistant", "Error: Request timed out.", context_documents={"error": "timeout"})
            except Exception as chat_error:
                logger.exception(f"Error getting chat stream for chat {chat_id}: {str(chat_error)}")
                error_chunk = {"content": f"An error occurred: {str(chat_error)}", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                ChatService.add_message(db, chat_id, "assistant", f"Error: {str(chat_error)}", context_documents={"error": str(chat_error)})

        except Exception as e:
            logger.exception(f"Outer error in streaming response generator: {str(e)}\n{traceback.format_exc()}")
            error_chunk = {"content": f"An unexpected error occurred: {str(e)}", "error": True, "done": True}
            yield f"data: {json.dumps(error_chunk)}\n\n"


    logger.debug(f"Returning StreamingResponse for chat {chat_id}")
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked"
        }
    )


# GET endpoint for EventSource compatibility
@router.get("/{chat_id}/stream")
async def stream_from_llm_get(
    request: Request, # Use Request object to get query params
    chat_id: str,
    # content: str, # Content will be a query parameter
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_stream), # Use stream-compatible auth
) -> StreamingResponse:
    """
    Stream a response from the LLM using GET (for EventSource).
    """
    import logging
    from app.core.config import settings

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if settings.LLM_DEBUG_LOGGING else logging.INFO)

    # Get content from query parameters
    content = request.query_params.get("content")
    if not content:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing 'content' query parameter")


    logger.debug(f"GET Stream request received for chat {chat_id} with content: {content[:50]}...")

    chat = ChatService.get_chat(db, chat_id)
    if not chat:
        logger.error(f"Chat {chat_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Check if user owns the chat
    if chat.user_id != current_user.id:
        logger.error(f"User {current_user.id} does not own chat {chat_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Add user message to the chat
    ChatService.add_message(
        db,
        chat_id,
        "user",
        content # Use content from query param
    )

    logger.debug(f"Initializing LLM service for streaming")
    # Initialize LLM service, passing user_id
    llm_service = LLMService(db, user_id=current_user.id) # <-- Pass user_id

    # Create async generator (same logic as POST endpoint)
    async def response_generator():
        import json
        import asyncio
        import logging
        import time
        import traceback

        logger = logging.getLogger(__name__) # Use local logger

        last_sent_time = time.time()
        keep_alive_interval = 15  # seconds

        try:
            logger.debug(f"Starting chat stream for chat {chat_id}")

            # Send an initial message to establish the connection
            initial_chunk = {"content": "", "status": "processing", "done": False}
            yield f"data: {json.dumps(initial_chunk)}\n\n"

            # Get the chat stream from the LLM service
            try:
                chat_stream = llm_service.chat( # No need for wait_for here
                    chat_id=chat_id,
                    user_message=content, # Use content from query param
                    use_rag=True,
                    stream=True
                )

                chunk_count = 0
                async for chunk in chat_stream:
                    chunk_count += 1
                    current_time = time.time()

                    if chunk_count % 10 == 0 or chunk.get("done", False):
                        logger.debug(f"Streaming chunk {chunk_count}: {chunk.get('content', '')[:30]}... (done: {chunk.get('done', False)})")

                    # Handle tool calls in stream
                    if 'tool_calls_delta' in chunk or 'tool_calls' in chunk:
                        # Just forward the chunk as-is - frontend will handle visualization
                        logger.debug(f"Tool call chunk detected in GET stream: {json.dumps(chunk)[:100]}...")

                    try:
                        yield f"data: {json.dumps(chunk)}\n\n"
                        last_sent_time = current_time
                    except Exception as json_error:
                        logger.error(f"Error serializing chunk {chunk_count}: {str(json_error)}")
                        continue

                    # Minimal delay
                    await asyncio.sleep(0.001)

                    # Keep-alive logic
                    if current_time - last_sent_time > keep_alive_interval and not chunk.get("done", False):
                         yield ": keep-alive\n\n"
                         last_sent_time = current_time

                logger.debug(f"Finished streaming {chunk_count} chunks for chat {chat_id}")

                # Ensure a final 'done' message if stream ends unexpectedly
                if chunk_count == 0 or not chunk.get("done", False):
                     final_chunk = {"content": "Response processing finished.", "done": True}
                     yield f"data: {json.dumps(final_chunk)}\n\n"

            except asyncio.TimeoutError:
                logger.error(f"Timeout during LLM interaction for chat {chat_id}")
                error_chunk = {"content": "The request timed out.", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                ChatService.add_message(db, chat_id, "assistant", "Error: Request timed out.", context_documents={"error": "timeout"})
            except Exception as chat_error:
                logger.exception(f"Error getting chat stream for chat {chat_id}: {str(chat_error)}")
                error_chunk = {"content": f"An error occurred: {str(chat_error)}", "error": True, "done": True}
                yield f"data: {json.dumps(error_chunk)}\n\n"
                ChatService.add_message(db, chat_id, "assistant", f"Error: {str(chat_error)}", context_documents={"error": str(chat_error)})

        except Exception as e:
            logger.exception(f"Outer error in streaming response generator: {str(e)}\n{traceback.format_exc()}")
            error_chunk = {"content": f"An unexpected error occurred: {str(e)}", "error": True, "done": True}
            yield f"data: {json.dumps(error_chunk)}\n\n"


    logger.debug(f"Returning StreamingResponse for chat {chat_id}")
    return StreamingResponse(
        response_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked"
        }
    )


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
def read_messages(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all messages for a chat.
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

    messages = ChatService.get_messages(db, chat_id)
    return messages

@router.post("/{chat_id}/messages/{message_id}/feedback", response_model=MessageResponse)
def add_feedback(
    chat_id: str,
    message_id: str,
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Add feedback to a message.
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

    message = ChatService.add_feedback(
        db,
        message_id,
        feedback_in.feedback,
        feedback_in.feedback_text
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return message