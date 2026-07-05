from __future__ import annotations

import json
import re
import shutil
import traceback
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from connectors.manager import connection_manager
from db_models.database import DatabaseConfig
from exception.exceptions import DatabaseNotConnectedError
from State.DBState import AgentState


class SchemaService:
    """
    Builds and queries a per-project schema index.

    - Supports SQL schemas using "columns"
    - Supports MongoDB schemas using "fields"
    - Never sends an empty document list to Chroma
    - Persists a JSON manifest for keyword fallback
    - Uses vector retrieval when available
    - Falls back to keyword retrieval when vector search fails
    """

    def __init__(self):
        self.base_dir = Path("storage/data/schema_vectors")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self._embeddings = None

        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            self._embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

        except Exception as exc:
            print("Schema embeddings unavailable, " f"using keyword fallback: {exc}")

    def _get_connector(self, state: AgentState):
        try:
            return connection_manager.get_connection(state.connection_name)

        except DatabaseNotConnectedError:
            if not state.connection_name or not state.database_config:
                raise

            return connection_manager.connect(
                state.connection_name,
                DatabaseConfig(**state.database_config),
            )

    def _project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    def _collection_name(self, state: AgentState) -> str:
        raw_name = state.project_id or state.connection_name or "default"

        sanitized = re.sub(
            r"[^A-Za-z0-9_.-]",
            "_",
            raw_name,
        )

        return f"schema_{sanitized}"

    def _schema_to_documents(
        self,
        schema: dict[str, Any],
    ) -> list[Document]:
        documents: list[Document] = []

        if not schema:
            print("_schema_to_documents received empty schema.")
            return documents

        for object_name, object_data in schema.items():
            if not isinstance(object_data, dict):
                print(f"Skipping {object_name}: " "schema data is not a dict.")
                continue

            columns = object_data.get("columns")
            fields = object_data.get("fields")

            if isinstance(columns, list):
                items = columns
                object_type = "table"

            elif isinstance(fields, list):
                items = fields
                object_type = "collection"

            else:
                items = []
                object_type = object_data.get("type") or "table"

            heading = "Collection" if object_type == "collection" else "Table"

            lines = [f"{heading}: {object_name}"]

            for item in items:
                if isinstance(item, dict):
                    item_name = (
                        item.get("name")
                        or item.get("column")
                        or item.get("field")
                        or "unknown_field"
                    )

                    item_type = item.get(
                        "type",
                        "unknown",
                    )

                    nullable = item.get("nullable")
                    key = item.get("key")

                    line = f"- {item_name} " f"({item_type})"

                    if nullable is not None:
                        line += f" nullable={nullable}"

                    if key:
                        line += f" key={key}"

                    lines.append(line)

                else:
                    lines.append(f"- {str(item)}")

            documents.append(
                Document(
                    page_content="\n".join(lines),
                    metadata={
                        "table_name": object_name,
                        "object_name": object_name,
                        "object_type": object_type,
                    },
                )
            )

        print(
            "_schema_to_documents generated:",
            len(documents),
        )

        return documents

    def _write_index_manifest(
        self,
        project_dir: Path,
        schema: dict[str, Any],
        documents: list[Document],
    ):
        manifest = {
            "schema": schema,
            "documents": [
                {
                    "page_content": document.page_content,
                    "metadata": document.metadata,
                }
                for document in documents
            ],
        }

        project_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            project_dir / "schema_index.json",
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                manifest,
                handle,
                indent=2,
                default=str,
            )

    def _read_index_manifest(
        self,
        project_dir: Path,
    ):
        manifest_file = project_dir / "schema_index.json"

        if not manifest_file.exists():
            return None

        with open(
            manifest_file,
            encoding="utf-8",
        ) as handle:
            return json.load(handle)

    def _build_or_refresh_index(
        self,
        state: AgentState,
    ):
        print("=" * 80)
        print("BUILDING / REFRESHING SCHEMA INDEX")

        connector = self._get_connector(state)

        print(
            "Connector type:",
            type(connector).__name__,
        )
        print(
            "Connection name:",
            state.connection_name,
        )

        schema = connector.get_schema()

        print(
            "Raw schema type:",
            type(schema).__name__,
        )
        print(
            "Raw schema:",
            schema,
        )

        if schema is None:
            print("ERROR: connector.get_schema() " "returned None")
            schema = {}

        if not isinstance(schema, dict):
            print("ERROR: connector.get_schema() " "did not return a dictionary")
            schema = {}

        print(
            "Schema object count:",
            len(schema),
        )

        project_dir = self._project_dir(
            state.project_id or state.connection_name or "default"
        )

        if project_dir.exists():
            shutil.rmtree(project_dir)

        documents = self._schema_to_documents(schema)

        print(
            "Generated schema documents:",
            len(documents),
        )

        self._write_index_manifest(
            project_dir,
            schema,
            documents,
        )

        # Critical: never call Chroma with [].
        if not documents:
            print("No schema documents generated. " "Skipping vector index build.")
            return schema, documents, project_dir

        if self._embeddings is not None:
            try:
                from langchain_chroma import Chroma

                print("Building Chroma vector index...")

                Chroma.from_documents(
                    documents=documents,
                    embedding=self._embeddings,
                    persist_directory=str(project_dir),
                    collection_name=(self._collection_name(state)),
                )

                print("Vector index built successfully.")

            except Exception as exc:
                print("Vector index build failed, " "continuing with keyword fallback:")
                print(
                    type(exc).__name__,
                    str(exc),
                )

        else:
            print("Embeddings unavailable. " "Using keyword fallback.")

        return schema, documents, project_dir

    def _keyword_score(
        self,
        query: str,
        content: str,
    ) -> int:
        query_tokens = {
            token
            for token in re.findall(
                r"[A-Za-z0-9_]+",
                (query or "").lower(),
            )
            if len(token) > 1
        }

        content_lower = content.lower()
        content_tokens = set(
            re.findall(
                r"[A-Za-z0-9_]+",
                content_lower,
            )
        )

        score = 0

        for token in query_tokens:
            if token in content_tokens:
                score += 3
            elif token in content_lower:
                score += 1

            # Small singular/plural tolerance.
            if token.endswith("s"):
                singular = token[:-1]
                if len(singular) > 1 and singular in content_lower:
                    score += 1

        return score

    def _retrieve_documents(
        self,
        state: AgentState,
        query: str,
        project_dir: Path,
        top_k: int = 5,
    ) -> list[Document]:
        manifest = self._read_index_manifest(project_dir)

        if manifest is None:
            return []

        documents = [
            Document(
                page_content=item.get(
                    "page_content",
                    "",
                ),
                metadata=item.get(
                    "metadata",
                    {},
                ),
            )
            for item in manifest.get(
                "documents",
                [],
            )
            if item.get(
                "page_content",
                "",
            ).strip()
        ]

        if not documents:
            return []

        if self._embeddings is not None:
            try:
                from langchain_chroma import Chroma

                vector_store = Chroma(
                    persist_directory=str(project_dir),
                    collection_name=(self._collection_name(state)),
                    embedding_function=(self._embeddings),
                )

                results = vector_store.similarity_search(
                    query or "table schema",
                    k=min(top_k, len(documents)),
                )

                if results:
                    return results

            except Exception as exc:
                print("Vector retrieval failed, " f"using keyword fallback: {exc}")

        scored_documents = [
            (
                self._keyword_score(
                    query,
                    document.page_content,
                ),
                document,
            )
            for document in documents
        ]

        scored_documents.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        positive_matches = [
            document for score, document in scored_documents if score > 0
        ]

        if positive_matches:
            return positive_matches[:top_k]

        # Do not return empty schema context when a
        # valid schema exists but keyword matching misses.
        print(
            "Keyword retrieval found no positive match. "
            "Using limited schema fallback."
        )

        return documents[:top_k]

    def _format_schema_context(
        self,
        documents: list[Document],
        source_schema: dict[str, Any],
    ) -> dict[str, Any]:
        retrieved_tables = []
        markdown_sections = []

        for document in documents:
            table_name = (
                document.metadata.get("table_name")
                or document.metadata.get("object_name")
                or "unknown_table"
            )

            retrieved_tables.append(
                {
                    "name": table_name,
                    "type": document.metadata.get(
                        "object_type",
                        "table",
                    ),
                    "content": document.page_content,
                }
            )

            markdown_sections.append(f"### {table_name}\n" f"{document.page_content}")

        if not markdown_sections:
            markdown_sections.append("No schema context could be retrieved.")

        return {
            "retrieved_tables": retrieved_tables,
            "schema_markdown": "\n\n".join(markdown_sections),
            "source_schema": source_schema,
        }

    def fetch_schema(
        self,
        state: AgentState,
    ):
        try:
            print("=" * 80)
            print("SCHEMA FETCH STARTED")

            if not state.project_id:
                print("Schema fetch skipped: " "missing project id.")

                return {
                    "retrieved_tables": [],
                    "schema_markdown": (
                        "Schema fetch skipped because " "project id is missing."
                    ),
                    "source_schema": {},
                }

            project_dir = self._project_dir(state.project_id)

            manifest_file = project_dir / "schema_index.json"

            if not manifest_file.exists():
                print("Schema index not found. " "Building new index.")

                (
                    schema,
                    documents,
                    project_dir,
                ) = self._build_or_refresh_index(state)

            else:
                print("Existing schema index found.")

                manifest = self._read_index_manifest(project_dir)

                if manifest is None:
                    print("Manifest could not be read. " "Rebuilding.")

                    (
                        schema,
                        documents,
                        project_dir,
                    ) = self._build_or_refresh_index(state)

                else:
                    schema = manifest.get(
                        "schema",
                        {},
                    )

                    documents = [
                        Document(
                            page_content=item.get(
                                "page_content",
                                "",
                            ),
                            metadata=item.get(
                                "metadata",
                                {},
                            ),
                        )
                        for item in manifest.get(
                            "documents",
                            [],
                        )
                        if item.get(
                            "page_content",
                            "",
                        ).strip()
                    ]

            print(
                "Source schema object count:",
                len(schema),
            )

            print(
                "Available schema documents:",
                len(documents),
            )

            if not schema:
                print(
                    "Cached/source schema is empty. "
                    "Refreshing once from live database."
                )

                (
                    schema,
                    documents,
                    project_dir,
                ) = self._build_or_refresh_index(state)

            if not schema:
                print("ERROR: Source schema is empty.")

                return {
                    "retrieved_tables": [],
                    "schema_markdown": (
                        "Database connection exists, "
                        "but no schema objects were discovered."
                    ),
                    "source_schema": {},
                }

            if not documents:
                print("ERROR: Schema exists but no " "documents were generated.")

                return {
                    "retrieved_tables": [],
                    "schema_markdown": (
                        "Schema was discovered, but "
                        "no retrievable schema documents "
                        "were generated."
                    ),
                    "source_schema": schema,
                }

            query = (state.user_input or "").strip()

            if not query:
                query = "table schema"

            print(
                "Schema retrieval query:",
                query,
            )

            retrieved_documents = self._retrieve_documents(
                state,
                query,
                project_dir,
            )

            print(
                "Retrieved schema documents:",
                len(retrieved_documents),
            )

            if not retrieved_documents:
                print("No relevant schema retrieved. " "Using limited schema fallback.")

                retrieved_documents = documents[:5]

            result = self._format_schema_context(
                retrieved_documents,
                schema,
            )

            print(
                "Final schema context:",
                result,
            )

            return result

        except Exception as exc:
            print(
                "Schema fetch failed:",
                type(exc).__name__,
                str(exc),
            )

            traceback.print_exc()

            return {
                "retrieved_tables": [],
                "schema_markdown": ("Schema retrieval failed: " f"{str(exc)}"),
                "source_schema": {},
            }
