from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio
import logging

from app.db.base import get_db
from app.models.user import User
from app.models.document import DocumentChunk
from app.services.rag_config import RAGConfigService
from app.rag.singleton import rag_singleton
from app.utils.deps import get_current_user, get_current_admin_user
from app.core.config import settings

router = APIRouter()

@router.get("/graph/analyze", response_model=Dict[str, Any])
async def analyze_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Analyze the graph structure and return statistics.
    """
    # Get singleton instance
    graph_rag = rag_singleton.get_graph_rag()
    
    # Check if graph is loaded
    if not graph_rag or graph_rag.get_node_count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not found or empty",
        )
    
    # Analyze graph
    analysis = graph_rag.analyze_graph()
    
    return analysis

@router.get("/graph/important-nodes", response_model=List[Dict[str, Any]])
async def get_important_nodes(
    method: str = "pagerank",
    top_n: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get the most important nodes in the graph using various centrality measures.
    
    Args:
        method: Centrality method to use ('pagerank', 'betweenness', 'degree', 'eigenvector')
        top_n: Number of top nodes to return
    """
    # Validate method
    valid_methods = ["pagerank", "betweenness", "degree", "eigenvector"]
    if method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid method. Must be one of: {', '.join(valid_methods)}",
        )
    
    # Get singleton instance
    graph_rag = rag_singleton.get_graph_rag()
    
    # Check if graph is loaded
    if not graph_rag or graph_rag.get_node_count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not found or empty",
        )
    
    # Get important nodes
    important_nodes = graph_rag.get_important_nodes(top_n=top_n, method=method)
    
    return important_nodes

@router.get("/graph/implementation", response_model=Dict[str, str])
async def get_graph_implementation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get the current graph implementation.
    """
    implementation = RAGConfigService.get_graph_implementation(db)
    
    return {
        "implementation": implementation
    }

@router.get("/graph/nodes/{node_id}", response_model=dict)
async def get_graph_node(
    node_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a graph node by ID.
    """
    # Get singleton instance
    graph = rag_singleton.get_graph_rag()
    
    # Check if graph is loaded
    if not graph or graph.get_node_count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not found or empty",
        )
    
    node = graph.get_node(node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )
    
    return node

@router.get("/graph/nodes/{node_id}/neighbors", response_model=List[dict])
async def get_node_neighbors(
    node_id: str,
    relation_type: Optional[str] = None,
    max_depth: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get neighbors of a graph node.
    """
    # Get singleton instance
    graph = rag_singleton.get_graph_rag()
    
    # Check if graph is loaded
    if not graph or graph.get_node_count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not found or empty",
        )
    
    neighbors = graph.get_neighbors(
        node_id=node_id,
        relation_type=relation_type,
        max_depth=max_depth
    )
    
    return neighbors

@router.post("/graph/search", response_model=List[dict])
async def search_graph(
    query: str,
    node_types: Optional[List[str]] = None,
    relation_types: Optional[List[str]] = None,
    max_results: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Search the graph for nodes matching the query.
    """
    # Get singleton instance
    graph = rag_singleton.get_graph_rag()
    
    # Check if graph is loaded
    if not graph or graph.get_node_count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not found or empty",
        )
    
    results = graph.search(
        query=query,
        node_types=node_types,
        relation_types=relation_types,
        max_results=max_results
    )
    
    return results

@router.post("/graph/rebuild", response_model=dict)
async def rebuild_graph(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Rebuild the graph from database. Admin only.
    """
    logger = logging.getLogger(__name__)
    
    # Check if there are any document chunks to use for graph building
    chunk_count = db.query(DocumentChunk).count()
    if chunk_count == 0:
        return {
            "status": "warning",
            "message": "No document chunks found to build graph. Please upload and process documents first.",
            "chunk_count": 0
        }
    
    # Get the current graph implementation
    implementation = RAGConfigService.get_graph_implementation(db)
    
    # Create a new graph instance with the current implementation
    graph = rag_singleton.get_graph_rag()
    
    # Rebuild graph in background with timeout
    async def rebuild():
        try:
            # Set a timeout for the build process
            timeout = settings.RAG_INDEX_BUILD_TIMEOUT
            logger.info(f"Starting graph rebuilding with timeout of {timeout} seconds")
            
            # Use asyncio.wait_for to set a timeout
            async def build_and_save():
                nodes, edges = graph.build_from_database(db)
                graph.save()
                return nodes, edges
                
            nodes, edges = await asyncio.wait_for(
                build_and_save(),
                timeout=timeout
            )
            
            logger.info(f"Graph rebuilding completed successfully with {nodes} nodes and {edges} edges")
            
        except asyncio.TimeoutError:
            logger.error(f"Graph rebuilding timed out after {timeout} seconds")
            print(f"Graph rebuilding timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Error rebuilding graph: {str(e)}")
            print(f"Error rebuilding graph: {str(e)}")
    
    # Add the task to the background tasks
    background_tasks.add_task(rebuild)
    
    # Estimate completion time based on chunk count
    estimated_minutes = max(5, int(chunk_count / 100))  # Rough estimate: 100 chunks per minute
    
    return {
        "status": "started",
        "message": f"Graph rebuilding started in the background with {chunk_count} document chunks. This may take {estimated_minutes} minutes or more to complete.",
        "implementation": implementation,
        "chunk_count": chunk_count,
        "estimated_completion_minutes": estimated_minutes,
        "timeout_seconds": settings.RAG_INDEX_BUILD_TIMEOUT
    }

@router.post("/graph/save-to-database", response_model=dict)
async def save_graph_to_database(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    Save the graph to the database. Admin only.
    """
    # Get singleton instance
    graph = rag_singleton.get_graph_rag()
    
    # Check if graph is loaded
    if not graph or graph.get_node_count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not found or empty",
        )
    
    # Save graph to database in background
    async def save():
        try:
            nodes, edges = graph.save_to_database(db)
            print(f"Graph saved to database with {nodes} nodes and {edges} edges")
        except Exception as e:
            print(f"Error saving graph to database: {str(e)}")
    
    # Add the task to the background tasks
    background_tasks.add_task(save)
    
    return {
        "status": "started",
        "message": "Graph saving to database started in the background"
    }