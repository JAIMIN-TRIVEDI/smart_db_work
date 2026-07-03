from langchain_core.messages import AIMessage

from State.DBState import AgentState


class ResponseService:

    def build_response(self, state: AgentState) -> AIMessage:

        if state.workflow_status == "cancelled":

            return AIMessage(
                content="Operation cancelled."
            )

        result = state.execution_result

        if result is None:

            return AIMessage(
                content="No result was returned."
            )

        if not result.get("success", False):

            return AIMessage(
                content="Query execution failed."
            )

        if result.get("query_type") == "SELECT":

            rows = result.get("rows") or []

            if not rows:

                return AIMessage(
                    content="No records found."
                )

            markdown = "| " + " | ".join(rows[0].keys()) + " |\n"
            markdown += "|" + "|".join(["---"] * len(rows[0])) + "|\n"

            for row in rows:

                markdown += (
                    "| "
                    + " | ".join(str(v) for v in row.values())
                    + " |\n"
                )

            return AIMessage(content=markdown)

        return AIMessage(
            content=(
                f"✅ Query executed successfully.\n\n"
                f"Rows affected : {result['rows_affected']}"
            )
        )