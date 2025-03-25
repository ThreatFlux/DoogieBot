from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from annoy import AnnoyIndex
import pickle
import os
from pathlib import Path
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FAISSStore:
    """
    Vector store using Annoy instead of FAISS, with the same interface.
    """
    
    def __init__(
        self, 
        index_path: str = "faiss_index.pkl",
        dimension: int = 1536  # Default for OpenAI embeddings
    ):
        """
        Initialize the vector store.
        
        Args:
            index_path: Path to save/load the index
            dimension: Dimension of the embedding vectors
        """
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.doc_ids = []
        self.doc_contents = []
        self.doc_metadata = []
    
    def _create_index(self) -> None:
        """
        Create a new Annoy index.
        """
        self.index = AnnoyIndex(self.dimension, 'angular')  # 'angular' is equivalent to cosine distance
        self.next_index = 0  # Annoy uses integers as IDs
    
    def add_embedding(
        self, 
        doc_id: str, 
        embedding: List[float], 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a document embedding to the index.
        
        Args:
            doc_id: Document ID
            embedding: Document embedding vector
            content: Document content
            metadata: Optional document metadata
        """
        if self.index is None:
            self._create_index()
        
        # Add to index
        self.index.add_item(self.next_index, embedding)
        self.doc_ids.append(doc_id)
        self.doc_contents.append(content)
        self.doc_metadata.append(metadata or {})
        self.next_index += 1
    
    def add_embeddings(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add multiple document embeddings to the index.
        
        Args:
            documents: List of documents with 'id', 'embedding', 'content', and optional 'metadata' fields
        """
        if not documents:
            return
        
        if self.index is None:
            self._create_index()
        
        # Extract embeddings
        for doc in documents:
            doc_id = doc.get('id')
            embedding = doc.get('embedding')
            content = doc.get('content')
            metadata = doc.get('metadata', {})
            
            if doc_id and embedding and content:
                self.index.add_item(self.next_index, embedding)
                self.doc_ids.append(doc_id)
                self.doc_contents.append(content)
                self.doc_metadata.append(metadata)
                self.next_index += 1
    
    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the index for documents similar to the query embedding.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of dictionaries with document ID, score, content, and metadata
        """
        if self.index is None or len(self.doc_ids) == 0:
            logger.warning("Index is empty. No results returned.")
            return []
        
        # Ensure the index is built
        if not getattr(self.index, '_n_items', None):
            logger.warning("Index is not built. Building index now.")
            self.index.build(10)  # 10 trees is a good default
        
        # Search index
        indices, distances = self.index.get_nns_by_vector(
            query_embedding, 
            min(top_k, len(self.doc_ids)), 
            include_distances=True
        )
        
        # Format results - Convert Annoy's distances to similarity scores
        # Annoy uses angular distance (cosine), so higher values are more dissimilar
        results = []
        for i, idx in enumerate(indices):
            # Convert distance to similarity score (1.0 is perfect match)
            # Annoy returns angular distance which ranges from 0 (identical) to 2 (completely dissimilar)
            # Transform to a 0-1 similarity score
            similarity = 1.0 - (distances[i] / 2.0)
            
            results.append({
                'id': self.doc_ids[idx],
                'score': float(similarity),
                'content': self.doc_contents[idx],
                'metadata': self.doc_metadata[idx]
            })
        
        return results
    
    def save(self) -> bool:
        """
        Save the index to disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.index_path)), exist_ok=True)
            
            # Save index data
            with open(self.index_path, 'wb') as f:
                pickle.dump({
                    'doc_ids': self.doc_ids,
                    'doc_contents': self.doc_contents,
                    'doc_metadata': self.doc_metadata,
                    'dimension': self.dimension,
                    'next_index': getattr(self, 'next_index', len(self.doc_ids))
                }, f)
            
            # Save Annoy index
            if self.index is not None:
                # Build index if not already built
                if not getattr(self.index, '_n_items', None):
                    self.index.build(10)  # 10 trees is a good default
                    
                index_bin_path = self.index_path + '.ann'
                self.index.save(index_bin_path)
            
            logger.info(f"Vector index saved to {self.index_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector index: {str(e)}")
            return False
    
    def load(self) -> bool:
        """
        Load the index from disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.index_path):
                logger.warning(f"Index file {self.index_path} does not exist")
                return False
            
            # Load index data
            with open(self.index_path, 'rb') as f:
                data = pickle.load(f)
                self.doc_ids = data['doc_ids']
                self.doc_contents = data['doc_contents']
                self.doc_metadata = data['doc_metadata']
                self.dimension = data['dimension']
                self.next_index = data.get('next_index', len(self.doc_ids))
            
            # Load Annoy index
            index_bin_path = self.index_path + '.ann'
            if os.path.exists(index_bin_path):
                self.index = AnnoyIndex(self.dimension, 'angular')
                self.index.load(index_bin_path)
                logger.info(f"Vector index loaded from {index_bin_path} with {len(self.doc_ids)} vectors")
                return True
            else:
                logger.warning(f"Vector index file {index_bin_path} does not exist")
                return False
        except Exception as e:
            logger.error(f"Error loading vector index: {str(e)}")
            return False
    
    def clear(self) -> None:
        """
        Clear the index.
        """
        self.index = None
        self.doc_ids = []
        self.doc_contents = []
        self.doc_metadata = []
        self.next_index = 0
        
        # Remove index files if they exist
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
            logger.info(f"Vector index file {self.index_path} removed")
        
        index_bin_path = self.index_path + '.ann'
        if os.path.exists(index_bin_path):
            os.remove(index_bin_path)
            logger.info(f"Vector index file {index_bin_path} removed")