"""Quick test of Gemini tool calling with parameter remapping"""
from datetime import datetime
from backend.agents.sql_agent import create_sql_agent
from backend.state import File, FileType, AnalysisState

# Create agent
agent = create_sql_agent()

# Create state with dangerous SQL
state: AnalysisState = {
    "files": [
        File(
            filename="test_drop.sql",
            content="DROP TABLE users;\nTRUNCATE TABLE sessions;",
            file_type=FileType.SQL,
            size_bytes=50
        )
    ],
    "findings": [],
    "cross_file_deps": [],
    "agent_decisions": [],
    "overall_risk": None,
    "recommend_approval": None,
   "defense_memo": None,
    "analysis_started_at": datetime.now(),
    "analysis_completed_at": None,
    "total_cost_usd": 0.0,
    "next_agent": None
}

print("\n" + "="*80)
print("TESTING GEMINI TOOL CALLING WITH PARAMETER REMAPPING")
print("="*80 + "\n")

result = agent.process(state)

print("\n" + "="*80)
print("RESULTS")
print("="*80)
print(f"Findings: {len(result['findings'])}")
print(f"Decisions: {len(result['agent_decisions'])}")

for i, finding in enumerate(result["findings"], 1):
    print(f"\n{i}. [{finding.severity.value}] {finding.category}")
    print(f"   {finding.description}")

print("\n" + "="*80 + "\n")
