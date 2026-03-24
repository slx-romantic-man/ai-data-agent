"""
API Retrieval Service - Two-stage intelligent API selection.

Stage 1: Local embedding vector recall (sentence-transformers/all-MiniLM-L6-v2)
Stage 2: LLM refinement to select and order APIs
"""
import json
import hashlib
from functools import lru_cache
from typing import List, Dict, Any, Optional

from app.config.settings import settings
from app.services.vector_store import get_vector_store, VectorStore
from app.utils.logger import get_logger

logger = get_logger(__name__)

# LLM prompt for API selection
API_SELECTION_SYSTEM_PROMPT = """你是一个API选择助手。根据用户的问题，从给定的候选API列表中选择最适合的API。

请仔细分析用户问题的意图，选择最相关的API。如果多个API都需要调用，请按照合理的调用顺序排列。

你必须返回JSON格式，包含selected_apis数组：
{
    "selected_apis": [
        {
            "api_id": 1,
            "reason": "选择理由",
            "call_order": 1
        }
    ]
}

如果没有合适的API，返回空数组：
{
    "selected_apis": []
}

只返回JSON，不要添加任何解释文字。"""


API_SELECTION_USER_PROMPT = """用户问题：{query}

候选API列表：
{candidates}

请选择适合的API并返回JSON格式的结果。"""


