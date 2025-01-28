from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
import logging
import os
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(
        self,
        collection_name: str = "arena_blocks",
        model_name: str = "all-MiniLM-L6-v2",
        vector_size: int = 384,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: str = "../../qdrant_data",
    ):
        """
        Initialize vector store with either local or remote Qdrant
        Args:
            collection_name: Name of the collection in Qdrant
            model_name: Name of the sentence-transformer model to use
            vector_size: Size of embedding vectors
            host: Qdrant server host (if None, uses local storage)
            port: Qdrant server port
            path: Path for local storage (only used if host is None)
        """
        self.collection_name = collection_name
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Initialize Qdrant client
        if host:
            logger.info(f"Connecting to Qdrant at {host}:{port}")
            api_key = os.getenv('QDRANT_API_KEY')
            self.client = QdrantClient(host=host, port=port, api_key=api_key)
        else:
            logger.info(f"Using local Qdrant storage at {path}")
            self.client = QdrantClient(path=path)
            
        # Create collection if it doesn't exist
        self._create_collection(vector_size)
        
    def _create_collection(self, vector_size: int):
        """Create Qdrant collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            logger.info(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        return self.model.encode(texts).tolist()
        
    def upsert_blocks(self, blocks_data: Dict[str, dict]):
        """
        Upsert blocks with their embeddings to Qdrant
        Args:
            blocks_data: Dict of block_id -> block_data
        """
        logger.info(f"Upserting {len(blocks_data)} blocks to vector store")
        
        points = []
        for block_id, block in blocks_data.items():
            if not block.get("crawled_text"):
                logger.debug(f"Skipping block {block_id} - no crawled text")
                continue
                
            # Generate embedding for the block's text
            embedding = self.generate_embeddings([block["crawled_text"]])[0]
            
            # Prepare metadata
            payload = {
                "block_id": block_id,
                "title": block.get("title", ""),
                "description": block.get("description", ""),
                "source_url": block.get("source_url", ""),
                "text_preview": block["crawled_text"][:200] if block.get("crawled_text") else "",
            }
            
            points.append(models.PointStruct(
                id=block_id,
                vector=embedding,
                payload=payload
            ))
            
        if points:
            logger.debug(f"Upserting {len(points)} points to Qdrant")
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        
    def search(self, query: str, limit: int = 5) -> List[dict]:
        """
        Search for similar blocks using a text query
        Args:
            query: Text query to search for
            limit: Maximum number of results to return
        Returns:
            List of similar blocks with their scores
        """
        logger.debug(f"Searching for: {query}")
        query_vector = self.generate_embeddings([query])[0]
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        return [
            {
                "score": hit.score,
                "block_id": hit.payload["block_id"],
                "title": hit.payload["title"],
                "description": hit.payload["description"],
                "source_url": hit.payload["source_url"],
                "text_preview": hit.payload["text_preview"],
            }
            for hit in results
        ]