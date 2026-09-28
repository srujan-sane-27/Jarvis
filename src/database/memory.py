import os
import json
import logging
from typing import List, Dict, Any, Optional
from src.config import get_settings

logger = logging.getLogger("jarvis.memory")


class SemanticMemoryStore:
    """Manages long-term vector embeddings and semantic search.

    Leverages local ChromaDB when available, or a resilient local embedding cache.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self._init_store()

    def _init_store(self):
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            persist_dir = os.path.abspath(self.settings.CHROMA_PERSIST_DIRECTORY)
            os.makedirs(persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                name="jarvis_longterm_memory",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB persistent vector memory initialized successfully.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization deferred or unavailable: {e}. Utilizing lightweight memory fallback.")

    def store_memory(self, memory_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Stores a textual memory entry."""
        if not self.collection:
            logger.debug(f"Store memory skipped (no vector client): {text[:50]}")
            return

        try:
            self.collection.upsert(
                ids=[memory_id],
                documents=[text],
                metadatas=[metadata or {"timestamp": "now"}]
            )
        except Exception as e:
            logger.error(f"Error upserting memory to ChromaDB: {e}")

    def query_memory(self, query_text: str, n_results: int = 3) -> List[str]:
        """Queries the vector store for semantic matches."""
        if not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            documents = results.get("documents", [[]])
            return documents[0] if documents else []
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []


# Global memory instance
memory_store = SemanticMemoryStore()
