from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.base import get_db, init_db
from app.core.config import settings
from app.services.user import UserService
from app.services.llm_config import LLMConfigService
from app.rag.singleton import rag_singleton
from app.utils.middleware import TrailingSlashMiddleware
from contextlib import asynccontextmanager

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
    
    # Ensure database tables exist
    try:
        # Initialize the database (create tables if they don't exist)
        init_db()
        print("Database tables initialized")
    except Exception as e:
        print(f"Error initializing database tables: {str(e)}")
        print("This may be due to database connection issues. Will continue and try again later.")
    
    # Get DB session
    db = next(get_db())
    
    try:
        # Create first admin user if credentials are provided
        if settings.FIRST_ADMIN_EMAIL and settings.FIRST_ADMIN_PASSWORD:
            admin_email = settings.FIRST_ADMIN_EMAIL
            admin_password = settings.FIRST_ADMIN_PASSWORD
            
            # Try to create tables directly if they don't exist
            try:
                # Create users table directly with SQL if it doesn't exist
                import sqlite3
                conn = sqlite3.connect('./db/doogie.db')
                cursor = conn.cursor()
                
                # Check if users table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
                if not cursor.fetchone():
                    print("Creating users table manually...")
                    cursor.execute("""
                    CREATE TABLE users (
                        id VARCHAR PRIMARY KEY,
                        email VARCHAR NOT NULL UNIQUE,
                        hashed_password VARCHAR NOT NULL,
                        role VARCHAR(5) NOT NULL,
                        status VARCHAR(8) NOT NULL,
                        theme_preference VARCHAR NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        last_login TIMESTAMP
                    );
                    """)
                    conn.commit()
                    print("Users table created manually.")
                
                conn.close()
            except Exception as e:
                print(f"Error creating users table manually: {str(e)}")
            
            try:
                admin_user = UserService.create_first_admin(db, admin_email, admin_password)
                if admin_user:
                    print(f"Created first admin user: {admin_email}")
                else:
                    print("Admin user already exists, skipping creation")
            except Exception as e:
                print(f"Error creating admin user: {str(e)}")
                print("Will create admin user on first successful database connection.")
        else:
            print("Admin credentials not provided, skipping admin user creation")
        
        # Create default LLM configuration if needed
        try:
            default_config = LLMConfigService.create_default_config_if_needed(db)
            if default_config:
                print(f"Created default LLM configuration with provider: {default_config.provider}")
            else:
                print("LLM configuration already exists, skipping creation")
        except Exception as e:
            print(f"Error creating default LLM configuration: {str(e)}")
            print("Will create default LLM configuration on first successful database connection.")
    except Exception as e:
        # If there's an error (like missing tables), log it but continue
        print(f"Error during startup initialization: {str(e)}")
        print("This may be due to database not being fully initialized yet. The application will retry on first request.")
    
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