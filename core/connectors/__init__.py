from abc import ABC, abstractmethod
from typing import Optional

from .models import ConnectorConfig, UserAccess


class BaseConnector(ABC):
    """Abstract base class for all storage connectors."""

    def __init__(self, config: ConnectorConfig, user_access: UserAccess):
        self.config = config
        self.user_access = user_access
        self._validate_access()

    def _validate_access(self) -> None:
        """Validate that user has access to this connector."""
        if not self.config.enabled:
            raise PermissionError("This connector is disabled")
        if self.user_access.company_id != self.config.company_id:
            raise PermissionError("User does not belong to the company")

    def _check_permission(self, operation: str) -> None:
        """Check if user has permission for specific operation."""
        if not self.user_access.permissions.get(operation, False):
            raise PermissionError(f"User does not have {operation} permission")

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the storage system."""
        pass

    @abstractmethod
    def download_file(self, path: str, local_path: Optional[str] = None) -> str:
        """Download a file from storage to local filesystem."""
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file from local filesystem to storage."""
        pass

    @abstractmethod
    def get_all_documents(self):
        """
        Retrieve all documents from the connector.
        
        Returns:
            list: A list of documents
        """
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """
        Generate a URL for an object in the storage system.
        
        Args:
            path: Path to the object in the storage system
            
        Returns:
            str: URL for accessing the object
        """
        pass
