from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from State.DBState import AgentState


class ResponseService:
    """
    Builds responses for both SQL connector results and raw MongoDB list results.
    """

    @staticmethod
    def _rows(result: Any) -> list[dict]:
        if isinstance(result, list):
            return [
                dict(item) if isinstance(item, dict) else {"value": item}
                for item in result
            ]

        if isinstance(result, dict):
            for key in ("rows", "data", "records", "result"):
                value = result.get(key)
                if isinstance(value, list):
                    return [
                        dict(item) if isinstance(item, dict) else {"value": item}
                        for item in value
                    ]

        return []

    @staticmethod
    def _markdown_table(rows: list[dict], max_rows: int = 50) -> str:
        if not rows:
            return "No records found."

        columns = []
        seen = set()

        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    columns.append(str(key))

        def clean(value):
            text = str(value)
            return text.replace("|", r"\|").replace("\n", " ")

        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join(["---"] * len(columns)) + " |",
        ]

        for row in rows[:max_rows]:
            lines.append(
                "| "
                + " | ".join(clean(row.get(column, "")) for column in columns)
                + " |"
            )

        if len(rows) > max_rows:
            lines.append(f"\nShowing first {max_rows} of {len(rows)} returned records.")

        return "\n".join(lines)

    def build_response(self, state: AgentState) -> AIMessage:
        if state.workflow_status == "cancelled":
            return AIMessage(content="Operation cancelled.")

        result = state.execution_result

        if result is None:
            return AIMessage(content="No result was returned.")

        # MongoConnector returns list[dict] for read operations.
        if isinstance(result, list):
            return AIMessage(content=self._markdown_table(self._rows(result)))

        if not isinstance(result, dict):
            return AIMessage(content=str(result))

        # SQL connectors generally return a structured result dictionary.
        if result.get("success") is False:
            error = result.get("error") or result.get("message")
            return AIMessage(
                content=(
                    f"Query execution failed: {error}"
                    if error
                    else "Query execution failed."
                )
            )

        rows = self._rows(result)
        query_type = str(
            result.get("query_type")
            or state.query_type
            or state.identified_intent
            or ""
        ).upper()

        if rows or query_type in {
            "SELECT",
            "SHOW",
            "READ",
            "ANALYTICS",
            "AGGREGATION",
            "REPORT",
        }:
            return AIMessage(content=self._markdown_table(rows))

        rows_affected = result.get("rows_affected")

        if rows_affected is not None:
            return AIMessage(
                content=(
                    "Query executed successfully.\n\n" f"Rows affected: {rows_affected}"
                )
            )

        return AIMessage(
            content=result.get("message") or "Query executed successfully."
        )
