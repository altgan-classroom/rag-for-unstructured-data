from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
from .tasks import process_queued_document, scan_and_enqueue_documents
from core.connectors.models import UserAccess, ConnectorConfig

# Configure logging
logger = logging.getLogger(__name__)

class DocumentQueue:
    """
    Manages document processing queue using Celery.
    Handles enqueueing documents and checking their processing status.
    """
    
    def __init__(self):
        """Initialize document queue."""
        self.pending_documents: List[Dict[str, Any]] = []

    def enqueue(
        self,
        document_metadata: Dict[str, Any],
        connector_config: ConnectorConfig,
        user_access: UserAccess,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> str:
        """
        Add a document to the processing queue.
        
        Args:
            document_metadata: Complete metadata for the document
            connector_config: Configuration for the storage connector
            chunk_size: Size of text chunks for processing
            chunk_overlap: Overlap between chunks
            
        Returns:
            task_id: Celery task ID for tracking the document processing
        """
        try:
            task = process_queued_document.delay(
                document=document_metadata,
                connector_config=connector_config.to_dict(),
                user_access=user_access.to_dict(),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            logger.info(f"Successfully enqueued document: {document_metadata['s3_url']}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue document {document_metadata['s3_url']}: {str(e)}")
            raise

    def enqueue_all_from_connector(
        self,
        connector_config: ConnectorConfig,
        user_access: UserAccess,
        file_extensions: Optional[List[str]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        batch_size: int = 100
    ) -> str:
        """
        Scan connector and enqueue all documents for processing.
        
        Args:
            connector_config: Configuration for the storage connector
            file_extensions: List of file extensions to process
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            batch_size: Number of documents to process in each batch
        """
        try:
            task = scan_and_enqueue_documents.delay(
                connector_config=connector_config.to_dict(),
                user_access=user_access.to_dict(),
                file_extensions=file_extensions,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                batch_size=batch_size
            )
            logger.info(f"Started scanning connector for documents. Task ID: {task.id}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to start connector scanning: {str(e)}")
            raise

    def get_task_status(self, task_id: str) -> str:
        """
        Get the status of a document processing task.
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Status of the task (PENDING, STARTED, SUCCESS, FAILURE, etc.)
        """
        try:
            task = process_queued_document.AsyncResult(task_id)
            return task.status
        except Exception as e:
            logger.error(f"Failed to get status for task {task_id}: {str(e)}")
            raise 