from __future__ import annotations

import json
import re

from State.DBState import AgentState
from agent.services.execution_service import ExecutionService


class InvestigationNode:
    """
    Executes exactly one critic-generated read-only investigation query.
    The result becomes evidence for the next query-generation attempt.
    """

    SAFE_SQL_PREFIXES = (
        "SELECT",
        "SHOW",
        "DESCRIBE",
        "DESC",
        "EXPLAIN",
        "WITH",
    )

    def __init__(self):
        self.execution_service = ExecutionService()

    @staticmethod
    def _is_safe_read(
        query: str,
    ) -> bool:

        query = (query or "").strip().rstrip(";")

        if not query:
            return False

        upper = query.upper()

        ########################################################
        # SQL READ-ONLY
        ########################################################

        sql_prefixes = (
            "SELECT",
            "SHOW",
            "DESCRIBE",
            "DESC",
            "EXPLAIN",
            "WITH",
        )

        if upper.startswith(sql_prefixes):

            forbidden = re.search(
                r"\b("
                r"INSERT|UPDATE|DELETE|DROP|ALTER|"
                r"TRUNCATE|CREATE|REPLACE|MERGE|"
                r"GRANT|REVOKE"
                r")\b",
                upper,
            )

            return forbidden is None

        ########################################################
        # MONGODB READ-ONLY
        ########################################################

        mongo_read_pattern = re.fullmatch(
            r"""
            db\.
            [A-Za-z_][A-Za-z0-9_]*
            \.
            (
                find
                |
                findOne
                |
                countDocuments
                |
                distinct
            )
            \(
                .*
            \)
            """,
            query,
            re.VERBOSE | re.DOTALL,
        )

        if mongo_read_pattern:
            return True

        return False

    def __call__(self, state: AgentState):
        print("=" * 80)
        print("ENTERED INVESTIGATION NODE")

        query = (state.investigation_query or "").strip()

        if not self._is_safe_read(query):
            return {
                "investigation_result": None,
                "investigation_evidence": (
                    "Investigation was skipped because the proposed "
                    "query was not safely read-only."
                ),
                "refinement_count": state.refinement_count + 1,
                "current_node": "investigation",
            }

        investigation_state = state.model_copy(deep=False)
        investigation_state.generated_sql_query = query
        investigation_state.identified_intent = "SELECT"
        investigation_state.query_type = "read"
        investigation_state.requires_approval = False
        investigation_state.approval = True

        result = self.execution_service.execute(investigation_state)

        evidence = json.dumps(
            result,
            default=str,
            ensure_ascii=False,
        )

        # Keep prompt size bounded.
        evidence = evidence[:12000]

        print("Investigation query:", query)
        print("Investigation result:", result)

        return {
            "investigation_result": result,
            "investigation_evidence": evidence,
            "refinement_count": state.refinement_count + 1,
            "current_node": "investigation",
        }
