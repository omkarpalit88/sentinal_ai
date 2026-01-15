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
    workflow = StateGraph(AnalysisState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator.process)
    
    # Phase 1: Placeholder nodes (will implement in later sub-phases)
    workflow.add_node("sql_agent", lambda state: _placeholder_sql_agent(state))
    workflow.add_node("synthesis_agent", lambda state: _placeholder_synthesis_agent(state))
    
    # Define edges
    workflow.set_entry_point("orchestrator")
    
    # Conditional routing from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "sql_agent": "sql_agent",
            "synthesis_agent": "synthesis_agent"
        }
    )
    
    # SQL Agent -> Synthesis Agent
    workflow.add_edge("sql_agent", "synthesis_agent")
    
    # Synthesis Agent -> END
    workflow.add_edge("synthesis_agent", END)
    
    # Compile the graph
    return workflow.compile()


def _route_from_orchestrator(state: AnalysisState) -> Literal["sql_agent", "synthesis_agent"]:
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
    else:
        return "synthesis_agent"


# Placeholder implementations (Phase 1.1)
def _placeholder_sql_agent(state: AnalysisState) -> AnalysisState:
    """Placeholder - will implement in Sub-Phase 1.3"""
    from backend.state import AgentDecision, add_decision
    
    decision = AgentDecision(
        agent_name="sql_agent",
        decision="Placeholder - not yet implemented",
        justification="SQL Agent will be implemented in Sub-Phase 1.3"
    )
    return add_decision(state, decision)


def _placeholder_synthesis_agent(state: AnalysisState) -> AnalysisState:
    """Placeholder - will implement in Sub-Phase 1.5"""
    from backend.state import AgentDecision, add_decision
    from datetime import datetime
    
    state["analysis_completed_at"] = datetime.now()
    state["defense_memo"] = "# Defense Memo\n\n*Placeholder - Agent not yet implemented*"
    state["overall_risk"] = "INFO"
    state["recommend_approval"] = True
    
    decision = AgentDecision(
        agent_name="synthesis_agent",
        decision="Placeholder - not yet implemented",
        justification="Synthesis Agent will be implemented in Sub-Phase 1.5"
    )
    return add_decision(state, decision)
