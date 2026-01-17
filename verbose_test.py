"""Minimal test to see full agent output"""
import sys
from datetime import datetime
from backend.agents.sql_agent import create_sql_agent
from backend.state import File, FileType

# Create agent
agent = create_sql_agent()
# Force verbose
agent.agent_executor.verbose = True

# Simple state
state = {
    "files": [File(filename="test.sql", content="DROP TABLE users;", file_type=FileType.SQL, size_bytes=20)],
    "findings": [], "cross_file_deps": [], "agent_decisions": [],
    "overall_risk": None, "recommend_approval": None, "defense_memo": None,
    "analysis_started_at": datetime.now(), "analysis_completed_at": None,
    "total_cost_usd": 0.0, "next_agent": None
}

result = agent.process(state)
print(f"\n\nFINAL: {len(result['findings'])} findings, {len(result['agent_decisions'])} decisions")