class APIRetrievalService:
    """
    Two-stage API retrieval service.

    Stage 1: Vector similarity search using local embeddings
    Stage 2: LLM-based refinement and ordering
    """

    def __init__(self):
        self._vector_store: Optional[VectorStore] = None
        self._permission_service = None
        self._model = None  # Lazy-loaded embedding model
        self._llm_client = None  # Lazy-loaded LLM client

    def _get_vector_store(self) -> VectorStore:
        """Get vector store instance (lazy)."""
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    async def _get_permission_service(self):
        """Get permission service instance (lazy)."""
        if self._permission_service is None:
            from app.services.api_permission_service import get_api_permission_service
            self._permission_service = await get_api_permission_service()
        return self._permission_service

    def _get_llm_client(self):
        """Get LLM client instance (lazy)."""
        if self._llm_client is None:
            from app.config.llm_config import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client

    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        Model is loaded lazily on first call.

        Args:
            text: Text to embed

        Returns:
            384-dimensional embedding vector
        """
        if self._model is None:
            import os
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")

        return self._model.encode(text).tolist()

    def _build_index_text(self, api: Dict[str, Any]) -> str:
        """
        Build text for embedding from API configuration.

        Combines name, description, category path, and endpoint descriptions.

        Args:
            api: API configuration dict

        Returns:
            Combined text for embedding
        """
        parts = []

        # Add name
        if api.get("name"):
            parts.append(api["name"])

        # Add description
        if api.get("description"):
            parts.append(api["description"])

        # Add category path
        if api.get("category_path"):
            parts.append(api["category_path"])

        # Add endpoint descriptions
        endpoints = api.get("endpoints", {})
        if isinstance(endpoints, dict):
            for endpoint_name, endpoint_config in endpoints.items():
                parts.append(endpoint_name)
                if isinstance(endpoint_config, dict) and endpoint_config.get("description"):
                    parts.append(endpoint_config["description"])

        return " ".join(parts)

    async def build_index_for_api(self, api_config_id: int):
        """
        Build or update vector index for a single API.

        Args:
            api_config_id: API configuration ID
        """
        try:
            permission_service = await self._get_permission_service()
            api = await permission_service.get_api_by_id(api_config_id)

            if not api:
                logger.warning(f"API {api_config_id} not found, skipping index")
                return

            api_dict = api.model_dump() if hasattr(api, 'model_dump') else api

            if not api_dict.get("is_active"):
                logger.info(f"API {api_config_id} is inactive, removing from index")
                self._get_vector_store().delete(api_config_id)
                return

            # Build text for embedding
            text = self._build_index_text(api_dict)

            # Generate embedding
            embedding = self._get_embedding(text)

            # Build metadata
            metadata = {
                "name": api_dict.get("name", ""),
                "description": api_dict.get("description", ""),
                "category_path": api_dict.get("category_path", ""),
                "config_id": api_dict.get("config_id", ""),
            }

            # Upsert to vector store
            self._get_vector_store().upsert(api_config_id, embedding, metadata)

            logger.info(f"Built index for API {api_config_id}: {api_dict.get('name')}")

        except Exception as e:
            logger.error(f"Failed to build index for API {api_config_id}: {e}")
            raise

    async def rebuild_all_embeddings(self) -> Dict[str, int]:
        """
        Rebuild embeddings for all active APIs.

        Returns:
            Dict with success and failure counts
        """
        try:
            permission_service = await self._get_permission_service()
            apis = await permission_service.get_all_apis(include_auth=False)

            success_count = 0
            failure_count = 0

            # Filter active APIs - handle both dict and Pydantic model
            def is_active(api):
                if hasattr(api, 'is_active'):
                    return api.is_active
                return api.get("is_active", False)

            active_apis = [api for api in apis if is_active(api)]

            logger.info(f"Rebuilding embeddings for {len(active_apis)} active APIs")

            # Process in batches of 50
            batch_size = 50
            for i in range(0, len(active_apis), batch_size):
                batch = active_apis[i:i + batch_size]

                items = []
                for api in batch:
                    try:
                        # Handle both dict and Pydantic model
                        api_dict = api.model_dump() if hasattr(api, 'model_dump') else api

                        text = self._build_index_text(api_dict)
                        embedding = self._get_embedding(text)
                        metadata = {
                            "name": api_dict.get("name", ""),
                            "description": api_dict.get("description", ""),
                            "category_path": api_dict.get("category_path", ""),
                            "config_id": api_dict.get("config_id", ""),
                        }
                        items.append({
                            "api_id": api_dict["id"],
                            "embedding": embedding,
                            "metadata": metadata
                        })
                        success_count += 1
                    except Exception as e:
                        api_id = api.id if hasattr(api, 'id') else api.get('id')
                        logger.error(f"Failed to process API {api_id}: {e}")
                        failure_count += 1

                if items:
                    self._get_vector_store().upsert_batch(items)

            logger.info(f"Rebuild complete: {success_count} success, {failure_count} failure")

            return {
                "success": success_count,
                "failure": failure_count,
                "total": len(active_apis)
            }

        except Exception as e:
            logger.error(f"Failed to rebuild all embeddings: {e}")
            raise

    async def retrieve_candidate_apis(
        self,
        query: str,
        user_id: str,
        top_k: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Stage 1: Retrieve candidate APIs using vector similarity.

        Args:
            query: User's natural language query
            user_id: User ID for permission filtering
            top_k: Maximum number of candidates to retrieve

        Returns:
            List of candidate API dicts with scores
        """
        try:
            permission_service = await self._get_permission_service()

            # Get accessible API IDs from MySQL
            accessible_ids = await permission_service.get_active_api_ids(user_id)

            if not accessible_ids:
                logger.info(f"User {user_id} has no accessible APIs")
                return []

            # Generate query embedding
            query_embedding = self._get_embedding(query)

            # Search in vector store
            candidates = self._get_vector_store().search(
                query_embedding=query_embedding,
                accessible_api_ids=accessible_ids,
                top_k=top_k
            )

            logger.info(f"Retrieved {len(candidates)} candidates for user {user_id}")

            return candidates

        except Exception as e:
            logger.error(f"Failed to retrieve candidates: {e}")
            return []

    async def select_apis_with_llm(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Use LLM to select and order APIs from candidates.

        Args:
            query: User's natural language query
            candidates: List of candidate APIs from Stage 1

        Returns:
            List of selected APIs with reasons and order
        """
        if not candidates:
            return []

        try:
            # Format candidates for prompt
            candidates_text = ""
            for i, api in enumerate(candidates, 1):
                candidates_text += f"\n{i}. API ID: {api['api_id']}"
                candidates_text += f"\n   名称: {api.get('name', 'N/A')}"
                candidates_text += f"\n   描述: {api.get('description', 'N/A')}"
                candidates_text += f"\n   分类: {api.get('category_path', 'N/A')}"
                candidates_text += f"\n   相似度: {api.get('score', 0):.3f}"
                candidates_text += "\n"

            prompt = API_SELECTION_USER_PROMPT.format(
                query=query,
                candidates=candidates_text
            )

            llm_client = self._get_llm_client()

            # Call LLM - use chat method which returns string content
            content = await llm_client.chat(
                messages=[
                    {"role": "system", "content": API_SELECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            logger.info(f"LLM raw response: {content[:500]}")

            # Check if response is empty
            if not content or not content.strip():
                logger.error("LLM returned empty response")
                return candidates[:3]

            # Extract JSON from response
            try:
                # Try to parse directly
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                # Try to extract JSON from markdown code block
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                    except json.JSONDecodeError as e2:
                        logger.error(f"Failed to parse extracted JSON: {e2}")
                        return candidates[:3]
                else:
                    logger.error(f"No JSON found in LLM response. Full response: {content}")
                    return candidates[:3]

            selected = result.get("selected_apis", [])

            # Enrich selected APIs with full info
            enriched = []
            for item in selected:
                api_id = item.get("api_id")
                # Find full API info from candidates
                api_info = next(
                    (c for c in candidates if c["api_id"] == api_id),
                    None
                )
                if api_info:
                    enriched.append({
                        **api_info,
                        "reason": item.get("reason", ""),
                        "call_order": item.get("call_order", 1)
                    })

            # Sort by call_order
            enriched.sort(key=lambda x: x.get("call_order", 1))

            logger.info(f"LLM selected {len(enriched)} APIs")

            return enriched

        except Exception as e:
            logger.error(f"Failed to select APIs with LLM: {e}")
            # Fallback: return top candidates
            return candidates[:3]

    @lru_cache(maxsize=128)
    def _get_cache_key(self, query: str, user_id: str, top_k: int) -> str:
        """Generate cache key for query."""
        content = f"{query}:{user_id}:{top_k}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get_apis_for_query(
        self,
        query: str,
        user_id: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Complete two-stage API retrieval with caching.

        Args:
            query: User's natural language query
            user_id: User ID for permission filtering
            top_k: Maximum number of APIs to return (defaults to settings)

        Returns:
            List of selected APIs ready for Agent to use
        """
        if top_k is None:
            top_k = getattr(settings, 'API_RETRIEVAL_FINAL_TOP_K', 10)

        # Stage 1: Vector recall with configurable candidate size
        candidate_top_k = getattr(settings, 'API_RETRIEVAL_CANDIDATE_TOP_K', 100)
        candidates = await self.retrieve_candidate_apis(query, user_id, top_k=candidate_top_k)

        if not candidates:
            return []

        # Stage 2: LLM selection
        selected = await self.select_apis_with_llm(query, candidates)

        return selected[:top_k]

    def get_indexed_count(self) -> int:
        """
        Get the number of APIs currently indexed.

        Returns:
            Number of indexed APIs
        """
        return self._get_vector_store().count()


# Global instance
_api_retrieval_service: Optional[APIRetrievalService] = None


def get_api_retrieval_service() -> APIRetrievalService:
    """Get APIRetrievalService instance (singleton)."""
    global _api_retrieval_service
    if _api_retrieval_service is None:
        _api_retrieval_service = APIRetrievalService()
    return _api_retrieval_service