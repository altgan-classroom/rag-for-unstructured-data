import io
import json
from typing import List, Optional

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from . import BaseConnector


class GoogleDriveConnector(BaseConnector):
    def __init__(self, config, user_access):
        super().__init__(config, user_access)
        self.credentials_info = config.config["credentials"]
        self.service = None

    def connect(self) -> None:
        try:
            # Support both service account and OAuth2 credentials
            if isinstance(self.credentials_info, dict):
                credentials = ServiceAccountCredentials.from_service_account_info(
                    self.credentials_info,
                    scopes=["https://www.googleapis.com/auth/drive"],
                )
            else:
                credentials = Credentials.from_authorized_user_info(
                    json.loads(self.credentials_info),
                    scopes=["https://www.googleapis.com/auth/drive"],
                )

            self.service = build("drive", "v3", credentials=credentials)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Google Drive: {str(e)}") from e

    def download_file(self, file_id: str, local_path: Optional[str] = None) -> str:
        self._check_permission("read")
        try:
            if not local_path:
                file_metadata = self.service.files().get(fileId=file_id).execute()
                local_path = file_metadata["name"]

            request = self.service.files().get_media(fileId=file_id)
            with io.FileIO(local_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    _, done = downloader.next_chunk()
            return local_path
        except Exception as e:
            raise Exception(
                f"Failed to download file from Google Drive: {str(e)}"
            ) from e

    def upload_file(
        self, local_path: str, remote_path: str, parent_folder_id: Optional[str] = None
    ) -> str:
        self._check_permission("write")
        try:
            file_metadata = {
                "name": remote_path.split("/")[-1],
                "parents": [parent_folder_id] if parent_folder_id else None,
            }

            media = MediaFileUpload(local_path, resumable=True)

            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )

            return file.get("id")
        except Exception as e:
            raise Exception(f"Failed to upload file to Google Drive: {str(e)}") from e

    def list_files(
        self, folder_id: Optional[str] = None, query: Optional[str] = None
    ) -> List[dict]:
        self._check_permission("read")
        try:
            # Construct query
            q_parts = []
            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")
            if query:
                q_parts.append(query)

            final_query = " and ".join(q_parts) if q_parts else None

            results = []
            page_token = None

            while True:
                fields = (
                    "nextPageToken, "
                    "files(id, name, mimeType, createdTime, modifiedTime)"
                )
                response = (
                    self.service.files()
                    .list(
                        q=final_query,
                        spaces="drive",
                        fields=fields,
                        pageToken=page_token,
                    )
                    .execute()
                )

                results.extend(response.get("files", []))
                page_token = response.get("nextPageToken")

                if not page_token:
                    break

            return results
        except Exception as e:
            raise Exception(f"Failed to list files in Google Drive: {str(e)}") from e

    def create_folder(
        self, folder_name: str, parent_folder_id: Optional[str] = None
    ) -> str:
        self._check_permission("write")
        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id] if parent_folder_id else None,
            }

            file = (
                self.service.files().create(body=file_metadata, fields="id").execute()
            )

            return file.get("id")
        except Exception as e:
            raise Exception(f"Failed to create folder in Google Drive: {str(e)}") from e

    def get_all_documents(self):
        """
        Retrieve all documents from Google Drive with their permission information.
        
        Returns:
            list[dict]: List of documents with their metadata and permissions
        """
        self._check_permission("read")
        try:
            # Exclude folders from results
            query = "mimeType != 'application/vnd.google-apps.folder'"
            documents = []
            
            files = self.list_files(query=query)
            for file in files:
                try:
                    # Get permissions for each file
                    permissions = self.service.permissions().list(
                        fileId=file['id'],
                        fields='permissions(id,type,emailAddress,role,displayName)'
                    ).execute()
                    
                    file_permissions = {
                        'owner': None,  # Will be populated from permissions
                        'grants': []
                    }
                    
                    # Process permissions
                    for perm in permissions.get('permissions', []):
                        permission_data = {
                            'grantee': {
                                'type': perm['type'],  # user, group, domain, anyone
                                'email': perm.get('emailAddress'),
                                'display_name': perm.get('displayName')
                            },
                            'permission': perm['role']  # owner, organizer, fileOrganizer, writer, commenter, reader
                        }
                        
                        # Mark the owner
                        if perm['role'] == 'owner':
                            file_permissions['owner'] = permission_data['grantee']
                        else:
                            file_permissions['grants'].append(permission_data)
                    
                except Exception:
                    file_permissions = None
                
                documents.append({
                    'id': file['id'],
                    'name': file['name'],
                    'mime_type': file['mimeType'],
                    'created_time': file['createdTime'],
                    'modified_time': file['modifiedTime'],
                    'permissions': file_permissions
                })
            
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to get all documents from Google Drive: {str(e)}") from e
