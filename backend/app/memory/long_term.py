from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings
from typing import List, Dict, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self):
        self.client = None
        self.embeddings = None
        self._initialized = False
        self.collections = {
            "architectures": "architecture",
            "patterns": "coding patterns",
            "references": "documentation references",
            "projects": "past projects"
        }

    def _initialize(self):
        if self._initialized:
            return True

        try:
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
            )
            self.client.get_collections()
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            self._ensure_collections()
            self._initialized = True
            logger.info("MemoryService initialized")
            return True
        except Exception as e:
            logger.warning(f"MemoryService could not initialize (Qdrant may be down): {e}")
            return False

    def _ensure_collections(self):
        for collection_name in self.collections.keys():
            try:
                self.client.get_collection(collection_name)
            except Exception:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=384,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {collection_name}")

    def is_ready(self) -> bool:
        return self._initialize()

    def embed_text(self, text: str) -> List[float]:
        if not self._initialize():
            raise RuntimeError("MemoryService not available")
        return self.embeddings.embed_query(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self._initialize():
            raise RuntimeError("MemoryService not available")
        return self.embeddings.embed_documents(texts)

    def store(
        self,
        collection: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        if not self._initialize():
            raise RuntimeError("MemoryService not available")
        vector = self.embed_text(content)
        point_id = str(uuid.uuid4())

        self.client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "content": content,
                        "metadata": metadata or {}
                    }
                )
            ]
        )

        return point_id

    def search(
        self,
        collection: str,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        if not self._initialize():
            raise RuntimeError("MemoryService not available")
        vector = self.embed_text(query)

        results = self.client.query_points(
            collection_name=collection,
            query=vector,
            limit=limit,
            with_payload=True
        )

        return [
            {
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "metadata": hit.payload.get("metadata", {})
            }
            for hit in results.points
        ]

    def store_batch(
        self,
        collection: str,
        items: List[Dict[str, str]]
    ) -> List[str]:
        if not self._initialize():
            raise RuntimeError("MemoryService not available")
        texts = [item["content"] for item in items]
        vectors = self.embed_texts(texts)

        point_ids = []
        points = []

        for i, (text, vector) in enumerate(zip(texts, vectors)):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "content": text,
                        "metadata": items[i].get("metadata", {})
                    }
                )
            )

        self.client.upsert(
            collection_name=collection,
            points=points
        )

        return point_ids

    def delete_collection(self, collection: str):
        if not self._initialize():
            return
        try:
            self.client.delete_collection(collection_name=collection)
            logger.info(f"Deleted Qdrant collection: {collection}")
        except Exception as e:
            logger.warning(f"Failed to delete collection {collection}: {e}")


memory_service = MemoryService()
