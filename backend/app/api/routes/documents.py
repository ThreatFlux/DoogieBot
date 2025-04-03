from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func # Import func
import asyncio
import logging
from pydantic import BaseModel

from app.db.base import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
import zipfile
from app.services.zip_processor import process_zip_file
from app.schemas.document import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentUpdate,
    ManualDocumentCreate,
    ProcessingStatus,
    ProcessingConfig,
    PaginatedResponse,
    DocumentChunkIdResponse,  # Added
    DocumentChunkDetailResponse # Added
)
from app.services.document import DocumentService
from app.rag.document_processor import DocumentProcessor
from app.utils.deps import get_current_user, get_current_admin_user
from app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# GitHub repository schema
class GitHubRepositoryImport(BaseModel):
    repo_url: str
    branch: str = "main"
    file_types: str = "rst,txt,yaml,yml"  # Comma-separated list of file extensions
    background_processing: bool = False  # Whether to process in background

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None),
    process: bool = Form(False),
    generate_embeddings: bool = Form(True),
    embedding_provider: Optional[str] = Form(None),  # Use the configured provider if None
    embedding_model: Optional[str] = Form(None),  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Upload a document.
    """
    # Check file size
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024 * 1024)} MB",
        )

    # Upload document
    document = await DocumentService.upload_document(db, file, current_user.id, title)

    # Process document in background if requested
    if process:
        async def process_doc():
            # Create a new session for the background task
            from app.db.base import SessionLocal
            async_db = SessionLocal()
            try:
                processor = DocumentProcessor(
                    async_db, # Use new session
                    generate_embeddings=generate_embeddings,
                    embedding_provider=embedding_provider,
                    embedding_model=embedding_model
                )
                await processor.process_document(document)
            except Exception as e:
                logger.error(f"Error processing uploaded document in background: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            finally:
                async_db.close()

        background_tasks.add_task(process_doc)

    # Manually set chunk_count to 0 for newly uploaded docs before processing
    document.chunk_count = 0
    return document

@router.post("/upload-zip", response_model=dict)
async def upload_zip_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    process: bool = Form(True),
    generate_embeddings: bool = Form(True),
    embedding_provider: Optional[str] = Form(None),  # Use the configured provider if None
    embedding_model: Optional[str] = Form(None),  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Upload a zip file containing multiple documents to be processed for RAG.
    Each document in the zip will be extracted and processed individually.
    """
    # Check if the file is a zip file
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a zip archive",
        )

    # Check file size
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)

    # Allow larger size for zip files (3x normal limit)
    max_zip_size = settings.MAX_UPLOAD_SIZE * 3

    if file_size > max_zip_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Zip file too large. Maximum size is {max_zip_size / (1024 * 1024)} MB",
        )

    # Read the file content before passing to the background task
    file_content = contents  # We already read the file content for size check
    filename = file.filename

    # Create a unique ID for this upload job
    import uuid
    job_id = str(uuid.uuid4())

    # Process the zip file in the background
    async def process_zip():
        logger.info(f"Starting background processing of zip file {filename} (job_id: {job_id})")
        try:
            # Create a new database session for the background task
            from app.db.base import SessionLocal
            async_db = SessionLocal()

            try:
                documents, errors, total_files = await process_zip_file(
                    async_db,
                    file_content,
                    filename,
                    current_user.id,
                    process,
                    generate_embeddings,
                    embedding_provider,
                    embedding_model
                )

                logger.info(f"Job {job_id}: Processed {len(documents)} documents from zip file with {len(errors)} errors")

                # Store processing results in database or cache if needed
                # This could be used to show progress to the user

            finally:
                async_db.close()

        except Exception as e:
            logger.error(f"Job {job_id}: Error processing zip file: {str(e)}")
            import traceback
            logger.error(f"Job {job_id}: Traceback: {traceback.format_exc()}")

    # Add the task to the background tasks
    background_tasks.add_task(process_zip)

    logger.info(f"Added zip processing task to background tasks (job_id: {job_id})")

    return {
        "status": "success",
        "message": f"Zip file '{file.filename}' uploaded and being processed in the background. Documents will be available once processing is complete.",
        "filename": file.filename
    }

