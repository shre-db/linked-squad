__module_name__ = "langgraph_graph"

from langgraph.graph import StateGraph, END, Graph
from .state_schema import ProfileBotState
from .handlers import (
    analyze_node,
    rewrite_node,
    job_fit_node,
    guide_node,
    router_node,
    process_agent_output_node,
)
from backend.memory import get_memory_saver

def build_graph():
    graph = StateGraph(ProfileBotState)

    # Define nodes
    graph.add_node("Router", router_node)
    graph.add_node("AnalyzeProfile", analyze_node)
    graph.add_node("RewriteContent", rewrite_node)
    graph.add_node("EvaluateJobFit", job_fit_node)
    graph.add_node("CareerGuidance", guide_node)
    graph.add_node("ProcessAgentOutput", process_agent_output_node)

    # Set entry point
    graph.set_entry_point("Router")

    # Routing logic from Router
    def route_decision(state: ProfileBotState) -> str:
        return state.current_router_action

    graph.add_conditional_edges(
        "Router",
        route_decision,
        {
            "CALL_ANALYZE": "AnalyzeProfile",
            "CALL_REWRITE": "RewriteContent",
            "CALL_JOB_FIT": "EvaluateJobFit",
            "CALL_GUIDE": "CareerGuidance",
            "PROCESS_AGENT_OUTPUT": "ProcessAgentOutput",
            "RESPOND_DIRECTLY": END,
            "AWAIT_URL": END,
            "AWAIT_CONFIRMATION": END,
            "REQUEST_JOB_DESCRIPTION": END,
            "INVALID_INPUT": END,
            "INITIAL_WELCOME": END,
        }
    )

    # Decision logic after agent execution
    def agent_output_decision(state: ProfileBotState) -> str:
        if (
            state.needs_output_processing and
            state.pending_agent_output and
            state.last_agent_called and
            state.current_router_action == "PROCESS_AGENT_OUTPUT"
        ):
            return "PROCESS_AGENT_OUTPUT"
        else:
            return "END"

    # Shared conditional edges for all agent nodes
    for node in ["AnalyzeProfile", "RewriteContent", "EvaluateJobFit", "CareerGuidance"]:
        graph.add_conditional_edges(
            node,
            agent_output_decision,
            {
                "PROCESS_AGENT_OUTPUT": "ProcessAgentOutput",
                "END": END
            }
        )

    # Processed output always ends the graph
    graph.add_edge("ProcessAgentOutput", END)

    return graph

def get_graph_runner() -> Graph:
    raw_graph = build_graph()
    memory_instance = get_memory_saver()
    compiled_graph = raw_graph.compile(checkpointer=memory_instance)
    return compiled_graph
