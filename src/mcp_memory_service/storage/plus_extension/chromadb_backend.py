"""
ChromaDB storage backend for MCP Memory Service.

Provides vector storage using ChromaDB with automatic fallback to SQLite-vec.
"""

import logging
from typing import List, Dict, Any, Optional
import hashlib
import json

from ..base import MemoryStorage

logger = logging.getLogger(__name__)


class ChromaDBBackend(MemoryStorage):
    """
    ChromaDB-based storage backend with SQLite-vec fallback.

    Features:
    - Persistent vector storage with ChromaDB
    - Automatic fallback to SQLite-vec on connection failure
    - Metadata filtering and semantic search
    - Compatible with MCP Memory Service interface
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "mcp_memory",
        sqlite_fallback_path: str = "./data/memory.db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize ChromaDB backend.

        Args:
            host: ChromaDB server host
            port: ChromaDB server port
            collection_name: Collection name for memories
            sqlite_fallback_path: SQLite database path for fallback
            embedding_model: Embedding model name
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.sqlite_fallback_path = sqlite_fallback_path
        self.embedding_model_name = embedding_model

        self.client = None
        self.collection = None
        self.fallback_storage = None
        self.is_using_fallback = False

    async def initialize(self):
        """Initialize ChromaDB connection with fallback."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Try to connect to ChromaDB
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(anonymized_telemetry=False)
            )

            # Test connection
            self.client.heartbeat()

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            logger.info(f"✅ ChromaDB connected: {self.host}:{self.port}")

        except Exception as e:
            logger.warning(f"⚠️  ChromaDB connection failed: {e}, falling back to SQLite-vec")
            self.is_using_fallback = True

            # Initialize SQLite-vec fallback
            from ..sqlite_vec import SqliteVecMemoryStorage
            self.fallback_storage = SqliteVecMemoryStorage(
                db_path=self.sqlite_fallback_path,
                embedding_model=self.embedding_model_name
            )
            await self.fallback_storage.initialize()

    async def store_memory(self, content: str, tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Store a memory in ChromaDB or fallback storage."""
        if self.is_using_fallback:
            return await self.fallback_storage.store_memory(content, tags, metadata)

        # Generate memory hash
        memory_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Prepare metadata
        meta = metadata or {}
        meta["tags"] = json.dumps(tags or [])
        meta["content_preview"] = content[:200]

        # Store in ChromaDB
        self.collection.add(
            ids=[memory_hash],
            documents=[content],
            metadatas=[meta]
        )

        logger.debug(f"Stored memory {memory_hash} in ChromaDB")
        return memory_hash

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        tags: List[str] = None,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search memories using semantic similarity."""
        if self.is_using_fallback:
            return await self.fallback_storage.search_memories(query, limit, tags, metadata_filter)

        # Build where clause for filtering
        where_clause = {}
        if tags:
            # ChromaDB doesn't support JSON array filtering directly
            # We'll filter in post-processing
            pass
        if metadata_filter:
            where_clause.update(metadata_filter)

        # Search ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_clause if where_clause else None
        )

        # Format results
        memories = []
        if results["ids"] and results["ids"][0]:
            for idx, memory_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][idx]
                meta = results["metadatas"][0][idx]
                distance = results["distances"][0][idx] if "distances" in results else 0.0

                # Filter by tags if needed
                stored_tags = json.loads(meta.get("tags", "[]"))
                if tags and not any(tag in stored_tags for tag in tags):
                    continue

                memories.append({
                    "id": memory_id,
                    "content": doc,
                    "score": 1.0 - distance,  # Convert distance to similarity
                    "metadata": meta,
                    "tags": stored_tags
                })

        return memories

    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID."""
        if self.is_using_fallback:
            return await self.fallback_storage.get_memory(memory_id)

        try:
            result = self.collection.get(ids=[memory_id])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0],
                    "tags": json.loads(result["metadatas"][0].get("tags", "[]"))
                }
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")

        return None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if self.is_using_fallback:
            return await self.fallback_storage.delete_memory(memory_id)

        try:
            self.collection.delete(ids=[memory_id])
            logger.debug(f"Deleted memory {memory_id} from ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    async def list_memories(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all memories with pagination."""
        if self.is_using_fallback:
            return await self.fallback_storage.list_memories(limit, offset)

        try:
            # ChromaDB doesn't have native pagination, get all and slice
            result = self.collection.get(
                limit=limit,
                offset=offset
            )

            memories = []
            if result["ids"]:
                for idx, memory_id in enumerate(result["ids"]):
                    memories.append({
                        "id": memory_id,
                        "content": result["documents"][idx],
                        "metadata": result["metadatas"][idx],
                        "tags": json.loads(result["metadatas"][idx].get("tags", "[]"))
                    })

            return memories
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return []

    async def close(self):
        """Close connections."""
        if self.is_using_fallback and self.fallback_storage:
            await self.fallback_storage.close()
        # ChromaDB HTTP client doesn't need explicit closing
        logger.info("ChromaDB backend closed")