@router.post("/manual", response_model=DocumentResponse)
async def create_manual_document(
    document_in: ManualDocumentCreate,
    background_tasks: BackgroundTasks,
    process: bool = True,
    generate_embeddings: bool = True,
    embedding_provider: Optional[str] = None,  # Use the configured provider if None
    embedding_model: Optional[str] = None,  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a manual document entry.
    """
    document = DocumentService.create_manual_document(
        db,
        document_in.title,
        document_in.content,
        current_user.id,
        document_in.meta_data
    )

    # Process document in background if requested
    if process:
        async def process_doc():
            # Create a new session for the background task
            from app.db.base import SessionLocal
            async_db = SessionLocal()
            try:
                processor = DocumentProcessor(
                    async_db, # Use new session
                    generate_embeddings=generate_embeddings,
                    embedding_provider=embedding_provider,
                    embedding_model=embedding_model
                )
                await processor.process_document(document)
            except Exception as e:
                logger.error(f"Error processing manual document in background: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            finally:
                async_db.close()

        background_tasks.add_task(process_doc)

    # Manually set chunk_count to 0 for newly created docs before processing
    document.chunk_count = 0
    return document

@router.get("", response_model=PaginatedResponse[DocumentResponse])
def read_documents(
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 9,
    doc_type: str = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve documents with pagination and chunk counts.
    """
    # Calculate skip based on page and size
    skip = (page - 1) * size

    # Get documents and total count
    user_id_filter = current_user.id if current_user.role != "admin" else None
    documents, total_count = DocumentService.get_documents(
        db, skip=skip, limit=size, doc_type=doc_type, user_id=user_id_filter
    )

    # Calculate total pages
    pages = (total_count + size - 1) // size if total_count > 0 else 1

    # Return paginated response
    return PaginatedResponse[DocumentResponse](
        items=documents,
        total=total_count,
        page=page,
        size=size,
        pages=pages
    )

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def read_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific document by id.
    Note: Chunk details are fetched via separate endpoints.
    """
    document = DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if user has access to the document
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Get chunk count for the detail view
    chunk_count = db.query(func.count(DocumentChunk.id)).filter(DocumentChunk.document_id == document_id).scalar()
    document.chunk_count = chunk_count or 0

    # Remove the chunks attribute as it's fetched separately now
    # document.chunks = DocumentService.get_chunks(db, document_id)

    return document

# --- New Chunk Endpoints ---

@router.get("/{document_id}/chunks", response_model=List[DocumentChunkIdResponse])
def read_document_chunk_ids(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all chunk IDs and indices for a specific document.
    """
    # Check if document exists and user has access
    document = DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this document's chunks",
        )

    chunk_ids = DocumentService.get_chunk_ids(db, document_id)
    return chunk_ids

