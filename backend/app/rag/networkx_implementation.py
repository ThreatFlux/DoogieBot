"""
NetworkX implementation of the graph interface.
This file is a wrapper around the modular implementation in the networkx package.
"""

from app.rag.networkx import NetworkXImplementation

# Re-export the NetworkXImplementation class
__all__ = ["NetworkXImplementation"]
