from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from typing import List # Add List import
from pydantic import BaseModel # Add BaseModel import

# Import necessary components for the new route
from app.db.base import get_db
from app.core.config import settings
from app.services.user import UserService
from app.services.llm_config import LLMConfigService
from app.rag.singleton import rag_singleton
from app.utils.middleware import TrailingSlashMiddleware
from contextlib import asynccontextmanager
from app.utils.deps import get_current_admin_user # Import dependency
from app.models.user import User # Import User model
from app.llm.factory import LLMFactory # Import LLMFactory

# Create the app directory if it doesn't exist
app_dir = Path(__file__).parent / "app"
app_dir.mkdir(exist_ok=True)

# Create the uploads directory if it doesn't exist
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)

# Global flag to track if RAG singleton has been initialized
_rag_initialized = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (before yield)
    global _rag_initialized
    
    # Get DB session
    db = next(get_db())
    
    # Create first admin user if credentials are provided
    if settings.FIRST_ADMIN_EMAIL and settings.FIRST_ADMIN_PASSWORD:
        admin_email = settings.FIRST_ADMIN_EMAIL
        admin_password = settings.FIRST_ADMIN_PASSWORD
        
        admin_user = UserService.create_first_admin(db, admin_email, admin_password)
        if admin_user:
            print(f"Created first admin user: {admin_email}")
        else:
            print("Admin user already exists, skipping creation")
    else:
        print("Admin credentials not provided, skipping admin user creation")
    
    # Create default LLM configuration if needed
    default_config = LLMConfigService.create_default_config_if_needed(db)
    if default_config:
        print(f"Created default LLM configuration with provider: {default_config.provider}")
    else:
        print("LLM configuration already exists, skipping creation")
    
    # Initialize RAG singleton only if not already initialized
    if not _rag_initialized:
        print("Initializing RAG components (first worker)...")
        # Set the flag before initializing to prevent other workers from initializing
        _rag_initialized = True
        # Initialize with minimal loading - we'll load components on demand
        try:
            # Don't actually load the components yet, just set up the singleton
            # The actual loading will happen when the components are first accessed
            print("RAG singleton initialized, components will be loaded on demand")
        except Exception as e:
            print(f"Error initializing RAG singleton: {str(e)}")
    else:
        print("RAG singleton already initialized by another worker")
    
    yield  # This is where the app runs
    
    # Shutdown logic (after yield)
    # Add any cleanup code here if needed

# Create the FastAPI app
app = FastAPI(
    title="Doogie Chat Bot API",
    description="API for Doogie Chat Bot with Hybrid RAG system",
    version="0.1.0",
    # Disable automatic redirects for trailing slashes
    # This ensures URLs work consistently with or without trailing slashes
    redirect_slashes=False,
    # Add the lifespan context manager
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Add trailing slash middleware
app.add_middleware(TrailingSlashMiddleware)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Doogie Chat Bot API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include API router
from app.api.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)


# --- Direct Route Definition for Debugging ---
# Define response models directly here as they were in reranking.py
class RerankingProviderInfo(BaseModel):
    id: str
    name: str
    requires_api_key: bool
    requires_base_url: bool

class RerankingProviderResponse(BaseModel):
    providers: List[RerankingProviderInfo]

@app.get(f"{settings.API_V1_STR}/reranking/providers", response_model=RerankingProviderResponse, tags=["reranking"])
def get_reranking_providers_main(
    current_user: User = Depends(get_current_admin_user) # Use original dependency
):
    """Get available reranking providers (defined in main.py for debugging)."""
    print("--- DEBUG: Direct /reranking/providers route in main.py hit ---") # Add debug print
    # Start with providers known to have rerank APIs (or potential ones)
    known_providers = {
        # "cohere": {"name": "Cohere", "requires_api_key": True, "requires_base_url": False},
    }
    # Add our special "local" provider for sentence-transformers
    known_providers["local"] = {
        "name": "Local (SentenceTransformers)",
        "requires_api_key": False,
        "requires_base_url": False
    }
    provider_list = [
        RerankingProviderInfo(
            id=pid,
            name=pinfo["name"],
            requires_api_key=pinfo["requires_api_key"],
            requires_base_url=pinfo["requires_base_url"]
        ) for pid, pinfo in known_providers.items()
    ]
    return RerankingProviderResponse(providers=provider_list)
# --- End Direct Route Definition ---

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logging.error(f"HTTP error: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logging.error(f"Unhandled exception: {str(exc)} - Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)