@router.get("/chunks/{chunk_id}", response_model=DocumentChunkDetailResponse)
def read_chunk_detail(
    chunk_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get the content and metadata for a specific chunk by its ID.
    """
    chunk = DocumentService.get_chunk_detail(db, chunk_id) # Raises 404 if not found

    # Check if user has access to the parent document
    document = DocumentService.get_document(db, chunk.document_id)
    if not document:
         # This case should ideally not happen if chunk exists, but good practice
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent document not found for this chunk",
        )
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this chunk",
        )

    return chunk

# --- End New Chunk Endpoints ---


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    document_in: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a document.
    """
    document = DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if user has access to the document
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    document = DocumentService.update_document(
        db, document_id, document_in.title, document_in.meta_data
    )

    # Get chunk count after update
    chunk_count = db.query(func.count(DocumentChunk.id)).filter(DocumentChunk.document_id == document_id).scalar()
    document.chunk_count = chunk_count or 0

    return document

@router.put("/{document_id}/content", response_model=DocumentDetailResponse)
def update_document_content(
    document_id: str,
    document_in: ManualDocumentCreate,
    background_tasks: BackgroundTasks,
    process: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a manual document's content.
    """
    document = DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if user has access to the document
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Check if document is a manual document
    if document.type != "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only manual documents can be edited",
        )

    # Update document content (this also deletes old chunks)
    document = DocumentService.update_document_content(
        db, document_id, document_in.title, document_in.content
    )

    # Process document in background if requested
    if process:
        async def process_doc():
            # Create a new session for the background task
            from app.db.base import SessionLocal
            async_db = SessionLocal()
            try:
                processor = DocumentProcessor(async_db) # Use new session
                await processor.process_document(document)
            except Exception as e:
                logger.error(f"Error processing updated manual document in background: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            finally:
                async_db.close()

        background_tasks.add_task(process_doc)

    # Set chunk count to 0 as chunks were deleted
    document.chunk_count = 0
    return document

@router.delete("/all", response_model=dict)
def delete_all_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Delete all documents. Admin only.
    """
    try:
        # Get all document IDs first
        doc_ids = [doc.id for doc in db.query(Document.id).all()]

        if not doc_ids:
            return {
                "status": "warning",
                "message": "No documents found to delete",
                "deleted_count": 0
            }

        deleted_count = 0
        for doc_id in doc_ids:
            try:
                # Use the service method which handles chunk deletion and file removal
                if DocumentService.delete_document(db, doc_id):
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting document {doc_id}: {str(e)}")
                # Rollback potentially needed if commit fails within delete_document
                db.rollback()
                continue # Try deleting the next one

        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} documents",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error in delete_all_documents: {str(e)}")
        db.rollback() # Ensure rollback on outer exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete all documents: {str(e)}"
        )

@router.delete("/{document_id}", response_model=dict) # Changed response model
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete a document.
    """
    document = DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if user has access to the document
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    result = DocumentService.delete_document(db, document_id)
    if result:
        return {"status": "success", "message": "Document deleted successfully"}
    else:
        # This case might not be reachable if get_document succeeded, but for completeness
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.post("/{document_id}/process", response_model=ProcessingStatus)
async def process_document(
    document_id: str,
    config: ProcessingConfig = None,
    embedding_provider: Optional[str] = None,  # Use the configured provider if None
    embedding_model: Optional[str] = None,  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Process a document (parse, chunk, and optionally embed).
    """
    document = DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if user has access to the document
    if document.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Use custom chunking config if provided
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP
    generate_embeddings = True  # Default to generating embeddings

    if config and config.chunking:
        chunk_size = config.chunking.chunk_size
        chunk_overlap = config.chunking.chunk_overlap

    # Check if embeddings should be generated
    if config and config.embedding is None:
        generate_embeddings = False
    elif config and config.embedding:
        # Use embedding config if provided
        embedding_provider = config.embedding.provider
        embedding_model = config.embedding.model

    # Process document
    processor = DocumentProcessor(
        db,
        chunk_size,
        chunk_overlap,
        generate_embeddings=generate_embeddings,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model
    )

    logger.info(f"Processing document {document_id} with generate_embeddings={generate_embeddings}")
    success, message, chunks = await processor.process_document(document)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )

    embedding_status = "with embeddings" if generate_embeddings else "without embeddings"
    return {
        "status": "success",
        "message": f"{message} {embedding_status}",
        "document_id": document_id,
        "total_chunks": chunks
    }

