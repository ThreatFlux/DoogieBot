"""
Database operations for the NetworkX implementation.
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
        graph: NetworkX graph
        db: Database session
        
    Returns:
        Tuple of (node_count, edge_count)
    """
    from app.models.document import GraphNode, GraphEdge, DocumentChunk
    
    start_time = time.time()
    logger.info("Building graph from database...")
    
    # Add nodes from database
    nodes_added = 0
    edges_added = 0
    
    # Get all nodes from database
    db_nodes = db.query(GraphNode).all()
    
    # Add nodes to graph
    for node in db_nodes:
        graph.add_node(
            node.id,
            content=node.content,
            type=node.node_type,
            metadata=json.loads(node.metadata) if node.metadata else {}
        )
        nodes_added += 1
    
    logger.info(f"Added {nodes_added} nodes from database")
    
    # Get all edges from database
    db_edges = db.query(GraphEdge).all()
    
    # Add edges to graph
    for edge in db_edges:
        # Check if nodes exist
        if edge.source_id not in graph.nodes:
            logger.warning(f"Source node {edge.source_id} does not exist")
            continue
        
        if edge.target_id not in graph.nodes:
            logger.warning(f"Target node {edge.target_id} does not exist")
            continue
        
        # Add edge
        graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation=edge.relation_type,
            weight=edge.weight,
            metadata=json.loads(edge.metadata) if edge.metadata else {}
        )
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
            graph.add_node(
                chunk_node_id,
                content=chunk.content,
                type="chunk",
                metadata={
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index
                }
            )
            nodes_added += 1
            
            # Extract entities from chunk content
            entities = extract_entities(chunk.content)
            
            # Add entity nodes and connect to chunk
            for entity_type, entity_text in entities:
                # Create a unique ID for the entity
                entity_id = f"entity_{entity_type}_{entity_text}"
                
                # Add entity node if it doesn't exist
                if entity_id not in graph.nodes:
                    graph.add_node(
                        entity_id,
                        content=entity_text,
                        type=entity_type,
                        metadata={}
                    )
                    nodes_added += 1
                
                # Connect chunk to entity
                graph.add_edge(
                    chunk_node_id,
                    entity_id,
                    relation="contains",
                    weight=1.0
                )
                edges_added += 1
        
        logger.info(f"Built graph from document chunks: {nodes_added} nodes, {edges_added} edges")
    
    end_time = time.time()
    logger.info(f"Graph building completed in {end_time - start_time:.2f}s")
    
    return (nodes_added, edges_added)

def save_to_database(graph, db: Session) -> Tuple[int, int]:
    """
    Save the graph to the database.
    
    Args:
        graph: NetworkX graph
        db: Database session
        
    Returns:
        Tuple of (node_count, edge_count)
    """
    from app.models.document import GraphNode, GraphEdge
    
    start_time = time.time()
    logger.info("Saving graph to database...")
    
    # Clear existing nodes and edges
    db.query(GraphEdge).delete()
    db.query(GraphNode).delete()
    
    nodes_added = 0
    edges_added = 0
    
    # Add nodes to database
    for node_id, node_data in graph.nodes(data=True):
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
    for source_id, target_id, edge_data in graph.edges(data=True):
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