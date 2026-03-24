"""
Vector Store Service - Qdrant-based vector storage for API embeddings.
Supports both in-memory mode and persistent file storage.
"""
from typing import List, Dict, Optional, Any
import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    Filter,
    FieldCondition,
    MatchAny,
    PointStruct,
    PointsList,
)

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Qdrant-based vector store for API embeddings.
    Supports in-memory mode (:memory:) or persistent file storage.
    """

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._collection_name = settings.QDRANT_COLLECTION
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client (lazy initialization)."""
        if self._client is None:
            # Use in-memory mode or persistent storage
            if settings.QDRANT_URL == ":memory:":
                self._client = QdrantClient(location=":memory:")
            elif settings.QDRANT_URL.startswith("file://"):
                # File-based persistent storage
                storage_path = settings.QDRANT_URL[7:]  # Remove "file://" prefix
                os.makedirs(storage_path, exist_ok=True)
                self._client = QdrantClient(path=storage_path)
            else:
                self._client = QdrantClient(url=settings.QDRANT_URL)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            existing = [c.name for c in self._client.get_collections().collections]
            if self._collection_name not in existing:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(
                        size=self._dimensions,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self._collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    def upsert(self, api_id: int, embedding: List[float], metadata: Dict[str, Any]):
        """
        Insert or update an API's embedding.

        Args:
            api_id: API configuration ID (used as point ID)
            embedding: 384-dimensional embedding vector
            metadata: API metadata (name, description, category_path, etc.)
        """
        try:
            client = self._get_client()
            client.upsert(
                collection_name=self._collection_name,
                points=[
                    PointStruct(
                        id=api_id,
                        vector=embedding,
                        payload={
                            "api_id": api_id,
                            **metadata
                        }
                    )
                ]
            )
            logger.debug(f"Upserted embedding for API {api_id}")
        except Exception as e:
            logger.error(f"Failed to upsert embedding for API {api_id}: {e}")
            raise

    def upsert_batch(self, items: List[Dict[str, Any]]):
        """
        Batch insert/update embeddings.

        Args:
            items: List of dicts with api_id, embedding, metadata
        """
        if not items:
            return

        try:
            client = self._get_client()
            points = [
                PointStruct(
                    id=item["api_id"],
                    vector=item["embedding"],
                    payload={
                        "api_id": item["api_id"],
                        **item.get("metadata", {})
                    }
                )
                for item in items
            ]
            client.upsert(
                collection_name=self._collection_name,
                points=points
            )
            logger.info(f"Upserted {len(items)} embeddings in batch")
        except Exception as e:
            logger.error(f"Failed to upsert batch embeddings: {e}")
            raise

    def delete(self, api_id: int):
        """
        Delete an API's embedding.

        Args:
            api_id: API configuration ID to delete
        """
        try:
            client = self._get_client()
            client.delete(
                collection_name=self._collection_name,
                points_selector=PointsList(points=[api_id])
            )
            logger.debug(f"Deleted embedding for API {api_id}")
        except Exception as e:
            logger.error(f"Failed to delete embedding for API {api_id}: {e}")
            # Don't raise - deletion failure shouldn't block operations

    def delete_batch(self, api_ids: List[int]):
        """
        Batch delete embeddings.

        Args:
            api_ids: List of API configuration IDs to delete
        """
        if not api_ids:
            return

        try:
            client = self._get_client()
            client.delete(
                collection_name=self._collection_name,
                points_selector=PointsList(points=api_ids)
            )
            logger.info(f"Deleted {len(api_ids)} embeddings in batch")
        except Exception as e:
            logger.error(f"Failed to delete batch embeddings: {e}")

    def search(
        self,
        query_embedding: List[float],
        accessible_api_ids: List[int],
        top_k: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for similar APIs within accessible ones.

        IMPORTANT: Filters by accessible_api_ids from MySQL, not by user_id in Qdrant.
        This ensures proper permission control.

        Args:
            query_embedding: 384-dimensional query vector
            accessible_api_ids: List of API IDs the user has permission to access
            top_k: Maximum number of results to return

        Returns:
            List of dicts with api_id, score, and metadata
        """
        if not accessible_api_ids:
            return []

        try:
            client = self._get_client()
            results = client.query_points(
                collection_name=self._collection_name,
                query=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="api_id",
                            match=MatchAny(any=accessible_api_ids)
                        )
                    ]
                ),
                limit=top_k
            )

            # query_points returns QueryResponse with points attribute
            points = results.points if hasattr(results, 'points') else results

            return [
                {
                    "api_id": p.id,
                    "score": p.score,
                    **p.payload
                }
                for p in points
            ]
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            return []

    def get_all_ids(self) -> List[int]:
        """
        Get all API IDs currently in the vector store.

        Returns:
            List of API IDs
        """
        try:
            client = self._get_client()
            # Scroll through all points
            all_ids = []
            offset = None

            while True:
                points, offset = client.scroll(
                    collection_name=self._collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )
                all_ids.extend([p.id for p in points])

                if offset is None:
                    break

            return all_ids
        except Exception as e:
            logger.error(f"Failed to get all IDs: {e}")
            return []

    def count(self) -> int:
        """
        Get the number of vectors in the collection.

        Returns:
            Number of vectors
        """
        try:
            client = self._get_client()
            info = client.get_collection(self._collection_name)
            return info.points_count if info else 0
        except Exception as e:
            logger.error(f"Failed to count vectors: {e}")
            return 0


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get VectorStore instance (singleton)."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store