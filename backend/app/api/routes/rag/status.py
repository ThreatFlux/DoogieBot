from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.services.rag_config import RAGConfigService
from app.rag.singleton import rag_singleton
from app.utils.deps import get_current_user

router = APIRouter()

@router.get("/stats", response_model=Dict[str, Any])
async def get_rag_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get RAG statistics - alias for get_rag_status.
    """
    return await get_rag_status(db, current_user)

@router.get("/status", response_model=Dict[str, Any])
async def get_rag_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get the status of the RAG system.
    """
    # Get document and chunk counts
    document_count = db.query(Document).count()
    chunk_count = db.query(DocumentChunk).count()
    
    # Get last updated timestamp
    latest_chunk = db.query(DocumentChunk).order_by(DocumentChunk.created_at.desc()).first()
    last_updated = latest_chunk.created_at if latest_chunk else None
    
    # Ensure singleton is initialized
    rag_singleton.initialize()
    
    # Get references to singleton instances
    bm25_index = rag_singleton.get_bm25_index()
    faiss_store = rag_singleton.get_faiss_store()
    graph_rag = rag_singleton.get_graph_rag()
    
    # Get counts from the singleton instances
    bm25_doc_count = len(bm25_index.doc_ids) if bm25_index else 0
    faiss_doc_count = len(faiss_store.doc_ids) if faiss_store else 0
    graph_node_count = graph_rag.get_node_count() if graph_rag else 0
    graph_edge_count = graph_rag.get_edge_count() if graph_rag else 0
    
    # Get RAG component configuration
    rag_config = RAGConfigService.get_config(db)
    
    return {
        "document_count": document_count,
        "chunk_count": chunk_count,
        "last_updated": last_updated,
        "bm25_status": {
            "enabled": rag_config.bm25_enabled,
            "document_count": bm25_doc_count,
            "last_indexed": None,  # Would need to store this in the index
            "status": "idle"
        },
        "faiss_status": {
            "enabled": rag_config.faiss_enabled,
            "document_count": faiss_doc_count,
            "last_indexed": None,  # Would need to store this in the index
            "status": "idle"
        },
        "graph_status": {
            "enabled": rag_config.graph_enabled,
            "implementation": rag_config.graph_implementation,
            "document_count": graph_node_count,  # Use node count as document count
            "node_count": graph_node_count,
            "edge_count": graph_edge_count,
            "last_indexed": None,  # Would need to store this in the index
            "status": "idle"
        }
    }