"""
Core functionality for the NetworkX implementation of the graph interface.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import networkx as nx
import pickle
import os
import logging
import json

from app.rag.graph_interface import GraphInterface
from app.rag.networkx.search import search_graph
from app.rag.networkx.analysis import analyze_graph, get_important_nodes
from app.rag.networkx.db_ops import build_from_database, save_to_database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkXImplementation(GraphInterface):
    """
    NetworkX implementation of the graph interface.
    """
    
    def __init__(self, graph_path: str = "graph_rag.pkl"):
        """
        Initialize the NetworkX implementation.
        
        Args:
            graph_path: Path to save/load the graph
        """
        self.graph_path = graph_path
        # Use a MultiDiGraph instead of DiGraph to allow multiple edges between nodes
        # This is useful for representing different types of relationships
        self.graph = nx.MultiDiGraph()
    
    def add_node(
        self, 
        node_id: str, 
        content: str, 
        node_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a node to the graph.
        
        Args:
            node_id: Node ID
            content: Node content
            node_type: Node type (entity, concept, etc.)
            metadata: Optional node metadata
            
        Returns:
            Node ID
        """
        self.graph.add_node(
            node_id,
            content=content,
            type=node_type,
            metadata=metadata or {}
        )
        return node_id
    
    def add_edge(
        self, 
        source_id: str, 
        target_id: str, 
        relation_type: str, 
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Add an edge to the graph.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relation_type: Relation type
            weight: Edge weight
            metadata: Optional edge metadata
            
        Returns:
            Tuple of source and target node IDs
        """
        # Check if nodes exist
        if source_id not in self.graph.nodes:
            logger.warning(f"Source node {source_id} does not exist")
            return None
        
        if target_id not in self.graph.nodes:
            logger.warning(f"Target node {target_id} does not exist")
            return None
        
        # Add edge
        self.graph.add_edge(
            source_id,
            target_id,
            relation=relation_type,
            weight=weight,
            metadata=metadata or {}
        )
        
        return (source_id, target_id)
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data or None if not found
        """
        if node_id in self.graph.nodes:
            node_data = self.graph.nodes[node_id]
            return {
                'id': node_id,
                'content': node_data.get('content'),
                'type': node_data.get('type'),
                'metadata': node_data.get('metadata', {})
            }
        return None
    
    def get_neighbors(
        self, 
        node_id: str, 
        relation_type: Optional[str] = None,
        max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get neighbors of a node.
        
        Args:
            node_id: Node ID
            relation_type: Optional relation type filter
            max_depth: Maximum depth to traverse
            
        Returns:
            List of neighbor nodes
        """
        if node_id not in self.graph.nodes:
            return []
        
        # Use BFS to get neighbors up to max_depth
        visited = set([node_id])
        queue = [(node_id, 0)]  # (node_id, depth)
        neighbors = []
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            for neighbor_id in self.graph.neighbors(current_id):
                edge_data = self.graph.get_edge_data(current_id, neighbor_id)
                
                # Filter by relation type if specified
                if relation_type and edge_data.get('relation') != relation_type:
                    continue
                
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))
                    
                    # Add to results
                    node_data = self.graph.nodes[neighbor_id]
                    neighbors.append({
                        'id': neighbor_id,
                        'content': node_data.get('content'),
                        'type': node_data.get('type'),
                        'relation': edge_data.get('relation'),
                        'weight': edge_data.get('weight', 1.0),
                        'depth': depth + 1,
                        'metadata': node_data.get('metadata', {})
                    })
        
        return neighbors
    
    def search(
        self,
        query: str,
        node_types: Optional[List[str]] = None,
        relation_types: Optional[List[str]] = None,
        max_results: int = 5,
        fast_mode: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the graph for nodes matching the query.
        
        Args:
            query: Search query
            node_types: Optional list of node types to filter by
            relation_types: Optional list of relation types to filter by
            max_results: Maximum number of results to return
            fast_mode: Whether to use fast mode (limited semantic search)
            
        Returns:
            List of matching nodes
        """
        return search_graph(
            self.graph, 
            query, 
            node_types, 
            relation_types, 
            max_results, 
            fast_mode
        )
    
    def get_subgraph(
        self,
        node_ids: List[str],
        include_neighbors: bool = False,
        max_neighbors: int = 3
    ) -> nx.MultiDiGraph:
        """
        Get a subgraph containing the specified nodes.
        
        Args:
            node_ids: List of node IDs
            include_neighbors: Whether to include neighbors
            max_neighbors: Maximum number of neighbors to include per node
            
        Returns:
            NetworkX MultiDiGraph
        """
        # Start with the specified nodes
        nodes = set(node_id for node_id in node_ids if node_id in self.graph.nodes)
        
        # Add neighbors if requested
        if include_neighbors:
            for node_id in list(nodes):
                # Get top neighbors by weight
                neighbors = []
                for neighbor_id in self.graph.neighbors(node_id):
                    # For MultiDiGraph, get_edge_data returns a dict of edge keys to edge attributes
                    edge_data_dict = self.graph.get_edge_data(node_id, neighbor_id)
                    # Get the highest weight among all edges between these nodes
                    max_weight = max([data.get('weight', 0.0) for data in edge_data_dict.values()])
                    neighbors.append((neighbor_id, max_weight))
                
                # Sort by weight and add top neighbors
                neighbors.sort(key=lambda x: x[1], reverse=True)
                for neighbor_id, _ in neighbors[:max_neighbors]:
                    nodes.add(neighbor_id)
        
        # Create subgraph
        subgraph = self.graph.subgraph(nodes).copy()
        
        return subgraph
    
    def get_important_nodes(self, top_n: int = 10, method: str = "pagerank") -> List[Dict[str, Any]]:
        """
        Get the most important nodes in the graph using various centrality measures.
        
        Args:
            top_n: Number of top nodes to return
            method: Centrality method to use ('pagerank', 'betweenness', 'degree', 'eigenvector')
            
        Returns:
            List of important nodes with scores
        """
        return get_important_nodes(self.graph, top_n, method)
    
    def save(self) -> bool:
        """
        Save the graph to disk.
        
        Returns:
            Success flag
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.graph_path)), exist_ok=True)
            
            # Save graph
            with open(self.graph_path, 'wb') as f:
                pickle.dump(self.graph, f)
            
            logger.info(f"Graph saved to {self.graph_path} with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
            return True
        except Exception as e:
            logger.error(f"Error saving graph: {str(e)}")
            return False
    
    def load(self) -> bool:
        """
        Load the graph from disk.
        
        Returns:
            Success flag
        """
        try:
            # Check if file exists
            if not os.path.exists(self.graph_path):
                logger.warning(f"Graph file {self.graph_path} does not exist")
                return False
            
            # Load graph
            with open(self.graph_path, 'rb') as f:
                self.graph = pickle.load(f)
            
            logger.info(f"Graph loaded from {self.graph_path} with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
            return True
        except Exception as e:
            logger.error(f"Error loading graph: {str(e)}")
            return False
    
    def clear(self) -> None:
        """
        Clear the graph.
        """
        self.graph = nx.MultiDiGraph()
        logger.info("Graph cleared")
    
    def analyze_graph(self) -> Dict[str, Any]:
        """
        Analyze the graph structure and return statistics.
        
        Returns:
            Dictionary of graph statistics
        """
        return analyze_graph(self.graph)
    
    def build_from_database(self, db) -> Tuple[int, int]:
        """
        Build the graph from the database.
        
        Args:
            db: Database session
            
        Returns:
            Tuple of (node_count, edge_count)
        """
        # Clear existing graph
        self.clear()
        return build_from_database(self.graph, db)
    
    def save_to_database(self, db) -> Tuple[int, int]:
        """
        Save the graph to the database.
        
        Args:
            db: Database session
            
        Returns:
            Tuple of (node_count, edge_count)
        """
        return save_to_database(self.graph, db)
    
    def get_node_count(self) -> int:
        """
        Get the number of nodes in the graph.
        
        Returns:
            Node count
        """
        return len(self.graph.nodes)
    
    def get_edge_count(self) -> int:
        """
        Get the number of edges in the graph.
        
        Returns:
            Edge count
        """
        return len(self.graph.edges)