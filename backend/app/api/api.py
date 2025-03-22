from fastapi import APIRouter
from app.api.routes import auth, users, chats, documents, rag, llm

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])