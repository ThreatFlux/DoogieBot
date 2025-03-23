from typing import Any, Dict
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio
import logging

from app.db.base import get_db
from app.models.user import User
from app.models.document import DocumentChunk
from app.services.rag_config import RAGConfigService
from app.rag.hybrid_retriever import HybridRetriever
from app.utils.deps import get_current_admin_user
from app.core.config import settings
from app.schemas.rag import RAGBuildOptions

router = APIRouter()

@router.post("/build-indexes", response_model=Dict[str, Any])
async def build_indexes(
    build_options: RAGBuildOptions,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Build or rebuild RAG indexes. Admin only.
    
    Args:
        build_options: Options for building indexes
    """
    # Get RAG configuration from database
    rag_config = RAGConfigService.get_config(db)
    
    # Override configuration with request parameters if provided
    # Otherwise use the database configuration
    use_bm25 = build_options.use_bm25 and rag_config.bm25_enabled
    use_faiss = build_options.use_faiss and rag_config.faiss_enabled
    use_graph = build_options.use_graph and rag_config.graph_enabled
    rebuild = build_options.rebuild
    batch_size = build_options.batch_size
    
    logger = logging.getLogger(__name__)
    
    # Check if there are any document chunks to index
    chunk_count = db.query(DocumentChunk).count()
    if chunk_count == 0:
        return {
            "status": "warning",
            "message": "No document chunks found to index. Please upload and process documents first.",
            "document_count": 0,
            "chunk_count": 0
        }
    
    # Create retriever
    retriever = HybridRetriever(
        db,
        use_bm25=use_bm25,
        use_faiss=use_faiss,
        use_graph=use_graph
    )
    
    # Build indexes in background with timeout
    async def build():
        try:
            # Set a timeout for the build process
            timeout = settings.RAG_INDEX_BUILD_TIMEOUT
            logger.info(f"Starting index building with timeout of {timeout} seconds")
            
            # Use asyncio.wait_for to set a timeout
            result = await asyncio.wait_for(
                retriever.build_indexes(rebuild=rebuild),
                timeout=timeout
            )
            
            logger.info(f"Index building completed successfully: {result}")
            
            # Store the result in a database or cache for later retrieval
            # For now, we just log it
            print(f"Index building completed: {result}")
            
        except asyncio.TimeoutError:
            logger.error(f"Index building timed out after {timeout} seconds")
            print(f"Index building timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Error building indexes: {str(e)}")
            print(f"Error building indexes: {str(e)}")
    
    # Add the task to the background tasks
    background_tasks.add_task(build)
    
    # Estimate completion time based on chunk count
    # This is a rough estimate - actual time will vary based on hardware and data
    estimated_minutes = max(5, int(chunk_count / 100))  # Rough estimate: 100 chunks per minute
    
    return {
        "status": "started",
        "message": f"Index building started in the background with {chunk_count} document chunks. This may take {estimated_minutes} minutes or more to complete.",
        "rebuild": rebuild,
        "chunk_count": chunk_count,
        "estimated_completion_minutes": estimated_minutes,
        "timeout_seconds": settings.RAG_INDEX_BUILD_TIMEOUT,
        "indexes": {
            "bm25": {
                "enabled": use_bm25,
                "status": "indexing" if use_bm25 else "skipped"
            },
            "faiss": {
                "enabled": use_faiss,
                "status": "indexing" if use_faiss else "skipped"
            },
            "graph": {
                "enabled": use_graph,
                "implementation": rag_config.graph_implementation,
                "status": "indexing" if use_graph else "skipped"
            }
        }
    }