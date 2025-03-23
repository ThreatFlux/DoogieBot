"""
Database operations for the GraphRAG implementation.
"""

from typing import Tuple
import logging
import json
import time
from sqlalchemy.orm import Session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_from_database(graph, db: Session) -> Tuple[int, int]:
    """
    Build the graph from the database.
    
    Args:
        graph: GraphRAG graph
        db: Database session
        
    Returns:
        Tuple of (node_count, edge_count)
    """
    try:
        # Check if we're using the actual GraphRAG library
        if hasattr(graph, 'build_from_database'):
            # GraphRAG library method
            return graph.build_from_database(db)
        else:
            # Fallback implementation
            return _fallback_build_from_database(graph, db)
    except Exception as e:
        logger.error(f"Error building graph from database: {str(e)}")
        return (0, 0)

def _fallback_build_from_database(graph, db: Session) -> Tuple[int, int]:
    """
    Fallback implementation for building graph from database when GraphRAG library is not available.
    """
    from app.models.document import GraphNode, GraphEdge, DocumentChunk
    
    start_time = time.time()
    logger.info("Building graph from database (fallback implementation)...")
    
    # Add nodes from database
    nodes_added = 0
    edges_added = 0
    
    # Get all nodes from database
    db_nodes = db.query(GraphNode).all()
    
    # Add nodes to graph
    for node in db_nodes:
        # Add node to graph
        graph["nodes"][node.id] = {
            "content": node.content,
            "type": node.node_type,
            "metadata": json.loads(node.metadata) if node.metadata else {}
        }
        # Initialize neighbors list
        graph["neighbors"][node.id] = []
        nodes_added += 1
    
    logger.info(f"Added {nodes_added} nodes from database")
    
    # Get all edges from database
    db_edges = db.query(GraphEdge).all()
    
    # Add edges to graph
    for edge in db_edges:
        # Check if nodes exist
        if edge.source_id not in graph["nodes"]:
            logger.warning(f"Source node {edge.source_id} does not exist")
            continue
        
        if edge.target_id not in graph["nodes"]:
            logger.warning(f"Target node {edge.target_id} does not exist")
            continue
        
        # Add edge to graph
        edge_key = (edge.source_id, edge.target_id)
        graph["edges"][edge_key] = {
            "relation": edge.relation_type,
            "weight": edge.weight,
            "metadata": json.loads(edge.metadata) if edge.metadata else {}
        }
        # Update neighbors
        if edge.target_id not in graph["neighbors"][edge.source_id]:
            graph["neighbors"][edge.source_id].append(edge.target_id)
        edges_added += 1
    
    logger.info(f"Added {edges_added} edges from database")
    
    # If no nodes were loaded from the database, try to build from document chunks
    if nodes_added == 0:
        logger.info("No nodes found in database, building from document chunks...")
        
        # Get all document chunks
        chunks = db.query(DocumentChunk).all()
        
        # Extract entities and build graph
        for chunk in chunks:
            # Create a node for the chunk
            chunk_node_id = f"chunk_{chunk.id}"
            graph["nodes"][chunk_node_id] = {
                "content": chunk.content,
                "type": "chunk",
                "metadata": {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index
                }
            }
            graph["neighbors"][chunk_node_id] = []
            nodes_added += 1
            
            # Extract entities from chunk content
            entities = extract_entities(chunk.content)
            
            # Add entity nodes and connect to chunk
            for entity_type, entity_text in entities:
                # Create a unique ID for the entity
                entity_id = f"entity_{entity_type}_{entity_text}"
                
                # Add entity node if it doesn't exist
                if entity_id not in graph["nodes"]:
                    graph["nodes"][entity_id] = {
                        "content": entity_text,
                        "type": entity_type,
                        "metadata": {}
                    }
                    graph["neighbors"][entity_id] = []
                    nodes_added += 1
                
                # Connect chunk to entity
                edge_key = (chunk_node_id, entity_id)
                graph["edges"][edge_key] = {
                    "relation": "contains",
                    "weight": 1.0,
                    "metadata": {}
                }
                if entity_id not in graph["neighbors"][chunk_node_id]:
                    graph["neighbors"][chunk_node_id].append(entity_id)
                edges_added += 1
        
        logger.info(f"Built graph from document chunks: {nodes_added} nodes, {edges_added} edges")
    
    end_time = time.time()
    logger.info(f"Graph building completed in {end_time - start_time:.2f}s")
    
    return (nodes_added, edges_added)

def save_to_database(graph, db: Session) -> Tuple[int, int]:
    """
    Save the graph to the database.
    
    Args:
        graph: GraphRAG graph
        db: Database session
        
    Returns:
        Tuple of (node_count, edge_count)
    """
    try:
        # Check if we're using the actual GraphRAG library
        if hasattr(graph, 'save_to_database'):
            # GraphRAG library method
            return graph.save_to_database(db)
        else:
            # Fallback implementation
            return _fallback_save_to_database(graph, db)
    except Exception as e:
        logger.error(f"Error saving graph to database: {str(e)}")
        return (0, 0)

def _fallback_save_to_database(graph, db: Session) -> Tuple[int, int]:
    """
    Fallback implementation for saving graph to database when GraphRAG library is not available.
    """
    from app.models.document import GraphNode, GraphEdge
    
    start_time = time.time()
    logger.info("Saving graph to database (fallback implementation)...")
    
    # Clear existing nodes and edges
    db.query(GraphEdge).delete()
    db.query(GraphNode).delete()
    
    nodes_added = 0
    edges_added = 0
    
    # Add nodes to database
    for node_id, node_data in graph["nodes"].items():
        # Create node
        db_node = GraphNode(
            id=node_id,
            content=node_data.get('content', ''),
            node_type=node_data.get('type', 'unknown'),
            metadata=json.dumps(node_data.get('metadata', {}))
        )
        
        # Add to database
        db.add(db_node)
        nodes_added += 1
        
        # Commit every 1000 nodes to avoid memory issues
        if nodes_added % 1000 == 0:
            db.commit()
            logger.info(f"Committed {nodes_added} nodes")
    
    # Commit any remaining nodes
    db.commit()
    logger.info(f"Added {nodes_added} nodes to database")
    
    # Add edges to database
    for edge_key, edge_data in graph["edges"].items():
        source_id, target_id = edge_key
        
        # Create edge
        db_edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=edge_data.get('relation', 'unknown'),
            weight=edge_data.get('weight', 1.0),
            metadata=json.dumps(edge_data.get('metadata', {}))
        )
        
        # Add to database
        db.add(db_edge)
        edges_added += 1
        
        # Commit every 1000 edges to avoid memory issues
        if edges_added % 1000 == 0:
            db.commit()
            logger.info(f"Committed {edges_added} edges")
    
    # Commit any remaining edges
    db.commit()
    logger.info(f"Added {edges_added} edges to database")
    
    end_time = time.time()
    logger.info(f"Graph saving completed in {end_time - start_time:.2f}s")
    
    return (nodes_added, edges_added)

def extract_entities(text):
    """
    Simple entity extraction using regex patterns.
    
    Args:
        text: Text to extract entities from
        
    Returns:
        List of (entity_type, entity_text) tuples
    """
    import re
    # This is a very basic implementation - in a real system, use NER
    entities = []
    
    # Look for capitalized phrases (potential named entities)
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text):
        entities.append(("entity", match.group(1)))
    
    return entities