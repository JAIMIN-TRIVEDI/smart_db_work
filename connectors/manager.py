from __future__ import annotations

from connectors.mysql_connector import MySQLConnector
from connectors.mongo_connector import MongoConnector

from db_models.database import DatabaseConfig

from exception.exceptions import (
    UnsupportedDatabaseError,
    DatabaseNotConnectedError,
)


class ConnectionManager:

    def __init__(self):

        # connection_name -> connector
        self.connections = {}

    ########################################################

    def connect(self, connection_name: str, config: DatabaseConfig):

        db = config.database_type.lower()

        if db == "mysql":

            connector = MySQLConnector()

        elif db == "mongodb":

            connector = MongoConnector()

        else:

            raise UnsupportedDatabaseError(f"{db} not supported.")

        connector.connect(config)

        self.connections[connection_name] = connector

        return connector

    ########################################################

    def disconnect(self, connection_name: str):

        connector = self.connections.get(connection_name)

        if connector:

            connector.disconnect()

            del self.connections[connection_name]

    ########################################################

    def get_connection(self, connection_name: str):

        if connection_name not in self.connections:

            raise DatabaseNotConnectedError("Connection not found.")

        return self.connections[connection_name]

    ########################################################

    def is_connected(self, connection_name: str):

        if connection_name not in self.connections:

            return False

        return self.connections[connection_name].is_connected

    ########################################################

    def list_connections(self):

        return list(self.connections.keys())


connection_manager = ConnectionManager()
