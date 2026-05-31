import json
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class ConnectorType(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_DRIVE = "google_drive"


class ConnectorConfig(BaseModel):
    connector_type: ConnectorType
    company_id: str
    config: Dict[str, Any]
    enabled: bool = True

    def to_dict(self):
        return {
            'connector_type': self.connector_type,
            'company_id': self.company_id,
            'config': self.config,
            'enabled': self.enabled
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)



class UserAccess(BaseModel):
    user_id: str
    company_id: str
    connector_type: ConnectorType
    permissions: Dict[str, bool] = Field(
        default_factory=lambda: {"read": True, "write": False}
    )

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'company_id': self.company_id,
            'connector_type': self.connector_type,
            'permissions': self.permissions
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
