"""
Core functionality for the GraphRAG implementation of the graph interface.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import pickle
import os
import logging
import json
from sqlalchemy.orm import Session

from app.rag.graph_interface import GraphInterface
from app.rag.graphrag.search import search_graph
from app.rag.graphrag.analysis import analyze_graph, get_important_nodes
from app.rag.graphrag.db_ops import build_from_database, save_to_database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGImplementation(GraphInterface):
    """
    GraphRAG implementation of the graph interface.
    This implementation uses the specialized GraphRAG library for improved performance.
    """
    
    def __init__(self, graph_path: str = "graph_rag.pkl"):
        """
        Initialize the GraphRAG implementation.
        
        Args:
            graph_path: Path to save/load the graph
        """
        self.graph_path = graph_path
        
        # Import GraphRAG here to avoid import errors if the library is not installed
        try:
            import graphrag
            self.graph = graphrag.Graph()
            logger.info("GraphRAG library initialized successfully")
        except ImportError:
            logger.error("GraphRAG library not found. Please install it with 'pip install graphrag'")
            # Fall back to a simple dictionary-based graph structure
            self.graph = {
                "nodes": {},  # node_id -> node_data
                "edges": {},  # (source_id, target_id) -> edge_data
                "neighbors": {}  # node_id -> list of neighbor_ids
            }
    
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
        try:
            # Check if we're using the actual GraphRAG library
            if hasattr(self.graph, 'add_node'):
                # GraphRAG library method
                self.graph.add_node(
                    node_id=node_id,
                    content=content,
                    node_type=node_type,
                    metadata=metadata or {}
                )
            else:
                # Fallback implementation
                self.graph["nodes"][node_id] = {
                    "content": content,
                    "type": node_type,
                    "metadata": metadata or {}
                }
                # Initialize neighbors list
                if node_id not in self.graph["neighbors"]:
                    self.graph["neighbors"][node_id] = []
            
            return node_id
        except Exception as e:
            logger.error(f"Error adding node: {str(e)}")
            return None
    
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
        if not self._node_exists(source_id):
            logger.warning(f"Source node {source_id} does not exist")
            return None
        
        if not self._node_exists(target_id):
            logger.warning(f"Target node {target_id} does not exist")
            return None
        
        try:
            # Check if we're using the actual GraphRAG library
            if hasattr(self.graph, 'add_edge'):
                # GraphRAG library method
                self.graph.add_edge(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation_type,
                    weight=weight,
                    metadata=metadata or {}
                )
            else:
                # Fallback implementation
                edge_key = (source_id, target_id)
                self.graph["edges"][edge_key] = {
                    "relation": relation_type,
                    "weight": weight,
                    "metadata": metadata or {}
                }
                # Update neighbors
                if target_id not in self.graph["neighbors"].get(source_id, []):
                    self.graph["neighbors"].setdefault(source_id, []).append(target_id)
            
            return (source_id, target_id)
        except Exception as e:
            logger.error(f"Error adding edge: {str(e)}")
            return None
    
    def _node_exists(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""
        if hasattr(self.graph, 'has_node'):
            return self.graph.has_node(node_id)
        else:
            return node_id in self.graph["nodes"]
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data or None if not found
        """
        try:
            if hasattr(self.graph, 'get_node'):
                # GraphRAG library method
                node_data = self.graph.get_node(node_id)
                if node_data:
                    return {
                        'id': node_id,
                        'content': node_data.get('content'),
                        'type': node_data.get('type'),
                        'metadata': node_data.get('metadata', {})
                    }
            else:
                # Fallback implementation
                if node_id in self.graph["nodes"]:
                    node_data = self.graph["nodes"][node_id]
                    return {
                        'id': node_id,
                        'content': node_data.get('content'),
                        'type': node_data.get('type'),
                        'metadata': node_data.get('metadata', {})
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error getting node: {str(e)}")
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
        if not self._node_exists(node_id):
            return []
        
        try:
            if hasattr(self.graph, 'get_neighbors'):
                # GraphRAG library method
                return self.graph.get_neighbors(
                    node_id=node_id,
                    relation_type=relation_type,
                    max_depth=max_depth
                )
            else:
                # Fallback implementation using BFS
                visited = set([node_id])
                queue = [(node_id, 0)]  # (node_id, depth)
                neighbors = []
                
                while queue:
                    current_id, depth = queue.pop(0)
                    
                    if depth >= max_depth:
                        continue
                    
                    for neighbor_id in self.graph["neighbors"].get(current_id, []):
                        # Get edge data
                        edge_key = (current_id, neighbor_id)
                        edge_data = self.graph["edges"].get(edge_key, {})
                        
                        # Filter by relation type if specified
                        if relation_type and edge_data.get('relation') != relation_type:
                            continue
                        
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            queue.append((neighbor_id, depth + 1))
                            
                            # Add to results
                            node_data = self.graph["nodes"].get(neighbor_id, {})
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
        except Exception as e:
            logger.error(f"Error getting neighbors: {str(e)}")
            return []
    
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
        try:
            if hasattr(self.graph, 'get_subgraph'):
                # GraphRAG library method
                return self.graph.get_subgraph(
                    node_ids=node_ids,
                    include_neighbors=include_neighbors,
                    max_neighbors=max_neighbors
                )
            else:
                # Fallback implementation
                # Create a new graph with the same structure
                subgraph = {
                    "nodes": {},
                    "edges": {},
                    "neighbors": {}
                }
                
                # Start with the specified nodes
                nodes = set(node_id for node_id in node_ids if node_id in self.graph["nodes"])
                
                # Add neighbors if requested
                if include_neighbors:
                    for node_id in list(nodes):
                        # Get neighbors
                        neighbors = self.graph["neighbors"].get(node_id, [])
                        
                        # Sort by weight if possible
                        weighted_neighbors = []
                        for neighbor_id in neighbors:
                            edge_key = (node_id, neighbor_id)
                            edge_data = self.graph["edges"].get(edge_key, {})
                            weight = edge_data.get('weight', 0.0)
                            weighted_neighbors.append((neighbor_id, weight))
                        
                        # Sort by weight and add top neighbors
                        weighted_neighbors.sort(key=lambda x: x[1], reverse=True)
                        for neighbor_id, _ in weighted_neighbors[:max_neighbors]:
                            nodes.add(neighbor_id)
                
                # Add nodes to subgraph
                for node_id in nodes:
                    subgraph["nodes"][node_id] = self.graph["nodes"][node_id]
                    subgraph["neighbors"][node_id] = []
                
                # Add edges between nodes in the subgraph
                for source_id in nodes:
                    for target_id in self.graph["neighbors"].get(source_id, []):
                        if target_id in nodes:
                            edge_key = (source_id, target_id)
                            if edge_key in self.graph["edges"]:
                                subgraph["edges"][edge_key] = self.graph["edges"][edge_key]
                                subgraph["neighbors"][source_id].append(target_id)
                
                return subgraph
        except Exception as e:
            logger.error(f"Error getting subgraph: {str(e)}")
            return None
    
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
            
            node_count = self.get_node_count()
            edge_count = self.get_edge_count()
            logger.info(f"Graph saved to {self.graph_path} with {node_count} nodes and {edge_count} edges")
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
            
            node_count = self.get_node_count()
            edge_count = self.get_edge_count()
            logger.info(f"Graph loaded from {self.graph_path} with {node_count} nodes and {edge_count} edges")
            return True
        except Exception as e:
            logger.error(f"Error loading graph: {str(e)}")
            return False
    
    def clear(self) -> None:
        """
        Clear the graph.
        """
        try:
            if hasattr(self.graph, 'clear'):
                # GraphRAG library method
                self.graph.clear()
            else:
                # Fallback implementation
                self.graph = {
                    "nodes": {},
                    "edges": {},
                    "neighbors": {}
                }
            
            logger.info("Graph cleared")
        except Exception as e:
            logger.error(f"Error clearing graph: {str(e)}")
    
    def analyze_graph(self) -> Dict[str, Any]:
        """
        Analyze the graph structure and return statistics.
        
        Returns:
            Dictionary of graph statistics
        """
        return analyze_graph(self.graph)
    
    def build_from_database(self, db: Session) -> Tuple[int, int]:
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
    
    def save_to_database(self, db: Session) -> Tuple[int, int]:
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
        try:
            if hasattr(self.graph, 'node_count'):
                # GraphRAG library method
                return self.graph.node_count()
            else:
                # Fallback implementation
                return len(self.graph["nodes"])
        except Exception as e:
            logger.error(f"Error getting node count: {str(e)}")
            return 0
    
    def get_edge_count(self) -> int:
        """
        Get the number of edges in the graph.
        
        Returns:
            Edge count
        """
        try:
            if hasattr(self.graph, 'edge_count'):
                # GraphRAG library method
                return self.graph.edge_count()
            else:
                # Fallback implementation
                return len(self.graph["edges"])
        except Exception as e:
            logger.error(f"Error getting edge count: {str(e)}")
            return 0