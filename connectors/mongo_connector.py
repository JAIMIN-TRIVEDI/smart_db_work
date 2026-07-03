from __future__ import annotations
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


from db_models.database import DatabaseConfig
from exception.exceptions import DatabaseConnectionError


class MongoConnector:
    """
    MongoDB Connector
    """

    def __init__(self):

        self.client: MongoClient | None = None
        self.db = None
        self.config = None

    @property
    def is_connected(self):

        return self.client is not None

    def connect(self, config: DatabaseConfig):

        try:
            username = quote_plus(config.username)
            password = quote_plus(config.password)

            uri = (
                f"mongodb+srv://{username}:{password}"
                f"@{config.host}/{config.database}"
                "?retryWrites=true&w=majority"
            )
            print(uri)
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
            )

            self.client.admin.command("ping")

            self.db = self.client[config.database]

            self.config = config

            return True

        except ConnectionFailure as e:
            raise DatabaseConnectionError(str(e))

    def disconnect(self):

        if self.client:
            self.client.close()

        self.client = None
        self.db = None
        self.config = None

    def ping(self):

        if not self.client:
            return False

        try:

            self.client.admin.command("ping")
            return True

        except Exception:
            return False

    def list_collections(self):

        if not self.db:
            raise DatabaseConnectionError("Database not connected.")

        return self.db.list_collection_names()
    
    
    def get_schema(self) -> dict:
        """
        Returns MongoDB collection schema by sampling one document
        from each collection.

        {
            "users": {
                "fields": [
                    {
                        "name": "_id",
                        "type": "ObjectId"
                    },
                    {
                        "name": "name",
                        "type": "str"
                    }
                ]
            }
        }
        """

        if not self.db:
            raise DatabaseConnectionError("Database not connected.")

        schema = {}

        collections = self.db.list_collection_names()

        for collection_name in collections:

            collection = self.db[collection_name]

            sample = collection.find_one()

            if sample is None:
                schema[collection_name] = {
                    "fields": []
                }
                continue

            schema[collection_name] = {
                "fields": [
                    {
                        "name": key,
                        "type": type(value).__name__
                    }
                    for key, value in sample.items()
                ]
            }

        return schema

    def get_database(self):

        if not self.db:
            raise DatabaseConnectionError("Database not connected.")

        return self.db
