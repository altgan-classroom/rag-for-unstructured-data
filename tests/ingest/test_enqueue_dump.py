# test_enqueue.py
import os
import csv
from core.ingest.queue import DocumentQueue
from core.connectors.models import ConnectorConfig, ConnectorType, UserAccess

from dotenv import load_dotenv
load_dotenv("deployment/.env")  

# Create an instance of DocumentQueue
document_queue = DocumentQueue()

# Connector configuration
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

# User access configuration
user_access = UserAccess(
    user_id="ram",
    company_id="altgan",
    connector_type=ConnectorType.S3,
)

csv_file_path = "data/file_storage/cloud/oil_and_gas_files_1st_35.csv"

# Read CSV file and enqueue documents
try:
    with open(csv_file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            s3_url = row['s3_url']
            # Extract document name from URL
            doc_name = s3_url.split('/')[-1].split('.')[0]
            document_metadata = {
                'doc_name': doc_name,
                's3_url': s3_url,
                'content_type': 'pdf',
                'size': row['size'],
                'permissions': {'grants': [{'grantee': 'Public'}]},
                'category': 'Oil and Gas',
            }
            
            # Enqueue the document
            task_id = document_queue.enqueue(
                document_metadata=document_metadata,
                connector_config=connector_config,
                user_access=user_access,
                chunk_size=1000,
                chunk_overlap=200
            )
            print(f"Document {doc_name} enqueued successfully. Task ID: {task_id}")
except Exception as e:
    print(f"Error processing CSV or enqueuing document: {str(e)}")