from __future__ import annotations

from State.DBState import AgentState
from agent.services.query_critic_service import QueryCriticService


class QueryCriticNode:

    def __init__(self):
        self.service = QueryCriticService()

    def __call__(self, state: AgentState):
        print("=" * 80)
        print("ENTERED QUERY CRITIC NODE")

        review = self.service.review(state)

        decision = review.decision.upper()

        # Prevent infinite graph loops.
        if (
            decision in {"REVISE", "INVESTIGATE"}
            and state.refinement_count >= state.max_refinements
        ):
            decision = "ACCEPT"

        print("Critic decision:", decision)
        print("Critic reasoning:", review.reasoning)
        print(
            "Investigation query:",
            review.investigation_query,
        )

        return {
            "critic_status": decision,
            "critic_reasoning": review.reasoning,
            "investigation_query": (
                review.investigation_query if decision == "INVESTIGATE" else None
            ),
            "current_node": "query_critic",
        }
