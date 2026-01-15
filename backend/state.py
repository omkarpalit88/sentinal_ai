"""
LangGraph State Schema for SentinAL
Defines the shared state structure passed between all agents
"""
from typing import TypedDict, List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """Supported file types"""
    SQL = "sql"
    TERRAFORM = "terraform"
    YAML = "yaml"
    UNKNOWN = "unknown"


class ConstraintLevel(str, Enum):
    """Risk severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class File(BaseModel):
    """Represents an uploaded deployment file"""
    filename: str
    content: str
    file_type: FileType
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Finding(BaseModel):
    """A single risk/issue found in a file"""
    file_id: str  # filename
    line_number: Optional[int] = None
    severity: ConstraintLevel
    category: str  # e.g., "DROP_TABLE", "MISSING_ROLLBACK", "HARDCODED_SECRET"
    description: str
    detected_by: str  # e.g., "sql_agent", "rules_tool", "semantic_tool"
    reasoning: Optional[str] = None  # Why this is risky (for LLM-detected findings)
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    
    class Config:
        json_encoders = {
            ConstraintLevel: lambda v: v.value
        }


class Dependency(BaseModel):
    """Cross-file dependency detected"""
    source_file: str
    target_file: str
    dependency_type: str  # e.g., "TABLE_REFERENCE", "RESOURCE_DEPENDENCY"
    description: str
    risk_level: ConstraintLevel
    detected_by: str = "cross_file_agent"


class AgentDecision(BaseModel):
    """Logs an agent's decision-making process"""
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    decision: str  # e.g., "Called rules_tool because file is SQL"
    tool_called: Optional[str] = None
    justification: str  # e.g., "Deterministic scan required for all SQL files"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalysisState(TypedDict):
    """
    Shared state for the LangGraph workflow.
    All agents read/write to this state.
    """
    # Input data
    files: List[File]
    
    # Analysis results
    findings: List[Finding]
    cross_file_deps: List[Dependency]
    
    # Agent decision trail (for transparency/debugging)
    agent_decisions: List[AgentDecision]
    
    # Overall assessment
    overall_risk: Optional[ConstraintLevel]
    recommend_approval: Optional[bool]
    defense_memo: Optional[str]  # Final markdown output
    
    # Metadata
    analysis_started_at: Optional[datetime]
    analysis_completed_at: Optional[datetime]
    total_cost_usd: float  # Track LLM API costs
    
    # Internal routing
    next_agent: Optional[str]  # Used by orchestrator for routing


# Helper functions for state updates
def add_finding(state: AnalysisState, finding: Finding) -> AnalysisState:
    """Immutable-style add finding to state"""
    return {
        **state,
        "findings": state.get("findings", []) + [finding]
    }


def add_decision(state: AnalysisState, decision: AgentDecision) -> AnalysisState:
    """Immutable-style add agent decision to state"""
    return {
        **state,
        "agent_decisions": state.get("agent_decisions", []) + [decision]
    }


def add_dependency(state: AnalysisState, dependency: Dependency) -> AnalysisState:
    """Immutable-style add cross-file dependency to state"""
    return {
        **state,
        "cross_file_deps": state.get("cross_file_deps", []) + [dependency]
    }
