from langchain_core.messages import AIMessage

from State.DBState import AgentState


class NonDatabaseQueryNode:

    def __call__(self, state: AgentState):

        return {

            "messages": [

                AIMessage(
                    content=(
                        "I can only help with database-related queries.\n\n"
                        "Please ask a question related to your connected database."
                    )
                )

            ],

            "current_node": "non_database_query"

        }