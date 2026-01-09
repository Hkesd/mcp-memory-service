"""
DashVector storage backend for MCP Memory Service.

Provides vector storage using Alibaba Cloud DashVector with automatic fallback.
"""

import logging
from typing import List, Dict, Any, Optional
import hashlib
import json
import time

from ..base import MemoryStorage

logger = logging.getLogger(__name__)


class DashVectorBackend(MemoryStorage):
    """
    DashVector (Alibaba Cloud) storage backend with SQLite-vec fallback.

    Features:
    - Cloud-based vector search with DashVector
    - Automatic fallback to SQLite-vec on connection failure
    - Metadata filtering and semantic search
    - Compatible with MCP Memory Service interface
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        collection_name: str = "mcp_memory",
        sqlite_fallback_path: str = "./data/memory.db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 384  # Default for all-MiniLM-L6-v2
    ):
        """
        Initialize DashVector backend.

        Args:
            api_key: DashVector API key
            endpoint: DashVector service endpoint
            collection_name: Collection name for memories
            sqlite_fallback_path: SQLite database path for fallback
            embedding_model: Embedding model name
            dimension: Vector dimension (must match embedding model)
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.collection_name = collection_name
        self.sqlite_fallback_path = sqlite_fallback_path
        self.embedding_model_name = embedding_model
        self.dimension = dimension

        self.client = None
        self.collection = None
        self.fallback_storage = None
        self.is_using_fallback = False
        self.embedding_function = None

    async def initialize(self):
        """Initialize DashVector connection with fallback."""
        if not self.api_key or not self.endpoint:
            logger.warning("⚠️  DashVector credentials missing, falling back to SQLite-vec")
            self.is_using_fallback = True
            await self._initialize_fallback()
            return

        try:
            import dashvector

            # Initialize DashVector client
            self.client = dashvector.Client(
                api_key=self.api_key,
                endpoint=self.endpoint
            )

            # Get or create collection
            try:
                self.collection = self.client.get(self.collection_name)
                logger.info(f"✅ DashVector collection '{self.collection_name}' found")
            except Exception:
                # Collection doesn't exist, create it
                self.collection = self.client.create(
                    name=self.collection_name,
                    dimension=self.dimension,
                    metric="cosine"
                )
                logger.info(f"✅ DashVector collection '{self.collection_name}' created")

            # Initialize embedding function
            await self._initialize_embeddings()

            logger.info(f"✅ DashVector connected: {self.endpoint}")

        except Exception as e:
            logger.warning(f"⚠️  DashVector initialization failed: {e}, falling back to SQLite-vec")
            self.is_using_fallback = True
            await self._initialize_fallback()

    async def _initialize_fallback(self):
        """Initialize SQLite-vec fallback storage."""
        from ..sqlite_vec import SqliteVecMemoryStorage
        self.fallback_storage = SqliteVecMemoryStorage(
            db_path=self.sqlite_fallback_path,
            embedding_model=self.embedding_model_name
        )
        await self.fallback_storage.initialize()

    async def _initialize_embeddings(self):
        """Initialize embedding model for text vectorization."""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_function = SentenceTransformer(self.embedding_model_name)
            logger.debug(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if self.embedding_function is None:
            raise RuntimeError("Embedding function not initialized")
        return self.embedding_function.encode(text).tolist()

    async def store_memory(self, content: str, tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Store a memory in DashVector or fallback storage."""
        if self.is_using_fallback:
            return await self.fallback_storage.store_memory(content, tags, metadata)

        # Generate memory hash
        memory_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Generate embedding
        embedding = self._generate_embedding(content)

        # Prepare metadata
        meta = metadata or {}
        meta["tags"] = json.dumps(tags or [])
        meta["content_preview"] = content[:200]
        meta["content_full"] = content  # DashVector requires storing full content in metadata
        meta["timestamp"] = int(time.time())

        # Store in DashVector
        from dashvector import Doc
        doc = Doc(
            id=memory_hash,
            vector=embedding,
            fields=meta
        )

        result = self.collection.insert([doc])
        if result:
            logger.debug(f"Stored memory {memory_hash} in DashVector")
            return memory_hash
        else:
            logger.error(f"Failed to store memory in DashVector")
            raise RuntimeError("DashVector insert failed")

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

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build filter expression
        filter_expr = None
        if metadata_filter:
            # DashVector filter syntax (simplified)
            # Note: Complex filtering may need custom implementation
            pass

        # Search DashVector
        result = self.collection.query(
            vector=query_embedding,
            topk=limit * 2,  # Over-fetch for tag filtering
            include_vector=False
        )

        # Format results
        memories = []
        if result and result.output:
            for item in result.output:
                fields = item.fields

                # Filter by tags if needed
                stored_tags = json.loads(fields.get("tags", "[]"))
                if tags and not any(tag in stored_tags for tag in tags):
                    continue

                memories.append({
                    "id": item.id,
                    "content": fields.get("content_full", ""),
                    "score": item.score,
                    "metadata": fields,
                    "tags": stored_tags
                })

                if len(memories) >= limit:
                    break

        return memories

    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID."""
        if self.is_using_fallback:
            return await self.fallback_storage.get_memory(memory_id)

        try:
            result = self.collection.fetch([memory_id])
            if result and result.output:
                item = result.output[0]
                fields = item.fields
                return {
                    "id": item.id,
                    "content": fields.get("content_full", ""),
                    "metadata": fields,
                    "tags": json.loads(fields.get("tags", "[]"))
                }
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")

        return None

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if self.is_using_fallback:
            return await self.fallback_storage.delete_memory(memory_id)

        try:
            result = self.collection.delete([memory_id])
            if result:
                logger.debug(f"Deleted memory {memory_id} from DashVector")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    async def list_memories(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all memories with pagination."""
        if self.is_using_fallback:
            return await self.fallback_storage.list_memories(limit, offset)

        # DashVector doesn't support direct listing, use scan/query
        # This is a simplified implementation
        logger.warning("DashVector list_memories is limited, consider using search instead")

        try:
            # Use a dummy query to get recent memories
            dummy_embedding = [0.0] * self.dimension
            result = self.collection.query(
                vector=dummy_embedding,
                topk=limit,
                include_vector=False
            )

            memories = []
            if result and result.output:
                for item in result.output[offset:offset + limit]:
                    fields = item.fields
                    memories.append({
                        "id": item.id,
                        "content": fields.get("content_full", ""),
                        "metadata": fields,
                        "tags": json.loads(fields.get("tags", "[]"))
                    })

            return memories
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return []

    async def close(self):
        """Close connections."""
        if self.is_using_fallback and self.fallback_storage:
            await self.fallback_storage.close()
        # DashVector client doesn't need explicit closing
        logger.info("DashVector backend closed")
