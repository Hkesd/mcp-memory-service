"""
Plus Extension Storage Backends for MCP Memory Service.

This module provides additional storage backends:
- ChromaDB: Vector database with persistent storage
- DashVector: Alibaba Cloud vector search service
- Hybrid Plus: Combined ChromaDB + DashVector with intelligent routing
"""

import logging
from typing import Type

logger = logging.getLogger(__name__)


def get_plus_backend_class(backend: str) -> Type:
    """
    Get plus extension storage backend class.

    Args:
        backend: Backend name ('chromadb', 'dashvector', 'hybrid_plus')

    Returns:
        Storage backend class
    """
    if backend == "chromadb":
        from .chromadb_backend import ChromaDBBackend
        return ChromaDBBackend
    elif backend == "dashvector":
        from .dashvector_backend import DashVectorBackend
        return DashVectorBackend
    elif backend == "hybrid_plus":
        from .hybrid_plus_backend import HybridPlusBackend
        return HybridPlusBackend
    else:
        raise ValueError(f"Unknown plus extension backend: {backend}")


async def create_plus_instance(StorageClass: Type, sqlite_path: str):
    """
    Create plus extension storage instance with configuration.

    Args:
        StorageClass: Storage backend class
        sqlite_path: SQLite database path (for fallback/hybrid modes)

    Returns:
        Initialized storage instance
    """
    import os

    if StorageClass.__name__ == "ChromaDBBackend":
        storage = StorageClass(
            host=os.getenv("CHROMADB_HOST", "localhost"),
            port=int(os.getenv("CHROMADB_PORT", "8000")),
            collection_name=os.getenv("CHROMADB_COLLECTION", "mcp_memory"),
            sqlite_fallback_path=sqlite_path
        )
    elif StorageClass.__name__ == "DashVectorBackend":
        storage = StorageClass(
            api_key=os.getenv("DASHVECTOR_API_KEY"),
            endpoint=os.getenv("DASHVECTOR_ENDPOINT"),
            collection_name=os.getenv("DASHVECTOR_COLLECTION", "mcp_memory"),
            sqlite_fallback_path=sqlite_path
        )
    elif StorageClass.__name__ == "HybridPlusBackend":
        storage = StorageClass(
            chromadb_host=os.getenv("CHROMADB_HOST", "localhost"),
            chromadb_port=int(os.getenv("CHROMADB_PORT", "8000")),
            dashvector_api_key=os.getenv("DASHVECTOR_API_KEY"),
            dashvector_endpoint=os.getenv("DASHVECTOR_ENDPOINT"),
            sqlite_fallback_path=sqlite_path
        )
    else:
        raise ValueError(f"Unknown storage class: {StorageClass.__name__}")

    await storage.initialize()
    return storage
