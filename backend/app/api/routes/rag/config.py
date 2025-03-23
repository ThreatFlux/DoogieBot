from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.user import User
from app.rag.singleton import rag_singleton
from app.utils.deps import get_current_user, get_current_admin_user
from app.services.rag_config import RAGConfigService
from app.schemas.rag import RAGComponentToggle, GraphImplementationUpdate

router = APIRouter()

@router.post("/toggle-component", response_model=Dict[str, Any])
async def toggle_rag_component(
    toggle_data: RAGComponentToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Toggle a RAG component on or off. Admin only.
    """
    # Validate component
    if toggle_data.component not in ['bm25', 'faiss', 'graph']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component: {toggle_data.component}. Must be one of: bm25, faiss, graph"
        )
    
    # Update component status in database
    config = RAGConfigService.update_component_status(db, toggle_data.component, toggle_data.enabled)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update {toggle_data.component} status"
        )
    
    return {
        "status": "success",
        "component": toggle_data.component,
        "enabled": toggle_data.enabled
    }

@router.post("/graph/implementation", response_model=Dict[str, Any])
async def update_graph_implementation(
    implementation_data: GraphImplementationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Update the graph implementation. Admin only.
    
    This will change the implementation used for the graph RAG component.
    Note: This will not rebuild the graph. You need to rebuild the graph after changing the implementation.
    """
    # Update implementation in database
    config = RAGConfigService.update_graph_implementation(db, implementation_data.implementation)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update graph implementation"
        )
    
    # Reset the singleton to use the new implementation
    rag_singleton.reset_graph()
    
    return {
        "status": "success",
        "implementation": implementation_data.implementation,
        "message": "Graph implementation updated. You need to rebuild the graph for the changes to take effect."
    }