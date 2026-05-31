from typing import Optional
import boto3
import io

from . import BaseConnector


class S3Connector(BaseConnector):
    def __init__(self, config, user_access):
        super().__init__(config, user_access)
        self.bucket = config.config["bucket"]
        self.aws_access_key_id = config.config["aws_access_key_id"]
        self.aws_secret_access_key = config.config["aws_secret_access_key"]
        self.region = config.config.get("region")
        self.client = None

    def connect(self) -> None:
        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region,
        )

    def download_file(self, path: str, local_path: Optional[str] = None) -> str:
        # self._check_permission("read")
        if not local_path:
            local_path = path.split("/")[-1]
        self.client.download_file(self.bucket, path, local_path) 
        return local_path

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        Upload a file to S3. Handles both file paths and BytesIO objects.
        
        Args:
            local_path: Either a file path or a BytesIO object containing the file data
            remote_path: Path in S3 where the file should be uploaded
        """
        # self._check_permission("write")
        
        # If local_path is a BytesIO object, use upload_fileobj
        if isinstance(local_path, io.BytesIO):
            self.client.upload_fileobj(local_path, self.bucket, remote_path)
        else:
            self.client.upload_file(local_path, self.bucket, remote_path)

    def get_url(self, path: str) -> str:
        """
        Generate a URL for an S3 object.
        
        Args:
            path: Path to the object in the bucket
            
        Returns:
            str: S3 URL for the object
        """
        return f"https://{self.bucket}.s3.amazonaws.com/{path}"

    def get_all_documents(self):
        """
        Retrieve all documents from the S3 bucket with their ACL information.
        
        Returns:
            list[dict]: List of documents with their metadata and permissions

        # Example ACL response structure
        {
            'permissions': {
                'owner': {
                    'id': '12345678abcdef',
                    'display_name': 'bucket-owner'
                },
                'grants': [
                    {
                        'grantee': {
                            'Type': 'CanonicalUser',
                            'ID': '12345678abcdef',
                            'DisplayName': 'bucket-owner'
                        },
                        'permission': 'FULL_CONTROL'
                    },
                    {
                        'grantee': {
                            'Type': 'Group',
                            'URI': 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers'
                        },
                        'permission': 'READ'
                    }
                ]
            }
        }
        """
        # self._check_permission("read")
        
        documents = []
        paginator = self.client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Skip folders (objects ending with '/')
                        if not obj['Key'].endswith('/'):
                            # Get ACL information for the object
                            try:
                                acl = self.client.get_object_acl(
                                    Bucket=self.bucket,
                                    Key=obj['Key']
                                )
                                permissions = {
                                    'owner': {
                                        'id': acl['Owner']['ID'],
                                        'display_name': acl['Owner'].get('DisplayName')
                                    },
                                    'grants': [{
                                        'grantee': grant['Grantee'],
                                        'permission': grant['Permission']
                                    } for grant in acl['Grants']]
                                }
                            except self.client.exceptions.ClientError:
                                permissions = None

                            documents.append({
                                'doc_name': obj['Key'].split('/')[-1],
                                's3_url': self.get_url(obj['Key']),
                                'content_type': obj['ContentType'],
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'],
                                'etag': obj['ETag'],
                                'permissions': permissions
                            })
            
            return documents
            
        except self.client.exceptions.ClientError as e:
            raise Exception(f"Failed to list objects in bucket: {str(e)}")
