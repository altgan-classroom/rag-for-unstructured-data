import os
import logging
import copy
import re
import time
import uuid
from typing import List, Dict, Any, Optional

from celery import Celery
from core.vector_db.services.qdrant import QdrantDB
from core.ingest.markdown import multimodal_extract, MarkDown
from core.connectors.factory import ConnectorFactory
from core.connectors.models import UserAccess, ConnectorConfig
from core.ingest.celery_app import celery_app
from core.ingest.llm import LLMClient
from core.ingest.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chunks(markdown: MarkDown, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks while maintaining page numbers.
    
    Args:
        text: List of strings where each string is a page's content
        chunk_size: Size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of dictionaries containing chunks with their starting page numbers
    """
    chunks = []
    current_chunk = []
    current_chunk_size = 0
    current_pages = []
    
    for page_num, page_text in enumerate(markdown.pages):
        # Split page text into words
        words = page_text.split()
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            # If adding this word would exceed chunk size
            if current_chunk_size + word_size > chunk_size and current_chunk:
                # Add current chunk with its starting page number
                content = f"Document Title: {markdown.metadata['doc_name']}\n" + ' '.join(current_chunk)
                chunks.append({
                    'content': content,
                    'page_number': current_pages[0] if current_pages else None
                })
                
                # Create overlap
                overlap_size = 0
                overlap_chunk = []
                
                # Add words from current chunk until we reach overlap size
                for i in range(len(current_chunk) - 1, -1, -1):
                    overlap_size += len(current_chunk[i]) + 1
                    overlap_chunk.insert(0, current_chunk[i])
                    if overlap_size >= overlap:
                        break
                
                # Start new chunk with overlap
                current_chunk = overlap_chunk
                current_chunk_size = overlap_size
                current_pages = [page_num + 1]  # Start fresh with current page
                
            # Add current word to chunk
            current_chunk.append(word)
            current_chunk_size += word_size
            current_pages.append(page_num + 1)
    
    # Add last chunk if it exists
    if current_chunk:
        content = f"Document Title: {markdown.metadata['doc_name']}\n" + ' '.join(current_chunk)
        chunks.append({
            'content': content,
            'page_number': current_pages[0] if current_pages else None
        })
    
    return chunks

@celery_app.task(bind=True)
def scan_and_enqueue_documents(
    self,
    connector_config: Dict[str, Any],
    user_access: Dict[str, Any],
    file_extensions: Optional[List[str]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    batch_size: int = 100
) -> Dict[str, Any]:
    """Scan connector and enqueue all documents for processing."""
    try:
        # Initialize connector using ConnectorFactory
        connector_config = ConnectorConfig.from_dict(connector_config)
        user_access = UserAccess.from_dict(user_access)
        connector = ConnectorFactory.create_connector(connector_config, user_access)  # Updated line
        connector.connect()

        # Get list of all files with their metadata
        all_documents = connector.get_all_documents()
        
        # Filter by file extensions if specified
        if file_extensions:
            filtered_documents = [
                doc for doc in all_documents 
                if any(doc.file_path.lower().endswith(ext.lower()) for ext in file_extensions)
            ]
        else:
            filtered_documents = all_documents

        total_docs = len(filtered_documents)
        processed_docs = 0
        failed_docs = []
        task_ids = []

        for i in range(0, total_docs, batch_size):
            batch = filtered_documents[i:i + batch_size]
            
            for doc_metadata in batch:
                try:
                    task = process_queued_document.delay(
                        document=doc_metadata,
                        connector_config=connector_config,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                    task_ids.append(task.id)
                    processed_docs += 1
                    
                except Exception as e:
                    failed_docs.append({
                        "document_metadata": doc_metadata,
                        "error": str(e)
                    })
                    logger.error(f"Failed to enqueue {doc_metadata}: {str(e)}")

            logger.info(f"Processed {processed_docs}/{total_docs} documents")

        return {
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "failed_documents": failed_docs,
            "task_ids": task_ids
        }

    except Exception as e:
        logger.error(f"Failed to scan connector: {str(e)}")
        raise

@celery_app.task(bind=True, max_retries=3)
def process_queued_document(
    self,
    document: Dict[str, Any],
    connector_config: Dict[str, Any],
    user_access: Dict[str, Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> bool:
    start_time = time.time()
    try:
        # Build the doc dict used downstream. Postgres no longer issues an id,
        # so generate a stable UUID per document. Permissions metadata (if any)
        # is preserved in the Qdrant payload but not persisted elsewhere.
        doc = copy.deepcopy(document)
        doc["id"] = doc.get("id") or str(uuid.uuid4())
        logger.info(f"Processing document: {doc.get('doc_name')} (id={doc['id']})")

        # Initialize connector using ConnectorFactory
        connector_config = ConnectorConfig.from_dict(connector_config)
        user_access = UserAccess.from_dict(user_access)
        connector = ConnectorFactory.create_connector(connector_config, user_access)  # Updated line
        
        try:
            # Extract content
            markdown = multimodal_extract(
                file_path=doc["s3_url"],
                connector=connector,
                metadata=copy.deepcopy(doc),
                use_llm_for_images=config.USE_LLM_FOR_IMAGES,
                llm_client=LLMClient(
                    provider=config.LLM_PROVIDER,
                    api_key=config.llm_api_key,
                ),
            )

            # Create chunks
            chunks = create_chunks(markdown, chunk_size, chunk_overlap)
            
            # Initialize custom_metadata_per_chunk with empty dicts
            custom_metadata_per_chunk = [{"page_number": chunk['page_number']} for chunk in chunks]
            
            # Process image metadata from content.metadata
            if hasattr(markdown, 'metadata') and "images" in markdown.metadata:
                # Extract image references from markdown content for each chunk
                for chunk_idx, chunk in enumerate(chunks):
                    # Find all image references in this chunk
                    image_refs = {}
                    # Find all image references in markdown format: ![alt text](image-ref:page_X_image_Y)
                    for match in re.finditer(r'!\[.*?\]\(image-ref:([^)]+)\)', chunk['content']):
                        image_ref = match.group(1)
                        if image_ref in markdown.metadata["images"]:
                            image_refs[image_ref] = markdown.metadata["images"][image_ref]
                    
                    # If we found any images in this chunk, add them to its metadata
                    if image_refs:
                        custom_metadata_per_chunk[chunk_idx]['images'] = image_refs
                    else:
                        custom_metadata_per_chunk[chunk_idx]['images'] = {}

            # Store in vector database with combined metadata
            vector_db = QdrantDB()
            vector_db.add_documents(
                chunks=[chunk['content'] for chunk in chunks],
                metadata=doc,
                custom_metadata_per_chunk=custom_metadata_per_chunk
            )

            logger.info(f"Successfully processed document: {doc}")
            return {
                'success': True,
                'document_id': doc.get('id'),
                'document_name': doc.get('doc_name'),
                'chunks_processed': len(chunks),
                'execution_time': f"{round(time.time() - start_time, 1)} sec"
            }

        except Exception as processing_error:
            logger.error(f"Processing error for document {doc}: {str(processing_error)}")
            raise processing_error

    except Exception as e:
        logger.error(f"Failed to process document {document.get('id')}: {str(e)}")
        self.retry(exc=e, countdown=60)

# Add periodic task to check queue health
@celery_app.task
def check_queue_health():
    """Periodic task to check queue health."""
    try:
        # Check Redis connection
        celery_app.connection().ensure_connection()
        
        # Check VectorDB health
        vectordb = QdrantDB()
        vectordb_status = vectordb.health_check()
        
        logger.info("Queue health check passed")
        return {
            "status": "healthy",
            "vectordb": vectordb_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }