"""
Graph analysis functionality for the NetworkX implementation.
"""

from typing import List, Dict, Any
import networkx as nx
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_graph(graph) -> Dict[str, Any]:
    """
    Analyze the graph structure and return statistics.
    
    Args:
        graph: NetworkX graph
        
    Returns:
        Dictionary of graph statistics
    """
    if len(graph.nodes) == 0:
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
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    density = nx.density(graph)
    
    # Node type distribution
    node_types = {}
    for node_id, data in graph.nodes(data=True):
        node_type = data.get('type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    # Relation type distribution
    relation_types = {}
    for u, v, data in graph.edges(data=True):
        relation = data.get('relation', 'unknown')
        relation_types[relation] = relation_types.get(relation, 0) + 1
    
    # Average degree
    degrees = [d for n, d in graph.degree()]
    average_degree = sum(degrees) / len(degrees) if degrees else 0
    
    # Connected components (for undirected view of the graph)
    undirected_graph = graph.to_undirected()
    connected_components = nx.number_connected_components(undirected_graph)
    
    # Diameter and average shortest path length (for largest connected component)
    diameter = 0
    average_shortest_path_length = 0
    
    try:
        # Get largest connected component
        largest_cc = max(nx.connected_components(undirected_graph), key=len)
        largest_cc_graph = undirected_graph.subgraph(largest_cc).copy()
        
        # Calculate diameter and average shortest path length
        if len(largest_cc) > 1:
            diameter = nx.diameter(largest_cc_graph)
            average_shortest_path_length = nx.average_shortest_path_length(largest_cc_graph)
    except Exception as e:
        # If there's an error (e.g., graph is not connected), set to 0
        logger.warning(f"Error calculating path metrics: {str(e)}")
        diameter = 0
        average_shortest_path_length = 0
    
    # Clustering coefficient
    try:
        clustering_coefficient = nx.average_clustering(undirected_graph)
    except Exception as e:
        logger.warning(f"Error calculating clustering coefficient: {str(e)}")
        clustering_coefficient = 0
    
    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "average_degree": average_degree,
        "connected_components": connected_components,
        "diameter": diameter,
        "average_shortest_path_length": average_shortest_path_length,
        "clustering_coefficient": clustering_coefficient,
        "node_type_distribution": node_types,
        "relation_type_distribution": relation_types
    }

def get_important_nodes(graph, top_n: int = 10, method: str = "pagerank") -> List[Dict[str, Any]]:
    """
    Get the most important nodes in the graph using various centrality measures.
    
    Args:
        graph: NetworkX graph
        top_n: Number of top nodes to return
        method: Centrality method to use ('pagerank', 'betweenness', 'degree', 'eigenvector')
        
    Returns:
        List of important nodes with scores
    """
    if len(graph.nodes) == 0:
        return []
    
    # Calculate centrality based on method
    try:
        if method == "pagerank":
            # PageRank centrality
            centrality = nx.pagerank(graph, weight='weight')
        elif method == "betweenness":
            # Betweenness centrality
            centrality = nx.betweenness_centrality(graph, weight='weight')
        elif method == "degree":
            # Degree centrality
            centrality = nx.degree_centrality(graph)
        elif method == "eigenvector":
            # Eigenvector centrality
            try:
                centrality = nx.eigenvector_centrality(graph, weight='weight')
            except:
                # Fall back to pagerank if eigenvector fails to converge
                logger.warning("Eigenvector centrality failed to converge, falling back to PageRank")
                centrality = nx.pagerank(graph, weight='weight')
        else:
            # Default to pagerank
            logger.warning(f"Unknown centrality method '{method}', using PageRank")
            centrality = nx.pagerank(graph, weight='weight')
    except Exception as e:
        logger.error(f"Error calculating centrality with method {method}: {str(e)}")
        # Return empty list on error
        return []
    
    # Sort nodes by centrality score
    sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
    
    # Get top N nodes
    top_nodes = []
    for node_id, score in sorted_nodes[:top_n]:
        node_data = graph.nodes[node_id]
        top_nodes.append({
            'id': node_id,
            'content': node_data.get('content'),
            'type': node_data.get('type'),
            'score': score,
            'metadata': node_data.get('metadata', {})
        })
    
    return top_nodes