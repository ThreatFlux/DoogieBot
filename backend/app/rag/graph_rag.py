from typing import List, Dict, Any, Optional, Tuple, Set
import os
import logging
from sqlalchemy.orm import Session

from app.rag.graph_interface import GraphInterface
from app.rag.networkx_implementation import NetworkXImplementation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAG:
    """
    Graph-based RAG for relationship-aware retrieval.
    This class is a wrapper around a graph implementation that provides the actual functionality.
    """
    
    def __init__(self, graph_path: str = "graph_rag.pkl", implementation: Optional[GraphInterface] = None):
        """
        Initialize the GraphRAG.
        
        Args:
            graph_path: Path to save/load the graph
            implementation: Graph implementation to use (NetworkX or GraphRAG)
        """
        self.graph_path = graph_path
        
        # Use the provided implementation or create a default NetworkX implementation
        if implementation is not None:
            self.graph = implementation
            logger.info(f"Using provided graph implementation: {type(implementation).__name__}")
        else:
            self.graph = NetworkXImplementation(graph_path)
            logger.info("Using default NetworkX implementation")
    
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
        return self.graph.add_node(node_id, content, node_type, metadata)
    
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
        return self.graph.add_edge(source_id, target_id, relation_type, weight, metadata)
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data or None if not found
        """
        return self.graph.get_node(node_id)
    
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
        return self.graph.get_neighbors(node_id, relation_type, max_depth)
    
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
        return self.graph.search(query, node_types, relation_types, max_results, fast_mode)
    
    def get_subgraph(
        self,
        node_ids: List[str],
        include_neighbors: bool = False,
        max_neighbors: int = 3
    ) -> Any:
        """
        Get a subgraph containing the specified nodes.
        
        Args:
            node_ids: List of node IDs
            include_neighbors: Whether to include neighbors
            max_neighbors: Maximum number of neighbors to include per node
            
        Returns:
            A subgraph object (implementation-specific)
        """
        return self.graph.get_subgraph(node_ids, include_neighbors, max_neighbors)
    
    def get_important_nodes(self, top_n: int = 10, method: str = "pagerank") -> List[Dict[str, Any]]:
        """
        Get the most important nodes in the graph using various centrality measures.
        
        Args:
            top_n: Number of top nodes to return
            method: Centrality method to use ('pagerank', 'betweenness', 'degree', 'eigenvector')
            
        Returns:
            List of important nodes with scores
        """
        return self.graph.get_important_nodes(top_n, method)
    
    def save(self) -> bool:
        """
        Save the graph to disk.
        
        Returns:
            Success flag
        """
        return self.graph.save()
    
    def load(self) -> bool:
        """
        Load the graph from disk.
        
        Returns:
            Success flag
        """
        return self.graph.load()
    
    def clear(self) -> None:
        """
        Clear the graph.
        """
        self.graph.clear()
    
    def analyze_graph(self) -> Dict[str, Any]:
        """
        Analyze the graph structure and return statistics.
        
        Returns:
            Dictionary of graph statistics
        """
        return self.graph.analyze_graph()
    
    def build_from_database(self, db: Session) -> Tuple[int, int]:
        """
        Build the graph from the database.
        
        Args:
            db: Database session
            
        Returns:
            Tuple of (node_count, edge_count)
        """
        return self.graph.build_from_database(db)
    
    def save_to_database(self, db: Session) -> Tuple[int, int]:
        """
        Save the graph to the database.
        
        Args:
            db: Database session
            
        Returns:
            Tuple of (node_count, edge_count)
        """
        return self.graph.save_to_database(db)
    
    def get_node_count(self) -> int:
        """
        Get the number of nodes in the graph.
        
        Returns:
            Node count
        """
        return self.graph.get_node_count()
    
    def get_edge_count(self) -> int:
        """
        Get the number of edges in the graph.
        
        Returns:
            Edge count
        """
        return self.graph.get_edge_count()