from typing import List, Dict, Any, Optional, Tuple, Set
import logging
from sqlalchemy.orm import Session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphInterface:
    """
    Abstract base class for graph implementations.
    This interface defines the methods that must be implemented by any graph implementation.
    """
    
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
        raise NotImplementedError("Subclasses must implement add_node")
    
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
        raise NotImplementedError("Subclasses must implement add_edge")
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data or None if not found
        """
        raise NotImplementedError("Subclasses must implement get_node")
    
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
        raise NotImplementedError("Subclasses must implement get_neighbors")
    
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
        raise NotImplementedError("Subclasses must implement search")
    
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
        raise NotImplementedError("Subclasses must implement get_subgraph")
    
    def get_important_nodes(
        self, 
        top_n: int = 10, 
        method: str = "pagerank"
    ) -> List[Dict[str, Any]]:
        """
        Get the most important nodes in the graph using various centrality measures.
        
        Args:
            top_n: Number of top nodes to return
            method: Centrality method to use ('pagerank', 'betweenness', 'degree', 'eigenvector')
            
        Returns:
            List of important nodes with scores
        """
        raise NotImplementedError("Subclasses must implement get_important_nodes")
    
    def save(self) -> bool:
        """
        Save the graph to disk.
        
        Returns:
            Success flag
        """
        raise NotImplementedError("Subclasses must implement save")
    
    def load(self) -> bool:
        """
        Load the graph from disk.
        
        Returns:
            Success flag
        """
        raise NotImplementedError("Subclasses must implement load")
    
    def clear(self) -> None:
        """
        Clear the graph.
        """
        raise NotImplementedError("Subclasses must implement clear")
    
    def analyze_graph(self) -> Dict[str, Any]:
        """
        Analyze the graph structure and return statistics.
        
        Returns:
            Dictionary of graph statistics
        """
        raise NotImplementedError("Subclasses must implement analyze_graph")
    
    def build_from_database(self, db: Session) -> Tuple[int, int]:
        """
        Build the graph from the database.
        
        Args:
            db: Database session
            
        Returns:
            Tuple of (node_count, edge_count)
        """
        raise NotImplementedError("Subclasses must implement build_from_database")
    
    def save_to_database(self, db: Session) -> Tuple[int, int]:
        """
        Save the graph to the database.
        
        Args:
            db: Database session
            
        Returns:
            Tuple of (node_count, edge_count)
        """
        raise NotImplementedError("Subclasses must implement save_to_database")
    
    def get_node_count(self) -> int:
        """
        Get the number of nodes in the graph.
        
        Returns:
            Node count
        """
        raise NotImplementedError("Subclasses must implement get_node_count")
    
    def get_edge_count(self) -> int:
        """
        Get the number of edges in the graph.
        
        Returns:
            Edge count
        """
        raise NotImplementedError("Subclasses must implement get_edge_count")