@router.post("/batch-process", response_model=dict)
async def batch_process_documents(
    document_ids: List[str],
    config: ProcessingConfig = None,
    embedding_provider: Optional[str] = None,  # Use the configured provider if None
    embedding_model: Optional[str] = None,  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Process multiple documents in batch. Admin only.
    """
    # Use custom chunking config if provided
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP
    generate_embeddings = True  # Default to generating embeddings

    if config and config.chunking:
        chunk_size = config.chunking.chunk_size
        chunk_overlap = config.chunking.chunk_overlap

    # Check if embeddings should be generated
    if config and config.embedding is None:
        generate_embeddings = False
    elif config and config.embedding:
        # Use embedding config if provided
        embedding_provider = config.embedding.provider
        embedding_model = config.embedding.model

    # Process documents
    processor = DocumentProcessor(
        db,
        chunk_size,
        chunk_overlap,
        generate_embeddings=generate_embeddings,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model
    )

    logger.info(f"Batch processing {len(document_ids)} documents with generate_embeddings={generate_embeddings}")
    results = await processor.process_documents(document_ids)

    # Add embedding status to results
    results["embedding_status"] = "with embeddings" if generate_embeddings else "without embeddings"

    return results

@router.post("/reprocess-all", response_model=dict)
async def reprocess_all_documents(
    background_tasks: BackgroundTasks,
    force_embeddings: bool = True,
    chunk_size: int = None,  # Optional custom chunk size
    chunk_overlap: int = None,  # Optional custom chunk overlap
    embedding_provider: Optional[str] = None,  # Use the configured provider if None
    embedding_model: Optional[str] = None,  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Reprocess all documents to add embeddings. Admin only.
    This is useful when you have existing documents without embeddings.
    """
    # Get all document IDs
    document_ids = [doc.id for doc in db.query(Document.id).all()]

    if not document_ids:
        return {
            "status": "warning",
            "message": "No documents found to reprocess",
            "document_count": 0
        }

    # Get active LLM config for logging
    from app.services.llm_config import LLMConfigService
    active_config = LLMConfigService.get_active_config(db)
    provider = embedding_provider or (active_config.embedding_provider if active_config else "default")
    model = embedding_model or (active_config.embedding_model if active_config else "default")

    # Use provided chunk size/overlap or default from settings
    chunk_size_to_use = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
    chunk_overlap_to_use = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP

    # Process documents in background
    async def reprocess_docs():
        # Create a new session for the background task
        from app.db.base import SessionLocal
        async_db = SessionLocal()
        try:
            processor = DocumentProcessor(
                async_db, # Use the new session
                chunk_size_to_use,
                chunk_overlap_to_use,
                generate_embeddings=force_embeddings,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model
            )
            logger.info(f"Reprocessing all documents with force_embeddings={force_embeddings}, chunk_size={chunk_size_to_use}, chunk_overlap={chunk_overlap_to_use}, using provider={provider}, model={model}")

            # First delete all existing chunks to ensure clean processing
            for doc_id in document_ids:
                DocumentService.delete_chunks(async_db, doc_id) # Use the new session

            results = await processor.process_documents(document_ids)
            logger.info(f"Reprocessing completed: {results}")
        except Exception as e:
            logger.error(f"Error in background reprocess task: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            async_db.close()


    background_tasks.add_task(reprocess_docs)

    return {
        "status": "started",
        "message": f"Reprocessing {len(document_ids)} documents in the background with embeddings using configured LLM settings",
        "document_count": len(document_ids),
        "using_provider": provider,
        "using_model": model,
        "chunk_size": chunk_size_to_use,
        "chunk_overlap": chunk_overlap_to_use
    }

@router.get("/embedding-status", response_model=dict)
async def get_embedding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Get the embedding status of all document chunks. Admin only.
    This helps diagnose issues with the embedding generation process.
    """
    # Get all document chunks
    chunks = db.query(DocumentChunk).all()

    total_chunks = len(chunks)
    chunks_with_embeddings = 0
    chunks_without_embeddings = 0

    # Count chunks with and without embeddings
    for chunk in chunks:
        if chunk.embedding:
            chunks_with_embeddings += 1
        else:
            chunks_without_embeddings += 1

    # Get document count
    document_count = db.query(Document).count()

    return {
        "total_documents": document_count,
        "total_chunks": total_chunks,
        "chunks_with_embeddings": chunks_with_embeddings,
        "chunks_without_embeddings": chunks_without_embeddings,
        "embedding_percentage": (chunks_with_embeddings / total_chunks * 100) if total_chunks > 0 else 0
    }

@router.post("/github", response_model=dict)
async def import_github_repository(
    background_tasks: BackgroundTasks,
    repo_data: GitHubRepositoryImport,
    process: bool = True,
    generate_embeddings: bool = True,
    embedding_provider: Optional[str] = None,  # Use the configured provider if None
    embedding_model: Optional[str] = None,  # Use the configured model if None
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Import documents from a GitHub repository.
    """
    try:
        logger.info(f"Importing GitHub repository: {repo_data.repo_url}, branch: {repo_data.branch}, file types: {repo_data.file_types}, background: {repo_data.background_processing}")

        # Create DocumentService instance
        document_service = DocumentService()

        # If background processing is requested, run the import in a background task
        if repo_data.background_processing:
            async def import_and_process():
                # Create a new session for the background task
                from app.db.base import SessionLocal
                async_db = SessionLocal()
                try:
                    # Import documents from GitHub
                    result = await document_service.import_github_repository(
                        async_db, # Use new session
                        repo_data.repo_url,
                        repo_data.branch,
                        repo_data.file_types.split(','),
                        current_user.id
                    )

                    if not result["success"]:
                        logger.error(f"Background GitHub import failed: {result['message']}")
                        return

                    # Process documents if requested
                    if process and result.get("document_ids"):
                        processor = DocumentProcessor(
                            async_db, # Use new session
                            generate_embeddings=generate_embeddings,
                            embedding_provider=embedding_provider,
                            embedding_model=embedding_model
                        )
                        await processor.process_documents(result["document_ids"])

                    logger.info(f"Background GitHub import completed: {result.get('imported_count', 0)} documents imported")
                except Exception as e:
                    logger.error(f"Error in background GitHub import: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                finally:
                    async_db.close()

            # Add the import task to background tasks
            background_tasks.add_task(import_and_process)

            # Return immediate success response
            return {
                "status": "success",
                "message": "GitHub repository import started in the background. Files will be processed automatically.",
                "background": True
            }
        else:
            # Import documents from GitHub synchronously
            result = await DocumentService.import_github_repository(
                db,
                repo_data.repo_url,
                repo_data.branch,
                repo_data.file_types.split(','),
                current_user.id
            )

            if not result["success"]:
                logger.error(f"GitHub import failed: {result['message']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST if "not found" in result["message"].lower() or "invalid" in result["message"].lower()
                        else status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["message"],
                )

            # Process documents in background if requested
            if process and result.get("document_ids"):
                async def process_docs():
                    # Create a new session for the background task
                    from app.db.base import SessionLocal
                    async_db = SessionLocal()
                    try:
                        processor = DocumentProcessor(
                            async_db, # Use new session
                            generate_embeddings=generate_embeddings,
                            embedding_provider=embedding_provider,
                            embedding_model=embedding_model
                        )
                        await processor.process_documents(result["document_ids"])
                    except Exception as e:
                        logger.error(f"Error processing GitHub docs in background: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                    finally:
                        async_db.close()

                background_tasks.add_task(process_docs)

        return {
            "status": "success",
            "message": f"Successfully imported {result.get('imported_count', 0)} documents from GitHub repository",
            "imported_count": result.get("imported_count", 0),
            "document_ids": result.get("document_ids", []),
            "background": False
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error importing GitHub repository: {error_message}")

        # Provide more specific error messages based on the exception
        if "rate limit" in error_message.lower():
            detail = "GitHub API rate limit exceeded. Please try again later or configure a GitHub API token."
        elif "not found" in error_message.lower():
            detail = f"Repository not found or inaccessible. Please check the URL and make sure the repository exists and is public."
        elif "network" in error_message.lower() or "timeout" in error_message.lower():
            detail = "Network error while connecting to GitHub. Please check your internet connection and try again."
        else:
            detail = f"Failed to import GitHub repository: {error_message}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )