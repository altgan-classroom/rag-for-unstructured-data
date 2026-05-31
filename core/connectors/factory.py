from typing import Callable, Dict

from . import BaseConnector
from .models import ConnectorConfig, ConnectorType, UserAccess


def _load_local():
    from .local import LocalFolderConnector
    return LocalFolderConnector


def _load_s3():
    from .s3 import S3Connector
    return S3Connector


def _load_azure_blob():
    from .azure_blob import AzureBlobConnector
    return AzureBlobConnector


def _load_google_drive():
    from .google_drive import GoogleDriveConnector
    return GoogleDriveConnector


class ConnectorFactory:
    # Lazy loaders: each cloud connector imports its SDK at module top, so we
    # defer the import until the corresponding ConnectorType is actually
    # requested. This keeps the ingest image slim (LOCAL-only) while leaving
    # the S3/Azure/Google sources in the repo for reference.
    _loaders: Dict[ConnectorType, Callable[[], type]] = {
        ConnectorType.LOCAL: _load_local,
        ConnectorType.S3: _load_s3,
        ConnectorType.AZURE_BLOB: _load_azure_blob,
        ConnectorType.GOOGLE_DRIVE: _load_google_drive,
    }

    @classmethod
    def create_connector(
        cls, config: ConnectorConfig, user_access: UserAccess
    ) -> BaseConnector:
        loader = cls._loaders.get(config.connector_type)
        if not loader:
            raise ValueError(f"Unsupported connector type: {config.connector_type}")

        try:
            connector_class = loader()
        except ImportError as exc:
            raise ImportError(
                f"Connector '{config.connector_type.value}' requires extra "
                f"dependencies that are not installed in this image. "
                f"Install them or use ConnectorType.LOCAL. ({exc})"
            ) from exc

        return connector_class(config, user_access)
