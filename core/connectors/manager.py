from typing import Dict

from .factory import ConnectorFactory
from .models import ConnectorConfig, ConnectorType, UserAccess


class ConnectorManager:
    def __init__(self):
        self.configs: Dict[str, Dict[ConnectorType, ConnectorConfig]] = {}
        self.user_access: Dict[str, Dict[str, UserAccess]] = {}

    def add_company_connector(self, config: ConnectorConfig) -> None:
        """Add or update a connector configuration for a company."""
        if config.company_id not in self.configs:
            self.configs[config.company_id] = {}
        self.configs[config.company_id][config.connector_type] = config

    def set_user_access(self, user_access: UserAccess) -> None:
        """Set user access permissions for a specific connector."""
        if user_access.user_id not in self.user_access:
            self.user_access[user_access.user_id] = {}
        self.user_access[user_access.user_id][user_access.connector_type] = user_access

    def get_connector(
        self, user_id: str, company_id: str, connector_type: ConnectorType
    ):
        """Get a connector instance for a specific user and company."""
        if company_id not in self.configs:
            raise ValueError(f"No configurations found for company {company_id}")

        config = self.configs[company_id].get(connector_type)
        if not config:
            raise ValueError(f"No configuration found for {connector_type}")

        user_access = self.user_access.get(user_id, {}).get(connector_type)
        if not user_access:
            raise PermissionError(f"User {user_id} has no access configuration")

        return ConnectorFactory.create_connector(config, user_access)
