"""
GraphRAG implementation of the graph interface.
This file is a wrapper around the modular implementation in the graphrag package.
"""

from app.rag.graphrag import GraphRAGImplementation

# Re-export the GraphRAGImplementation class
__all__ = ["GraphRAGImplementation"]