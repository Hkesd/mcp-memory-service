"""
Hybrid Plus storage backend combining ChromaDB and DashVector.

Provides intelligent routing between local ChromaDB and cloud DashVector with fallback.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio

from ..base import MemoryStorage

logger = logging.getLogger(__name__)


class HybridPlusBackend(MemoryStorage):
    """
    Hybrid storage backend combining ChromaDB (local) and DashVector (cloud).

    Features:
    - Primary storage: ChromaDB (fast local access)
    - Sync to cloud: DashVector (backup + cross-device)
    - Intelligent routing: ChromaDB for reads, async sync to DashVector
    - Automatic fallback to SQLite-vec if both fail
    """

    def __init__(
        self,
        chromadb_host: str = "localhost",
        chromadb_port: int = 8000,
        dashvector_api_key: str = None,
        dashvector_endpoint: str = None,
        sqlite_fallback_path: str = "./data/memory.db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        sync_enabled: bool = True,
        sync_interval: int = 300  # 5 minutes
    ):
        """
        Initialize Hybrid Plus backend.

        Args:
            chromadb_host: ChromaDB server host
            chromadb_port: ChromaDB server port
            dashvector_api_key: DashVector API key
            dashvector_endpoint: DashVector endpoint
            sqlite_fallback_path: SQLite database path for fallback
            embedding_model: Embedding model name
            sync_enabled: Enable background sync to DashVector
            sync_interval: Sync interval in seconds
        """
        self.chromadb_host = chromadb_host
        self.chromadb_port = chromadb_port
        self.dashvector_api_key = dashvector_api_key
        self.dashvector_endpoint = dashvector_endpoint
        self.sqlite_fallback_path = sqlite_fallback_path
        self.embedding_model_name = embedding_model
        self.sync_enabled = sync_enabled
        self.sync_interval = sync_interval

        self.chromadb_backend = None
        self.dashvector_backend = None
        self.fallback_storage = None
        self.sync_task = None
        self.is_using_fallback = False

    async def initialize(self):
        """Initialize both ChromaDB and DashVector backends."""
        from .chromadb_backend import ChromaDBBackend
        from .dashvector_backend import DashVectorBackend

        # Initialize ChromaDB (primary)
        try:
            self.chromadb_backend = ChromaDBBackend(
                host=self.chromadb_host,
                port=self.chromadb_port,
                collection_name="mcp_memory_hybrid",
                sqlite_fallback_path=self.sqlite_fallback_path,
                embedding_model=self.embedding_model_name
            )
            await self.chromadb_backend.initialize()

            if self.chromadb_backend.is_using_fallback:
                logger.info("ChromaDB unavailable, using SQLite-vec as primary")
                self.is_using_fallback = True
            else:
                logger.info("✅ ChromaDB initialized as primary storage")

        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self.is_using_fallback = True

        # Initialize DashVector (cloud backup) if credentials provided
        if self.dashvector_api_key and self.dashvector_endpoint and not self.is_using_fallback:
            try:
                self.dashvector_backend = DashVectorBackend(
                    api_key=self.dashvector_api_key,
                    endpoint=self.dashvector_endpoint,
                    collection_name="mcp_memory_hybrid",
                    sqlite_fallback_path=self.sqlite_fallback_path,
                    embedding_model=self.embedding_model_name
                )
                await self.dashvector_backend.initialize()

                if not self.dashvector_backend.is_using_fallback:
                    logger.info("✅ DashVector initialized for cloud sync")

                    # Start background sync task
                    if self.sync_enabled:
                        self.sync_task = asyncio.create_task(self._sync_loop())
                        logger.info(f"Background sync enabled (interval: {self.sync_interval}s)")
                else:
                    logger.warning("DashVector unavailable, running ChromaDB-only mode")

            except Exception as e:
                logger.warning(f"DashVector initialization failed: {e}, running ChromaDB-only")

        # If everything failed, we're using SQLite-vec fallback
        if self.is_using_fallback:
            logger.warning("⚠️  Both ChromaDB and DashVector unavailable, using SQLite-vec")
            from ..sqlite_vec import SqliteVecMemoryStorage
            self.fallback_storage = SqliteVecMemoryStorage(
                db_path=self.sqlite_fallback_path,
                embedding_model=self.embedding_model_name
            )
            await self.fallback_storage.initialize()

    async def _sync_loop(self):
        """Background sync task from ChromaDB to DashVector."""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)
                await self._sync_to_cloud()
            except asyncio.CancelledError:
                logger.info("Sync loop cancelled")
                break
            except Exception as e:
                logger.error(f"Sync error: {e}")

    async def _sync_to_cloud(self):
        """Sync memories from ChromaDB to DashVector."""
        if not self.dashvector_backend or self.dashvector_backend.is_using_fallback:
            return

        try:
            # Get all memories from ChromaDB
            chromadb_memories = await self.chromadb_backend.list_memories(limit=1000)

            # Get all memories from DashVector
            dashvector_memories = await self.dashvector_backend.list_memories(limit=1000)
            dashvector_ids = {m["id"] for m in dashvector_memories}

            # Sync missing memories
            synced_count = 0
            for memory in chromadb_memories:
                if memory["id"] not in dashvector_ids:
                    try:
                        await self.dashvector_backend.store_memory(
                            content=memory["content"],
                            tags=memory.get("tags", []),
                            metadata=memory.get("metadata", {})
                        )
                        synced_count += 1
                    except Exception as e:
                        logger.error(f"Failed to sync memory {memory['id']}: {e}")

            if synced_count > 0:
                logger.info(f"Synced {synced_count} memories to DashVector")

        except Exception as e:
            logger.error(f"Cloud sync failed: {e}")

    async def store_memory(self, content: str, tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Store memory in primary storage with async cloud sync."""
        if self.is_using_fallback:
            return await self.fallback_storage.store_memory(content, tags, metadata)

        # Store in ChromaDB (primary)
        memory_id = await self.chromadb_backend.store_memory(content, tags, metadata)

        # Async sync to DashVector (non-blocking)
        if self.dashvector_backend and not self.dashvector_backend.is_using_fallback:
            asyncio.create_task(self._store_to_cloud(content, tags, metadata))

        return memory_id

    async def _store_to_cloud(self, content: str, tags: List[str], metadata: Dict[str, Any]):
        """Background task to store memory in DashVector."""
        try:
            await self.dashvector_backend.store_memory(content, tags, metadata)
            logger.debug("Memory synced to DashVector")
        except Exception as e:
            logger.error(f"Failed to sync to DashVector: {e}")

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        tags: List[str] = None,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search memories from primary storage (ChromaDB)."""
        if self.is_using_fallback:
            return await self.fallback_storage.search_memories(query, limit, tags, metadata_filter)

        # Search ChromaDB (fast local)
        return await self.chromadb_backend.search_memories(query, limit, tags, metadata_filter)

    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve memory from primary storage."""
        if self.is_using_fallback:
            return await self.fallback_storage.get_memory(memory_id)

        # Try ChromaDB first
        result = await self.chromadb_backend.get_memory(memory_id)

        # Fallback to DashVector if not found locally
        if not result and self.dashvector_backend:
            result = await self.dashvector_backend.get_memory(memory_id)

        return result

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from both storages."""
        if self.is_using_fallback:
            return await self.fallback_storage.delete_memory(memory_id)

        # Delete from ChromaDB
        chromadb_deleted = await self.chromadb_backend.delete_memory(memory_id)

        # Delete from DashVector (async)
        if self.dashvector_backend and not self.dashvector_backend.is_using_fallback:
            asyncio.create_task(self.dashvector_backend.delete_memory(memory_id))

        return chromadb_deleted

    async def list_memories(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List memories from primary storage."""
        if self.is_using_fallback:
            return await self.fallback_storage.list_memories(limit, offset)

        return await self.chromadb_backend.list_memories(limit, offset)

    async def close(self):
        """Close all connections and stop sync task."""
        # Stop sync task
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

        # Close backends
        if self.chromadb_backend:
            await self.chromadb_backend.close()
        if self.dashvector_backend:
            await self.dashvector_backend.close()
        if self.fallback_storage:
            await self.fallback_storage.close()

        logger.info("Hybrid Plus backend closed")
