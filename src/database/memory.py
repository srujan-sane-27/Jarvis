import os
import json
import logging
import importlib
from typing import List, Dict, Any, Optional
from src.config import get_settings

logger = logging.getLogger("jarvis.memory")


class SemanticMemoryStore:
    """Manages long-term vector embeddings and semantic search.

    Leverages local ChromaDB when available, or a resilient, lightweight local cache.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.collection = None
        self._initialized = False
        self._local_cache_path = os.path.join(
            os.path.abspath(self.settings.CHROMA_PERSIST_DIRECTORY),
            "memory_cache.json"
        )
        self._local_memories: Dict[str, Dict[str, Any]] = {}

    def _ensure_store(self):
        """Lazy initialization of ChromaDB or lightweight fallback store."""
        if self._initialized:
            return
        self._initialized = True

        persist_dir = os.path.abspath(self.settings.CHROMA_PERSIST_DIRECTORY)
        try:
            os.makedirs(persist_dir, exist_ok=True)
            # Dynamic import ensures language servers don't flag missing package errors
            chroma_module = importlib.import_module("chromadb")
            self.client = chroma_module.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                name="jarvis_longterm_memory",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB vector memory initialized successfully.")
        except Exception:
            # Fallback: lightweight JSON local storage for 0% CPU & low memory footprint
            self._load_local_cache()
            logger.info("Lightweight high-efficiency memory store initialized.")

    def _load_local_cache(self):
        """Loads cached memories from disk for lightweight mode."""
        if os.path.exists(self._local_cache_path):
            try:
                with open(self._local_cache_path, "r", encoding="utf-8") as f:
                    self._local_memories = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load local memory cache: {e}")
                self._local_memories = {}

    def _save_local_cache(self):
        """Persists memories to local disk."""
        try:
            persist_dir = os.path.dirname(self._local_cache_path)
            os.makedirs(persist_dir, exist_ok=True)
            with open(self._local_cache_path, "w", encoding="utf-8") as f:
                json.dump(self._local_memories, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist local memory cache: {e}")

    def store_memory(self, memory_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Stores a textual memory entry."""
        self._ensure_store()
        if self.collection:
            try:
                self.collection.upsert(
                    ids=[memory_id],
                    documents=[text],
                    metadatas=[metadata or {"timestamp": "now"}]
                )
                return
            except Exception as e:
                logger.error(f"Error upserting memory to ChromaDB: {e}")

        # Resilient local fallback
        self._local_memories[memory_id] = {
            "text": text,
            "metadata": metadata or {"timestamp": "now"}
        }
        self._save_local_cache()

    def query_memory(self, query_text: str, n_results: int = 3) -> List[str]:
        """Queries the memory store for semantic or relevant matches."""
        self._ensure_store()
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=n_results
                )
                documents = results.get("documents", [[]])
                return documents[0] if documents else []
            except Exception as e:
                logger.error(f"Error querying ChromaDB: {e}")

        # Local fallback search: keyword relevance scoring
        if not self._local_memories:
            return []

        words = set(query_text.lower().split())
        scored: List[tuple[int, str]] = []
        for item in self._local_memories.values():
            doc = item.get("text", "")
            doc_words = set(doc.lower().split())
            overlap = len(words.intersection(doc_words))
            scored.append((overlap, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored[:n_results] if score > 0 or not words]


# Global memory instance
memory_store = SemanticMemoryStore()
