from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.models.document import DocumentChunk, GraphNode, GraphEdge
from app.rag.singleton import rag_singleton
from app.utils.deps import get_current_admin_user

router = APIRouter()

@router.delete("/chunks", response_model=dict)
async def delete_all_chunks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Delete all document chunks. Admin only.
    """
    # Delete all chunks
    db.query(DocumentChunk).delete()
    db.commit()
    
    return {
        "status": "success",
        "message": "All document chunks deleted"
    }

@router.post("/reset", response_model=dict)
async def reset_rag_system(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Reset the RAG system. This will clear all indexes and delete all document chunks. Admin only.
    """
    # Clear all indexes
    rag_singleton.clear_all()
    
    # Delete all chunks
    db.query(DocumentChunk).delete()
    
    # Delete all graph nodes and edges
    db.query(GraphEdge).delete()
    db.query(GraphNode).delete()
    
    db.commit()
    
    return {
        "status": "success",
        "message": "RAG system reset successfully"
    }