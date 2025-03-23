from typing import Optional
import os
import logging
from sqlalchemy.orm import Session
from app.rag.bm25_index import BM25Index
from app.rag.faiss_store import FAISSStore
from app.rag.graph_rag import GraphRAG
from app.rag.networkx_implementation import NetworkXImplementation
from app.rag.graphrag_implementation import GraphRAGImplementation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSingleton:
    """
    Singleton class to hold RAG components in memory.
    """
    # Class variables for the singleton pattern
    _instance = None
    _lock = False
    
    # Singleton instances of RAG components
    bm25_index: Optional[BM25Index] = None
    faiss_store: Optional[FAISSStore] = None
    graph_rag: Optional[GraphRAG] = None
    
    # Flag to track if components are initialized
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGSingleton, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, index_dir: str = "./indexes", db: Optional[Session] = None):
        """
        Initialize RAG components if not already initialized.
        Thread-safe initialization with double-checked locking pattern.
        
        Args:
            index_dir: Directory containing index files
            db: Optional database session for getting configuration
        """
        # Quick check without acquiring lock
        if self._initialized:
            logger.debug("RAG components already initialized (quick check)")
            return
        
        # Use a lock to prevent multiple initializations
        if RAGSingleton._lock:
            logger.debug("Initialization in progress by another thread, waiting...")
            # Wait for initialization to complete
            while RAGSingleton._lock:
                import time
                time.sleep(0.1)
            return
        
        # Set lock
        RAGSingleton._lock = True
        
        try:
            # Double-check after acquiring lock
            if self._initialized:
                logger.debug("RAG components already initialized (after lock)")
                return
            
            logger.info("Initializing RAG components...")
            
            # Create index directory if it doesn't exist
            os.makedirs(index_dir, exist_ok=True)
            
            # Initialize BM25 index
            self.bm25_index = BM25Index(os.path.join(index_dir, "bm25_index.pkl"))
            bm25_loaded = self.bm25_index.load()
            if bm25_loaded:
                logger.info(f"BM25 index loaded with {len(self.bm25_index.doc_ids)} documents")
            else:
                logger.warning("BM25 index not loaded")
            
            # Initialize FAISS store
            self.faiss_store = FAISSStore(os.path.join(index_dir, "faiss_index.pkl"))
            faiss_loaded = self.faiss_store.load()
            if faiss_loaded:
                logger.info(f"FAISS index loaded with {len(self.faiss_store.doc_ids)} vectors")
            else:
                logger.warning("FAISS index not loaded")
            
            # Initialize GraphRAG with the appropriate implementation
            self._initialize_graph_rag(index_dir, db)
            
            self._initialized = True
            logger.info("RAG components initialization complete")
        finally:
            # Release lock
            RAGSingleton._lock = False
    
    def _initialize_graph_rag(self, index_dir: str, db: Optional[Session] = None):
        """
        Initialize the GraphRAG component with the appropriate implementation.
        
        Args:
            index_dir: Directory containing index files
            db: Optional database session for getting configuration
        """
        # Get the graph implementation from the database if available
        implementation = "networkx"  # Default to NetworkX
        if db:
            try:
                from app.services.rag_config import RAGConfigService
                implementation = RAGConfigService.get_graph_implementation(db)
            except Exception as e:
                logger.error(f"Error getting graph implementation from database: {str(e)}")
        
        # Create the appropriate graph implementation
        graph_path = os.path.join(index_dir, "graph_rag.pkl")
        if implementation == "graphrag":
            logger.info("Using GraphRAG implementation")
            graph_impl = GraphRAGImplementation(graph_path)
        else:
            logger.info("Using NetworkX implementation")
            graph_impl = NetworkXImplementation(graph_path)
        
        # Create the GraphRAG instance with the implementation
        self.graph_rag = GraphRAG(implementation=graph_impl)
        
        # Load the graph
        graph_loaded = self.graph_rag.load()
        if graph_loaded:
            logger.info(f"Graph loaded with {self.graph_rag.get_node_count()} nodes and {self.graph_rag.get_edge_count()} edges")
        else:
            logger.warning("Graph not loaded")
    
    def get_bm25_index(self) -> BM25Index:
        """Get the BM25 index instance."""
        if not self._initialized:
            self.initialize()
        elif self.bm25_index is None:
            # If initialized but index is None, create a new instance without full initialization
            logger.warning("BM25 index was None despite initialization, creating new instance")
            self.bm25_index = BM25Index("./indexes/bm25_index.pkl")
            self.bm25_index.load()
        return self.bm25_index
    
    def get_faiss_store(self) -> FAISSStore:
        """Get the FAISS store instance."""
        if not self._initialized:
            self.initialize()
        elif self.faiss_store is None:
            # If initialized but store is None, create a new instance without full initialization
            logger.warning("FAISS store was None despite initialization, creating new instance")
            self.faiss_store = FAISSStore("./indexes/faiss_index.pkl")
            self.faiss_store.load()
        return self.faiss_store
    
    def get_graph_rag(self) -> GraphRAG:
        """Get the GraphRAG instance."""
        if not self._initialized:
            self.initialize()
        elif self.graph_rag is None:
            # If initialized but graph is None, create a new instance without full initialization
            logger.warning("GraphRAG was None despite initialization, creating new instance")
            self._initialize_graph_rag("./indexes")
        return self.graph_rag
    
    def reset_graph(self, db: Optional[Session] = None):
        """
        Reset the graph implementation based on the current configuration.
        
        Args:
            db: Optional database session for getting configuration
        """
        if self.graph_rag:
            # Save the current graph if it exists
            self.graph_rag.save()
        
        # Re-initialize the graph with the current configuration
        self._initialize_graph_rag("./indexes", db)
    
    def clear_all(self):
        """Clear all RAG components."""
        if self.bm25_index:
            self.bm25_index.clear()
        if self.faiss_store:
            self.faiss_store.clear()
        if self.graph_rag:
            self.graph_rag.clear()
        self._initialized = False
        logger.info("All RAG components cleared")

# Create a global instance
rag_singleton = RAGSingleton()