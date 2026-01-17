"""
LangGraph Workflow Definition
Defines the state graph with nodes and edges
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from backend.state import AnalysisState
from backend.orchestrator import orchestrator


def create_workflow() -> StateGraph:
    """
    Creates the LangGraph state machine
    
    Workflow (Phase 1):
    1. START -> Orchestrator (file type detection, routing)
    2. Orchestrator -> SQL Agent (if SQL files present)
    3. SQL Agent -> Synthesis Agent (generate Defense Memo)
    4. Synthesis Agent -> END
    
    Returns:
        Compiled StateGraph ready for invocation
    """
    from backend.agents.sql_agent import create_sql_agent
    from backend.agents.terraform_agent import create_terraform_agent
    from backend.agents.yaml_agent import create_yaml_agent
    from backend.agents.synthesis_agent import synthesis_agent
    
    # Create agent instances
    sql_agent = create_sql_agent()
    terraform_agent = create_terraform_agent()
    yaml_agent = create_yaml_agent()
    
    workflow = StateGraph(AnalysisState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator.process)
    workflow.add_node("sql_agent", sql_agent.process)
    workflow.add_node("terraform_agent", terraform_agent.process)
    workflow.add_node("yaml_agent", yaml_agent.process)
    workflow.add_node("synthesis_agent", synthesis_agent.process)
    
    # Define edges
    workflow.set_entry_point("orchestrator")
    
    # Conditional routing from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "sql_agent": "sql_agent",
            "terraform_agent": "terraform_agent",
            "yaml_agent": "yaml_agent",
            "synthesis_agent": "synthesis_agent"
        }
    )
    
    # Specialist agents -> Synthesis Agent
    workflow.add_edge("sql_agent", "synthesis_agent")
    workflow.add_edge("terraform_agent", "synthesis_agent")
    workflow.add_edge("yaml_agent", "synthesis_agent")
    
    # Synthesis Agent -> END
    workflow.add_edge("synthesis_agent", END)
    
    # Compile the graph
    return workflow.compile()


def _route_from_orchestrator(state: AnalysisState) -> Literal["sql_agent", "terraform_agent", "yaml_agent", "synthesis_agent"]:
    """
    Conditional routing logic from orchestrator
    
    Args:
        state: Current analysis state
        
    Returns:
        Next node name
    """
    next_agent = state.get("next_agent", "synthesis_agent")
    
    if next_agent == "sql_agent":
        return "sql_agent"
    elif next_agent == "terraform_agent":
        return "terraform_agent"
    elif next_agent == "yaml_agent":
        return "yaml_agent"
    else:
        return "synthesis_agent"
