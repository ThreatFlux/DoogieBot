"""
Graph analysis functionality for the GraphRAG implementation.
"""

from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_graph(graph) -> Dict[str, Any]:
    """
    Analyze the graph structure and return statistics.
    
    Args:
        graph: GraphRAG graph
        
    Returns:
        Dictionary of graph statistics
    """
    try:
        # Check if we're using the actual GraphRAG library
        if hasattr(graph, 'analyze'):
            # GraphRAG library method
            return graph.analyze()
        else:
            # Fallback implementation
            return _fallback_analyze_graph(graph)
    except Exception as e:
        logger.error(f"Error analyzing graph: {str(e)}")
        # Return empty stats on error
        return {
            "node_count": 0,
            "edge_count": 0,
            "density": 0,
            "average_degree": 0,
            "connected_components": 0,
            "diameter": 0,
            "average_shortest_path_length": 0,
            "clustering_coefficient": 0,
            "node_type_distribution": {},
            "relation_type_distribution": {}
        }

def _fallback_analyze_graph(graph) -> Dict[str, Any]:
    """
    Fallback implementation for graph analysis when GraphRAG library is not available.
    """
    if len(graph["nodes"]) == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "density": 0,
            "average_degree": 0,
            "connected_components": 0,
            "diameter": 0,
            "average_shortest_path_length": 0,
            "clustering_coefficient": 0,
            "node_type_distribution": {},
            "relation_type_distribution": {}
        }
    
    # Basic statistics
    node_count = len(graph["nodes"])
    edge_count = len(graph["edges"])
    
    # Calculate density
    max_possible_edges = node_count * (node_count - 1)
    density = edge_count / max_possible_edges if max_possible_edges > 0 else 0
    
    # Node type distribution
    node_types = {}
    for node_id, data in graph["nodes"].items():
        node_type = data.get('type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    # Relation type distribution
    relation_types = {}
    for edge_key, data in graph["edges"].items():
        relation = data.get('relation', 'unknown')
        relation_types[relation] = relation_types.get(relation, 0) + 1
    
    # Average degree
    degrees = [len(graph["neighbors"].get(node_id, [])) for node_id in graph["nodes"]]
    average_degree = sum(degrees) / len(degrees) if degrees else 0
    
    # For more complex metrics like connected components, diameter, etc.,
    # we would need to implement graph algorithms, which is beyond the scope
    # of this fallback implementation. Instead, we'll return placeholder values.
    
    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "average_degree": average_degree,
        "connected_components": 1,  # Placeholder
        "diameter": 0,  # Placeholder
        "average_shortest_path_length": 0,  # Placeholder
        "clustering_coefficient": 0,  # Placeholder
        "node_type_distribution": node_types,
        "relation_type_distribution": relation_types
    }

def get_important_nodes(graph, top_n: int = 10, method: str = "pagerank") -> List[Dict[str, Any]]:
    """
    Get the most important nodes in the graph using various centrality measures.
    
    Args:
        graph: GraphRAG graph
        top_n: Number of top nodes to return
        method: Centrality method to use ('pagerank', 'betweenness', 'degree', 'eigenvector')
        
    Returns:
        List of important nodes with scores
    """
    try:
        # Check if we're using the actual GraphRAG library
        if hasattr(graph, 'get_important_nodes'):
            # GraphRAG library method
            return graph.get_important_nodes(top_n=top_n, method=method)
        else:
            # Fallback implementation
            return _fallback_get_important_nodes(graph, top_n, method)
    except Exception as e:
        logger.error(f"Error getting important nodes: {str(e)}")
        # Return empty list on error
        return []

def _fallback_get_important_nodes(graph, top_n: int = 10, method: str = "pagerank") -> List[Dict[str, Any]]:
    """
    Fallback implementation for getting important nodes when GraphRAG library is not available.
    """
    if len(graph["nodes"]) == 0:
        return []
    
    # For a proper implementation of centrality measures like PageRank,
    # we would need to implement complex graph algorithms.
    # As a simple approximation, we'll use degree centrality (number of connections)
    # for all methods in this fallback implementation.
    
    # Calculate degree for each node
    node_degrees = {}
    for node_id in graph["nodes"]:
        degree = len(graph["neighbors"].get(node_id, []))
        node_degrees[node_id] = degree
    
    # Sort nodes by degree
    sorted_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)
    
    # Get top N nodes
    top_nodes = []
    for node_id, score in sorted_nodes[:top_n]:
        node_data = graph["nodes"][node_id]
        # Normalize score to be between 0 and 1
        normalized_score = score / max(node_degrees.values()) if max(node_degrees.values()) > 0 else 0
        top_nodes.append({
            'id': node_id,
            'content': node_data.get('content'),
            'type': node_data.get('type'),
            'score': normalized_score,
            'metadata': node_data.get('metadata', {})
        })
    
    return top_nodes