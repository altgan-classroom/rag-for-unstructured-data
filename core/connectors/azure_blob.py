from typing import Optional

from azure.storage.blob import BlobServiceClient

from . import BaseConnector


class AzureBlobConnector(BaseConnector):
    def __init__(self, config, user_access):
        super().__init__(config, user_access)
        self.connection_string = config.config["connection_string"]
        self.container_name = config.config["container_name"]
        self.client = None
        self.container_client = None

    def connect(self) -> None:
        try:
            self.client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self.container_client = self.client.get_container_client(
                self.container_name
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Azure Blob Storage: {str(e)}"
            ) from e

    def download_file(self, path: str, local_path: Optional[str] = None) -> str:
        self._check_permission("read")
        try:
            if not local_path:
                local_path = path.split("/")[-1]

            blob_client = self.container_client.get_blob_client(path)
            with open(local_path, "wb") as file:
                data = blob_client.download_blob()
                file.write(data.readall())
            return local_path
        except Exception as e:
            raise Exception(f"Failed to download file from Azure Blob: {str(e)}") from e

    def upload_file(self, local_path: str, remote_path: str) -> None:
        self._check_permission("write")
        try:
            blob_client = self.container_client.get_blob_client(remote_path)
            with open(local_path, "rb") as file:
                blob_client.upload_blob(file, overwrite=True)
        except Exception as e:
            raise Exception(f"Failed to upload file to Azure Blob: {str(e)}") from e

    def list_files(self, prefix: Optional[str] = None) -> list:
        self._check_permission("read")
        try:
            files = []
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            for blob in blobs:
                files.append(blob.name)
            return files
        except Exception as e:
            raise Exception(f"Failed to list files in Azure Blob: {str(e)}") from e

    def get_all_documents(self):
        """
        Retrieve all documents from Azure Blob Storage with their ACL information.
        
        Returns:
            list[dict]: List of documents with their metadata and permissions
        """
        self._check_permission("read")
        try:
            documents = []
            blobs = self.container_client.list_blobs()
            
            for blob in blobs:
                try:
                    # Get blob client for accessing ACL
                    blob_client = self.container_client.get_blob_client(blob.name)
                    
                    # Get ACL information
                    acl = blob_client.get_blob_acl()
                    
                    permissions = {
                        'owner': {
                            'id': acl.get('owner', {}).get('id'),
                            'display_name': acl.get('owner', {}).get('name')
                        },
                        'grants': []
                    }
                    
                    # Process ACL entries
                    for entry in acl.get('signed_identifiers', []):
                        permission_data = {
                            'grantee': {
                                'type': 'SignedIdentifier',
                                'id': entry.id
                            },
                            'permission': entry.access_policy.permission  # r(read), w(write), d(delete), l(list)
                        }
                        permissions['grants'].append(permission_data)
                    
                except Exception:
                    permissions = None
                
                documents.append({
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'content_type': blob.content_settings.content_type,
                    'etag': blob.etag,
                    'permissions': permissions
                })
            
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to get all documents from Azure Blob: {str(e)}") from e
