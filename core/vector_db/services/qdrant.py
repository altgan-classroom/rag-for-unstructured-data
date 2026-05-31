from typing import List, Dict, Any, Optional
import logging
import uuid
import os
from pathlib import Path
from llama_index.core.settings import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext,VectorStoreIndex, load_index_from_storage
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core import Document
from .base import BaseVectorDB, SearchResult
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, SparseVectorParams, Distance
from datetime import datetime
# from llama_index import VectorStoreIndex

logger = logging.getLogger(__name__)

class QdrantDB(BaseVectorDB):
    """Qdrant vector database implementation using llama_index."""
    
    def __init__(
        self,
        collection_name: str = os.getenv('QDRANT_COLLECTION_NAME', "documents"),
        host: str = os.getenv('QDRANT_HOST', "qdrant"),
        port: int = int(os.getenv('QDRANT_PORT', "6333")),
        embedding_model: str = os.getenv('EMBEDDING_MODEL', "mixedbread-ai/mxbai-embed-large-v1"),
        persist_dir: str = os.getenv('QDRANT_PERSIST_DIR', "/data/persist/qdrant"),
    ):  # fastembed_sparse_model is handled in QdrantVectorStore initialization
        """
        Initialize Qdrant vector store with llama_index.
        
        Args:
            collection_name: Name of the Qdrant collection
            host: Qdrant host
            port: Qdrant port
            embedding_model: HuggingFace model name for embeddings
        """
        try:
            self.collection_name = collection_name
            
            # Initialize embedding model
            self.embedding_model = HuggingFaceEmbedding(model_name=embedding_model,embed_batch_size=32)
        
            # Initialize Qdrant vector store with client instance
            self.vector_store = QdrantVectorStore(
                collection_name=collection_name,
                client=QdrantClient(host=host, port=port),
                embedding_model=self.embedding_model,
                enable_hybrid=True,
                fastembed_sparse_model=os.getenv('FASTEMBED_SPARSE_MODEL', "Qdrant/bm42-all-minilm-l6-v2-attentions"),  # optional, for hybrid
                prefer_grpc=False
            )
            
            # Initialize storage context
            if os.path.exists(persist_dir) and os.path.isfile(os.path.join(persist_dir, "docstore.json")):
                # If persist_dir exists and has docstore.json, use it
                self.storage_context = StorageContext.from_defaults(
                    vector_store=self.vector_store,
                    persist_dir=persist_dir
                )
            else:
                # If persist_dir doesn't exist or doesn't have docstore.json, create new storage
                self.storage_context = StorageContext.from_defaults(
                    vector_store=self.vector_store,
                    docstore=SimpleDocumentStore(),
                    index_store=SimpleIndexStore()
                )
            self.persist_dir = persist_dir
            
            logger.info(f"Qdrant vector store initialized with host: {host}, port: {port}")
            
            # Ensure collection exists with proper configuration
            # self._ensure_collection()
            
            logger.info(f"Initialized vector store for collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise

    def add_documents(
        self,
        chunks: List[str],
        metadata: Dict[str, Any],
        custom_metadata_per_chunk: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Add document chunks to Qdrant using llama_index.
        
        Args:
            chunks: List of text chunks
            metadata: Document metadata that applies to all chunks
            custom_metadata_per_chunk: Optional list of metadata dictionaries, one per chunk
                Each dictionary contains metadata specific to that chunk
                
        Returns:
            document_id: ID of the added document
        """
        try:
            # Create documents from chunks
            documents = []
            for i, chunk in enumerate(chunks):
                # Generate a UUID for the document ID
                doc_id = str(uuid.uuid4())
                
                # Get custom metadata for this chunk if provided
                chunk_metadata = {
                    **metadata,  # Original metadata
                    "chunk_index": i,
                    "chunk_id": f"{metadata.get('id', 'doc')}_chunk_{i}",
                }
                
                # Add chunk-specific metadata if provided
                if custom_metadata_per_chunk and i < len(custom_metadata_per_chunk):
                    chunk_metadata.update(custom_metadata_per_chunk[i])
                
                doc = Document(
                    text=chunk,
                    metadata=chunk_metadata,
                    doc_id=doc_id
                )
                documents.append(doc)

            # Store documents in vector store
            if not self.vector_store.client.collection_exists(self.collection_name):
                index = VectorStoreIndex.from_documents(
                    documents,
                    embed_model=self.embedding_model,
                    storage_context=self.storage_context
                )
                # Persist the index and storage after creation
                Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
                index.storage_context.persist(persist_dir=self.persist_dir)
                logger.info(f"Created and persisted new index to {self.persist_dir}")
            else:
                index = load_index_from_storage(
                    storage_context=self.storage_context,
                    embed_model=self.embedding_model
                )
                index.refresh_ref_docs(
                    documents,
                    # embed_model=self.embedding_model,
                )

            logger.info(f"Added document with {len(chunks)} chunks")
            return metadata["id"]
            
        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}")
            raise

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents with optional filters using llama_index.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional filters for metadata fields
            
        Returns:
            List of SearchResult objects with their metadata
        """
        try:
            # Perform similarity search
            results = self.vector_store.query(
                query=query,
                limit=limit,
                service_context=self.service_context,
                filter=filters
            )
            
            # Format results into SearchResult objects
            formatted_results = []
            for result in results:
                search_result = SearchResult(
                    content=result.node.text,
                    document_id=result.node.metadata.get("document_id", ""),
                    chunk_index=result.node.metadata.get("chunk_index", 0),
                    score=result.score,
                    metadata=result.node.metadata.get("custom_metadata", {}),
                    file_path=result.node.metadata.get("file_path", ""),
                    file_name=result.node.metadata.get("file_name", ""),
                    owner_id=result.node.metadata.get("owner_id", ""),
                    created_at=result.node.metadata.get("created_at", None),
                    updated_at=result.node.metadata.get("updated_at", None)
                )
                formatted_results.append(search_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks using llama_index.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            bool: True if successful
        """
        try:
            # Delete all nodes with matching document_id
            self.vector_store.delete(
                doc_ids=[f"{document_id}_{i}" for i in range(10000)]  # Assuming max 10000 chunks per doc
            )
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise

    def update_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """Update metadata for an existing document."""
        try:
            # Update the document's metadata in Qdrant
            self.vector_store.update(
                doc_ids=[f"{document_id}_{i}" for i in range(10000)],  # Assuming max 10000 chunks per doc
                metadata=metadata_updates
            )
            logger.info(f"Updated metadata for document: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}")
            return False

    def get_document(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a document and its metadata by ID."""
        try:
            # Get all nodes with matching document_id
            nodes = self.vector_store.query(
                query="",  # Empty query to get all documents
                limit=10000,  # Assuming max 10000 chunks per doc
                service_context=self.service_context,
                filter={"document_id": document_id}
            )
            
            # Get metadata for each node
            metadata = {}
            for node in nodes:
                metadata.update(node.metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get document: {str(e)}")
            return None

    def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List documents matching the given filters using llama_index.
        
        Args:
            filters: Optional filters for metadata fields
            offset: Offset for pagination
            limit: Maximum number of results
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            # Get all nodes matching the filters
            nodes = self.vector_store.query(
                query="",  # Empty query to get all documents
                limit=limit,
                service_context=self.service_context,
                filter=filters
            )
            
            # Get unique document IDs
            document_ids = set()
            for node in nodes:
                doc_id = node.metadata.get("document_id", "")
                if doc_id not in document_ids:
                    document_ids.add(doc_id)
            
            # Get metadata for each document
            documents = []
            for doc_id in document_ids:
                # Get first node for this document's metadata
                node = next(
                    n for n in nodes 
                    if n.metadata.get("document_id") == doc_id
                )
                
                documents.append({
                    "document_id": doc_id,
                    "metadata": node.metadata
                })
            
            return documents[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise

    def health_check(self) -> bool:
        """
        Check the health of the vector database connection using llama_index.
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            # Try to get collection info
            self.vector_store.get_collection_info()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database."""
        try:
            stats = self.client.get_collection(collection_name=self.collection_name)
            return {
                "total_documents": stats.total_points,
                "total_chunks": stats.total_points,  # Assuming chunks are equivalent to points
                "storage_size": stats.storage_size,
                "index_size": stats.index_size,
                "last_updated": stats.last_updated.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {}