import copy
import re
from typing import Any

from State.DBState import AgentState
from agent.services.execution_service import ExecutionService


class DemoApplicationNode:
    READ_INTENTS = {"SELECT", "SHOW"}

    def __init__(self):
        self.execution_service = ExecutionService()

    def _tables(self, state: AgentState):
        tables = list(getattr(state, "affected_tables", None) or [])
        if tables:
            return tables
        sql = state.generated_sql_query or ""
        for pattern in (
            r"\bUPDATE\s+([A-Za-z_][\w$]*)",
            r"\bINSERT\s+INTO\s+([A-Za-z_][\w$]*)",
            r"\bDELETE\s+FROM\s+([A-Za-z_][\w$]*)",
            r"\b(?:ALTER|TRUNCATE)\s+TABLE\s+([A-Za-z_][\w$]*)",
        ):
            m = re.search(pattern, sql, re.I)
            if m:
                return [m.group(1)]
        return []

    def _rows(self, result: Any):
        if isinstance(result, list):
            return [dict(x) if isinstance(x, dict) else {"value": x} for x in result]
        if isinstance(result, dict):
            for key in ("rows", "data", "records", "result"):
                if isinstance(result.get(key), list):
                    return [
                        dict(x) if isinstance(x, dict) else {"value": x}
                        for x in result[key]
                    ]
        return []

    def _snapshot(self, state, table):
        read_state = state.model_copy(deep=False)
        read_state.generated_sql_query = f"SELECT * FROM `{table}` LIMIT 100"
        read_state.identified_intent = "SELECT"
        read_state.query_type = "read"
        read_state.requires_approval = False
        read_state.approval = True
        try:
            return self._rows(self.execution_service.execute(read_state))
        except Exception:
            return []

    def _literal(self, value):
        value = value.strip().rstrip(";")
        if value.upper() == "NULL":
            return None
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            return value[1:-1].replace("''", "'")
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value

    def _matches(self, row, where):
        if not where:
            return True
        for part in re.split(r"\s+AND\s+", where, flags=re.I):
            m = re.match(r"\s*([A-Za-z_][\w$]*)\s*=\s*(.+?)\s*$", part)
            if not m:
                return False
            expected = self._literal(m.group(2))
            if row.get(m.group(1)) != expected and str(row.get(m.group(1))) != str(
                expected
            ):
                return False
        return True

    def _simulate(self, sql, before):
        after = copy.deepcopy(before)

        m = re.search(r"\bUPDATE\s+([A-Za-z_][\w$]*)", sql, re.I | re.S)
        if m:
            assignments = {}
            for part in re.split(r"\s*,\s*", m.group(1)):
                a = re.match(r"\s*([A-Za-z_][\w$]*)\s*=\s*(.+?)\s*$", part, re.S)
                if a:
                    assignments[a.group(1)] = self._literal(a.group(2))
            for row in after:
                if self._matches(row, m.group(2)):
                    row.update(assignments)
            return after

        m = re.search(r"\bDELETE\s+FROM\s+([A-Za-z_][\w$]*)", sql, re.I | re.S)
        if m:
            return [row for row in after if not self._matches(row, m.group(1))]

        m = re.search(r"\bINSERT\s+INTO\s+([A-Za-z_][\w$]*)", sql, re.I | re.S)
        if m:
            cols = [x.strip().strip('`\\"[]') for x in m.group(1).split(",")]
            vals = [self._literal(x) for x in re.split(r"\s*,\s*", m.group(2))]
            after.append(dict(zip(cols, vals)))
            return after

        if re.search(r"\bTRUNCATE\s+TABLE\b", sql, re.I):
            return []
        return after

    def __call__(self, state: AgentState):
        if (state.identified_intent or "").upper() in self.READ_INTENTS:
            return {"current_node": "demo_application", "demo_result": None}

        tables = self._tables(state)
        table = tables[0] if tables else "unknown_table"
        before = self._snapshot(state, table) if tables else []
        after = self._simulate(state.generated_sql_query or "", before)

        return {
            "workflow_status": "pending_approval",
            "current_node": "demo_application",
            "approval": False,
            "demo_result": {
                "table_name": table,
                "affected_tables": tables,
                "before": before,
                "after": after,
                "caution": "Read-only preview. The write query has not been executed on the actual database.",
                "sql": state.generated_sql_query,
                "risk_level": state.query_risk_level,
                "confidence": state.query_confidence,
            },
        }
