# test_enqueue.py
import os
from core.ingest.queue import DocumentQueue
from core.connectors.models import ConnectorConfig, ConnectorType, UserAccess

from dotenv import load_dotenv
load_dotenv("deployment/.env")   


# Create an instance of DocumentQueue
document_queue = DocumentQueue()

document_metadata = {
    'doc_name': '1211523415_20190529_CCS1_Well_Integrity_Report_with_PNX_20190306', 
    's3_url': 'https://orca-rag-documents.s3.amazonaws.com/oil-and-gas/1211523415_20190529_CCS1_Well_Integrity_Report_with_PNX_20190306.pdf',
    'content_type': 'pdf', 'size': 1800.0,
    'permissions': {'grants': [{'grantee': 'Public'}]},
    'category': 'Oil and Gas',            
 }

connector_config = ConnectorConfig(
    connector_type=ConnectorType.S3,
    company_id="altgan",
    config={
        "bucket": os.environ.get("AWS_S3_BUCKET_NAME"),
        "region": os.environ.get("AWS_REGION"),
        "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY")
    }
)

user_access = UserAccess(
    user_id="ram",
    company_id="altgan",
    connector_type=ConnectorType.S3,
)

# Enqueue the document
try:
    task_id = document_queue.enqueue(
        document_metadata=document_metadata,
        connector_config=connector_config,
        user_access=user_access,
        chunk_size=1000,
        chunk_overlap=200
    )
    print(f"Document enqueued successfully. Task ID: {task_id}")
except Exception as e:
    print(f"Error enqueuing document: {str(e)}")