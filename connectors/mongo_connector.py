from __future__ import annotations

import ast
import re
from urllib.parse import quote_plus

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from db_models.database import DatabaseConfig
from exception.exceptions import DatabaseConnectionError


class MongoConnector:
    """
    MongoDB connector with:
    - verified database selection
    - schema inference
    - safe execution of supported read-only Mongo shell-style queries
    """

    def __init__(self):
        self.client: MongoClient | None = None
        self.db = None
        self.config: DatabaseConfig | None = None

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.db is not None

    def connect(self, config: DatabaseConfig) -> bool:
        try:
            username = quote_plus(config.username)
            password = quote_plus(config.password)

            uri = (
                f"mongodb+srv://{username}:{password}"
                f"@{config.host}"
                "?retryWrites=true&w=majority"
            )

            print(f"Connecting to MongoDB cluster: {config.host}")

            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )

            client.admin.command("ping")
            print("MongoDB authentication successful.")

            database_names = client.list_database_names()

            print(
                "Available MongoDB databases:",
                database_names,
            )
            print(
                "Requested database:",
                config.database,
            )

            if config.database in database_names:
                selected_database = config.database
                print(
                    "Exact database match found:",
                    selected_database,
                )
            else:
                case_insensitive_match = next(
                    (
                        database_name
                        for database_name in database_names
                        if database_name.lower() == config.database.lower()
                    ),
                    None,
                )

                if case_insensitive_match is None:
                    client.close()
                    raise DatabaseConnectionError(
                        f"Database '{config.database}' was not found. "
                        f"Available databases: {database_names}"
                    )

                selected_database = case_insensitive_match

                print("Database matched with different casing:")
                print(f"Requested: {config.database}")
                print(f"Actual: {selected_database}")

            database = client[selected_database]
            collection_names = database.list_collection_names()

            print(
                f"Collections in '{selected_database}':",
                collection_names,
            )

            self.client = client
            self.db = database
            self.config = config

            print("MongoDB connected successfully.")
            print("Selected database:", selected_database)
            print("Collection count:", len(collection_names))

            return True

        except Exception as exc:
            self.client = None
            self.db = None
            self.config = None

            if isinstance(exc, DatabaseConnectionError):
                raise

            raise DatabaseConnectionError(str(exc)) from exc

    def disconnect(self):
        if self.client is not None:
            self.client.close()

        self.client = None
        self.db = None
        self.config = None

    def ping(self) -> bool:
        if self.client is None:
            return False

        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def list_collections(self) -> list[str]:
        if self.db is None:
            raise DatabaseConnectionError("Database not connected.")

        try:
            return self.db.list_collection_names()
        except PyMongoError as exc:
            raise DatabaseConnectionError(str(exc)) from exc

    # ======================================================
    # QUERY EXECUTION
    # ======================================================

    def execute_query(self, query: str):
        """
        Execute supported read-only MongoDB shell-style queries.

        Supported:
        - db.collection.find({})
        - db.collection.find({...})
        - db.collection.find({...}).limit(n)
        - db.collection.find({...}).sort({...})
        - db.collection.find({...}).sort({...}).limit(n)
        - db.collection.find({...}).skip(n).limit(n)
        - db.collection.findOne({...})
        - db.collection.countDocuments({...})
        - db.collection.distinct("field")
        - db.collection.distinct("field", {...})

        Write operations are intentionally excluded. They should
        go through risk analysis, demo preview, confirmation, and
        explicit approval before live execution.
        """

        if self.db is None:
            raise DatabaseConnectionError("Database not connected.")

        if not query or not query.strip():
            raise DatabaseConnectionError("MongoDB query is empty.")

        query = query.strip().rstrip(";")

        print("=" * 80)
        print("MONGO QUERY EXECUTION")
        print("Query:", query)

        # ==================================================
        # FIND WITH OPTIONAL SORT / SKIP / LIMIT
        # ==================================================

        find_match = re.fullmatch(
            r"""
            db\.
            (?P<collection>[A-Za-z_][A-Za-z0-9_]*)
            \.
            find
            \(
                (?P<filter>\{.*?\})
            \)
            (?:
                \.sort
                \(
                    (?P<sort>\{.*?\})
                \)
            )?
            (?:
                \.skip
                \(
                    (?P<skip>\d+)
                \)
            )?
            (?:
                \.limit
                \(
                    (?P<limit>\d+)
                \)
            )?
            """,
            query,
            re.VERBOSE | re.DOTALL,
        )

        if find_match:
            collection_name = find_match.group("collection")

            filter_query = self._parse_mongo_object(find_match.group("filter"))

            sort_text = find_match.group("sort")
            skip_text = find_match.group("skip")
            limit_text = find_match.group("limit")

            print("Mongo operation: find")
            print("Collection:", collection_name)
            print("Filter:", filter_query)

            cursor = self.db[collection_name].find(filter_query)

            if sort_text:
                sort_query = self._parse_mongo_object(sort_text)

                sort_spec = []

                for field_name, direction in sort_query.items():
                    try:
                        direction = int(direction)
                    except (TypeError, ValueError):
                        raise DatabaseConnectionError(
                            "MongoDB sort direction must be "
                            "1 for ascending or -1 for descending."
                        )

                    if direction not in (-1, 1):
                        raise DatabaseConnectionError(
                            "MongoDB sort direction must be "
                            "1 for ascending or -1 for descending."
                        )

                    sort_spec.append((field_name, direction))

                print("Sort:", sort_spec)
                cursor = cursor.sort(sort_spec)

            if skip_text is not None:
                skip_value = int(skip_text)
                print("Skip:", skip_value)
                cursor = cursor.skip(skip_value)

            # Keep a safe default cap when the query has no limit.
            limit_value = int(limit_text) if limit_text is not None else 100

            print("Limit:", limit_value)
            cursor = cursor.limit(limit_value)

            documents = list(cursor)

            return [self._serialize_document(document) for document in documents]

        # ==================================================
        # FIND ONE
        # ==================================================

        find_one_match = re.fullmatch(
            r"""
            db\.
            (?P<collection>[A-Za-z_][A-Za-z0-9_]*)
            \.
            findOne
            \(
                (?P<filter>\{.*\})
            \)
            """,
            query,
            re.VERBOSE | re.DOTALL,
        )

        if find_one_match:
            collection_name = find_one_match.group("collection")

            filter_query = self._parse_mongo_object(find_one_match.group("filter"))

            print("Mongo operation: findOne")
            print("Collection:", collection_name)
            print("Filter:", filter_query)

            document = self.db[collection_name].find_one(filter_query)

            if document is None:
                return []

            return [self._serialize_document(document)]

        # ==================================================
        # COUNT DOCUMENTS
        # ==================================================

        count_match = re.fullmatch(
            r"""
            db\.
            (?P<collection>[A-Za-z_][A-Za-z0-9_]*)
            \.
            countDocuments
            \(
                (?P<filter>\{.*\})
            \)
            """,
            query,
            re.VERBOSE | re.DOTALL,
        )

        if count_match:
            collection_name = count_match.group("collection")

            filter_query = self._parse_mongo_object(count_match.group("filter"))

            print("Mongo operation: countDocuments")
            print("Collection:", collection_name)
            print("Filter:", filter_query)

            count = self.db[collection_name].count_documents(filter_query)

            return [{"count": count}]

        # ==================================================
        # DISTINCT
        # ==================================================

        distinct_match = re.fullmatch(
            r"""
            db\.
            (?P<collection>[A-Za-z_][A-Za-z0-9_]*)
            \.
            distinct
            \(
                ["']
                (?P<field>[^"']+)
                ["']
                (?:
                    \s*,\s*
                    (?P<filter>\{.*\})
                )?
            \)
            """,
            query,
            re.VERBOSE | re.DOTALL,
        )

        if distinct_match:
            collection_name = distinct_match.group("collection")

            field_name = distinct_match.group("field")

            filter_text = distinct_match.group("filter")

            filter_query = self._parse_mongo_object(filter_text) if filter_text else {}

            print("Mongo operation: distinct")
            print("Collection:", collection_name)
            print("Field:", field_name)
            print("Filter:", filter_query)

            values = self.db[collection_name].distinct(
                field_name,
                filter_query,
            )

            return [{field_name: self._serialize_value(value)} for value in values]

        raise DatabaseConnectionError("Unsupported MongoDB query format: " f"{query}")

    def _parse_mongo_object(
        self,
        object_text: str,
    ) -> dict:
        """
        Parse simple Mongo shell object syntax.

        Example:
            { storeLocation: "Denver" }

        becomes:
            {"storeLocation": "Denver"}

        Also supports nested objects and keys such as $gt.
        """

        text = object_text.strip()

        # Quote unquoted Mongo/JS object keys.
        text = re.sub(
            r"([{,]\s*)" r"([A-Za-z_$][A-Za-z0-9_.$]*)" r"\s*:",
            r'\1"\2":',
            text,
        )

        # Convert JS literals to Python literals.
        text = re.sub(
            r"\btrue\b",
            "True",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bfalse\b",
            "False",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bnull\b",
            "None",
            text,
            flags=re.IGNORECASE,
        )

        try:
            parsed = ast.literal_eval(text)
        except Exception as exc:
            raise DatabaseConnectionError(
                "Unable to parse MongoDB filter " f"'{object_text}'. Reason: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise DatabaseConnectionError("MongoDB filter must be an object.")

        return parsed

    def _serialize_document(
        self,
        document: dict,
    ) -> dict:
        return {key: self._serialize_value(value) for key, value in document.items()}

    def _serialize_value(self, value):
        if isinstance(value, ObjectId):
            return str(value)

        if isinstance(value, dict):
            return {
                key: self._serialize_value(nested_value)
                for key, nested_value in value.items()
            }

        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass

        return value

    # ======================================================
    # SCHEMA DISCOVERY
    # ======================================================

    @staticmethod
    def _mongo_type(value) -> str:
        if value is None:
            return "null"

        return type(value).__name__

    def get_schema(
        self,
        sample_size: int = 20,
    ) -> dict:
        """
        Infer collection schemas by sampling documents.
        """

        if self.db is None:
            raise DatabaseConnectionError("Database not connected.")

        schema = {}
        collections = self.db.list_collection_names()

        print(
            "Mongo collections found:",
            collections,
        )

        for collection_name in collections:
            collection = self.db[collection_name]

            field_types: dict[str, set[str]] = {}
            field_presence: dict[str, int] = {}

            documents = list(collection.find({}).limit(sample_size))

            total_documents = len(documents)

            if total_documents == 0:
                schema[collection_name] = {
                    "type": "collection",
                    "fields": [],
                }
                continue

            for document in documents:
                for key, value in document.items():
                    field_types.setdefault(
                        key,
                        set(),
                    ).add(self._mongo_type(value))

                    field_presence[key] = field_presence.get(key, 0) + 1

            fields = []

            for field_name in sorted(field_types.keys()):
                detected_types = sorted(field_types[field_name])

                fields.append(
                    {
                        "name": field_name,
                        "type": " | ".join(detected_types),
                        "nullable": (
                            field_presence.get(
                                field_name,
                                0,
                            )
                            < total_documents
                        ),
                    }
                )

            schema[collection_name] = {
                "type": "collection",
                "fields": fields,
            }

        print(
            "Mongo schema generated:",
            schema,
        )

        return schema

    def get_database(self):
        if self.db is None:
            raise DatabaseConnectionError("Database not connected.")

        return self.db
