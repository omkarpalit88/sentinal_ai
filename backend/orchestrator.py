"""
Orchestrator Agent - Routes files to specialist agents
"""
from datetime import datetime
from typing import List
from backend.state import (
    AnalysisState, File, FileType, AgentDecision,
    add_decision
)
from backend.utils.helpers import detect_file_type
from backend.config import settings


class OrchestratorAgent:
    """
    Orchestrator responsibilities:
    1. Detect file types
    2. Route to appropriate specialist agents
    3. Coordinate multi-file analysis
    4. Initialize shared state
    """
    
    def __init__(self):
        self.name = "orchestrator"
    
    def process(self, state: AnalysisState) -> AnalysisState:
        """
        Main orchestrator logic
        
        Args:
            state: Current analysis state
            
        Returns:
            Updated state with routing decisions
        """
        files = state.get("files", [])
        
        if not files:
            return state
        
        # Initialize state metadata if not present
        if not state.get("analysis_started_at"):
            state["analysis_started_at"] = datetime.now()
            state["total_cost_usd"] = 0.0
            state["findings"] = []
            state["cross_file_deps"] = []
            state["agent_decisions"] = []
        
        # Detect file types for all files
        for file in files:
            if file.file_type == FileType.UNKNOWN:
                detected_type = detect_file_type(file.filename, file.content)
                file.file_type = detected_type
                
                # Log decision
                decision = AgentDecision(
                    agent_name=self.name,
                    decision=f"Detected file type: {detected_type.value}",
                    tool_called="detect_file_type",
                    justification=f"File '{file.filename}' identified as {detected_type.value}"
                )
                state = add_decision(state, decision)
        
        # Determine next agent to route to
        # Phase 1: Only SQL agent available
        next_agent = self._route_to_next_agent(state)
        state["next_agent"] = next_agent
        
        if settings.log_agent_decisions:
            decision = AgentDecision(
                agent_name=self.name,
                decision=f"Routing to: {next_agent}",
                justification=self._get_routing_justification(state)
            )
            state = add_decision(state, decision)
        
        return state
    
    def _route_to_next_agent(self, state: AnalysisState) -> str:
        """
        Determine which specialist agent should process next
        
        Phase 1: Only SQL agent
        Phase 2+: SQL, Terraform, YAML agents
        Phase 4+: Cross-file agent
        
        Args:
            state: Current state
            
        Returns:
            Agent name to route to
        """
        files = state.get("files", [])
        
        # Phase 1: Simple routing to SQL agent
        for file in files:
            if file.file_type == FileType.SQL:
                return "sql_agent"
        
        # No supported file types
        return "synthesis_agent"
    
    def _get_routing_justification(self, state: AnalysisState) -> str:
        """Generate human-readable routing justification"""
        files = state.get("files", [])
        file_types = [f.file_type.value for f in files]
        
        return (
            f"Analyzed {len(files)} file(s) with types: {', '.join(file_types)}. "
            f"Routing to appropriate specialist agent."
        )


# Create singleton instance
orchestrator = OrchestratorAgent()
