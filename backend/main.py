from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.config import settings
from app.services.user import UserService
from app.services.llm_config import LLMConfigService
from app.rag.singleton import rag_singleton

# Create the app directory if it doesn't exist
app_dir = Path(__file__).parent / "app"
app_dir.mkdir(exist_ok=True)

# Create the uploads directory if it doesn't exist
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)

# Create the FastAPI app
app = FastAPI(
    title="Doogie Chat Bot API",
    description="API for Doogie Chat Bot with Hybrid RAG system",
    version="0.1.0",
)

# Add CORS middleware with environment-specific configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

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

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# Global flag to track if RAG singleton has been initialized
_rag_initialized = False

# Startup event to create first admin user and default LLM configuration
@app.on_event("startup")
async def startup_initialization():
    global _rag_initialized
    
    # Get DB session
    db = next(get_db())
    
    # Create first admin user
    admin_email = settings.FIRST_ADMIN_EMAIL
    admin_password = settings.FIRST_ADMIN_PASSWORD
    
    admin_user = UserService.create_first_admin(db, admin_email, admin_password)
    if admin_user:
        print(f"Created first admin user: {admin_email}")
    else:
        print("Admin user already exists, skipping creation")
    
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)