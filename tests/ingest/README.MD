## Instructiosn to RUn test_enequeue_dump.py
1) go to deployment folder in Orca and 0start ingest docker service using 
```sudo docker compose up ingest```
2) open a new terminal 
3) in tests/ingest/ingest_config/config.yaml, upodate ```COLLECTION_NAME``` as per category documents
4) Update the document list in csv file stored in "data/file_storage/cloud/jb_infra_linkdocs.csv" file
5) Update AWS credentials and folder location in .env file.
6) from Orca folder run
```REDIS_URL=redis://localhost:6379/0 python -m tests.ingest.test_enqueue_dump```
