"""Enqueue every PDF under data/raw/ for ingestion.

Run order:
  1. python scripts/download_data.py            # populates data/raw/
  2. docker compose -f deployment/docker-compose.yml up -d qdrant redis ingest
  3. python scripts/run_ingest.py               # this script

The Celery worker (the `ingest` service in docker-compose) picks up every
enqueued task and writes chunks into Qdrant.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "deployment" / ".env"
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "raw"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Local folder of source PDFs (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=1000, help="Chunk size in characters"
    )
    parser.add_argument(
        "--chunk-overlap", type=int, default=200, help="Chunk overlap in characters"
    )
    parser.add_argument(
        "--category",
        default="course",
        help="Tag stored in Qdrant payload alongside each chunk",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[".pdf"],
        help="File extensions to ingest (default: .pdf)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Poll task status until everything completes",
    )
    args = parser.parse_args()

    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    data_dir = args.data_dir.expanduser().resolve()
    if not data_dir.is_dir():
        print(f"ERROR: data dir does not exist: {data_dir}", file=sys.stderr)
        print("Run: python scripts/download_data.py", file=sys.stderr)
        return 2

    files = [
        p for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {e.lower() for e in args.extensions}
    ]
    if not files:
        print(f"ERROR: no matching files under {data_dir}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(REPO_ROOT))
    from core.connectors.models import ConnectorConfig, ConnectorType, UserAccess
    from core.ingest.queue import DocumentQueue

    # Pass the path *relative* to the repo root so the same config works
    # whether this script runs on the host or inside the worker container
    # (the repo is mounted at /app inside the ingest container).
    try:
        connector_root = str(data_dir.relative_to(REPO_ROOT))
    except ValueError:
        connector_root = str(data_dir)

    connector_config = ConnectorConfig(
        connector_type=ConnectorType.LOCAL,
        company_id="course",
        config={"root": connector_root},
    )
    user_access = UserAccess(
        user_id=os.environ.get("USER", "learner"),
        company_id="course",
        connector_type=ConnectorType.LOCAL,
        permissions={"read": True, "write": False},
    )

    queue = DocumentQueue()
    task_ids = []
    print(f"Enqueueing {len(files)} file(s) from {data_dir} ...")
    for f in files:
        rel = f.relative_to(data_dir).as_posix()
        metadata = {
            "doc_name": f.name,
            "s3_url": rel,                      # used by the connector as the key
            "content_type": "application/pdf",
            "size": f.stat().st_size,
            "permissions": {"grants": [{"grantee": "Public"}]},
            "category": args.category,
        }
        task_id = queue.enqueue(
            document_metadata=metadata,
            connector_config=connector_config,
            user_access=user_access,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"  enqueued  {rel:60s}  task={task_id}")
        task_ids.append(task_id)

    print(f"\nEnqueued {len(task_ids)} tasks. Watch progress with:")
    print("  docker compose -f deployment/docker-compose.yml logs -f ingest")

    if args.watch:
        print("\nPolling task status (Ctrl-C to stop) ...")
        pending = set(task_ids)
        while pending:
            time.sleep(5)
            done = [tid for tid in pending if queue.get_task_status(tid) in {"SUCCESS", "FAILURE"}]
            for tid in done:
                print(f"  finished  {tid}  -> {queue.get_task_status(tid)}")
                pending.discard(tid)
        print("All tasks complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
