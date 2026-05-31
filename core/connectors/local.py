import io
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import BaseConnector


class LocalFolderConnector(BaseConnector):
    """Filesystem-backed connector. Mirrors the S3Connector interface so the
    ingestion pipeline can run end-to-end without any cloud credentials.

    Expected config:
        {"root": "data/raw"}   # path relative to repo root, or absolute
    """

    def __init__(self, config, user_access):
        super().__init__(config, user_access)
        self.root = Path(config.config["root"]).expanduser().resolve()

    def connect(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _abs(self, path: str) -> Path:
        return (self.root / path).resolve()

    def download_file(self, path: str, local_path: Optional[str] = None) -> str:
        src = self._abs(path)
        if not src.is_file():
            raise FileNotFoundError(f"No such file under {self.root}: {path}")
        if not local_path:
            local_path = src.name
        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return str(dst)

    def upload_file(self, local_path, remote_path: str) -> None:
        dst = self._abs(remote_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(local_path, io.BytesIO):
            with open(dst, "wb") as f:
                f.write(local_path.getvalue())
        else:
            shutil.copy2(local_path, dst)

    def get_url(self, path: str) -> str:
        return self._abs(path).as_uri()

    def get_all_documents(self):
        documents = []
        for f in self.root.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(self.root).as_posix()
            stat = f.stat()
            content_type, _ = mimetypes.guess_type(f.name)
            documents.append({
                "doc_name": f.name,
                "s3_url": self.get_url(rel),
                "content_type": content_type,
                "key": rel,
                "size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime),
                "etag": None,
                "permissions": None,
            })
        return documents
