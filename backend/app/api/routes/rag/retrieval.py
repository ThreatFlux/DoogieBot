from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.models.document import DocumentChunk
from app.services.document import DocumentService
from app.services.rag_config import RAGConfigService
from app.rag.hybrid_retriever import HybridRetriever
from app.utils.deps import get_current_user
from app.schemas.rag import RAGRetrieveOptions

router = APIRouter()

@router.post("/retrieve", response_model=List[dict])
async def retrieve(
    options: RAGRetrieveOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve relevant documents using the hybrid approach.
    
    Args:
        options: Retrieval options
    """
    # Get RAG configuration from database
    rag_config = RAGConfigService.get_config(db)
    # Check if there are any document chunks to search
    chunk_count = db.query(DocumentChunk).count()
    if chunk_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document chunks found to search. Please upload and process documents first."
        )
    
    # Create retriever
    retriever = HybridRetriever(
        db,
        use_bm25=options.use_bm25,
        use_faiss=options.use_faiss,
        use_graph=options.use_graph
    )
    
    # Retrieve documents
    results = await retriever.retrieve(
        query=options.query,
        query_embedding=options.query_embedding,
        top_k=options.top_k,
        rerank=options.rerank,
        fast_mode=options.fast_mode
    )
    
    return results

@router.get("/chunks/{chunk_id}", response_model=Dict[str, Any])
async def get_chunk_info(
    chunk_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get information about a document chunk, including its document ID and title.
    """
    # Get the chunk
    chunk = DocumentService.get_chunk(db, chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )
    
    # Get the document
    document = DocumentService.get_document(db, chunk.document_id)
    
    # Return chunk info with document details
    return {
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "document_id": chunk.document_id,
        "document_title": document.title if document else "Unknown document",
        "document_type": document.type if document else None,
        "document_filename": document.filename if document else None,
        "created_at": chunk.created_at
    }