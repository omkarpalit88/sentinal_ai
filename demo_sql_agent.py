"""
Demo script to test SQL Agent with Gemini API
Shows LLM's autonomous tool selection in action
"""
from datetime import datetime
from backend.agents.sql_agent import create_sql_agent
from backend.state import AnalysisState, File, FileType

# Test SQL files
DANGEROUS_SQL = """
DROP TABLE users;
TRUNCATE TABLE sessions;
DELETE FROM logs;
"""

SAFE_SQL = """
SELECT * FROM users WHERE id = 1;
INSERT INTO audit_log (action, timestamp) VALUES ('login', NOW());
"""

SUBTLE_SQL = """
UPDATE users SET active = 0;
DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE active = 0);
"""

def test_sql_agent(filename: str, content: str):
    """Test SQL Agent on a file"""
    print(f"\n{'='*80}")
    print(f"Testing: {filename}")
    print(f"{'='*80}")
    print(f"SQL Content:\n{content}")
    print(f"{'='*80}\n")
    
    # Create agent
    print("Creating SQL Agent with Gemini LLM...")
    agent = create_sql_agent()
    print(f"✅ Agent created: {agent.name}\n")
    
    # Create state
    state: AnalysisState = {
        "files": [
            File(
                filename=filename,
                content=content,
                file_type=FileType.SQL,
                size_bytes=len(content)
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
    
    # Run agent
    print("Running LangChain Agent (Gemini will autonomously select tools)...\n")
    try:
        result = agent.process(state)
        
        # Display agent decisions (LLM reasoning)
        print("\n" + "="*80)
        print("AGENT DECISION LOG (LLM Reasoning)")
        print("="*80)
        for i, decision in enumerate(result["agent_decisions"], 1):
            print(f"\n{i}. {decision.decision}")
            if decision.tool_called:
                print(f"   Tool Called: {decision.tool_called}")
            print(f"   Justification: {decision.justification}")
        
        # Display findings
        print("\n" + "="*80)
        print("FINDINGS")
        print("="*80)
        if result["findings"]:
            for i, finding in enumerate(result["findings"], 1):
                print(f"\n{i}. [{finding.severity.value}] {finding.category}")
                print(f"   {finding.description}")
                print(f"   Detected by: {finding.detected_by}")
        else:
            print("No findings detected")
        
        print("\n" + "="*80 + "\n")
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SQL AGENT DEMO - Testing LangChain Agent with Gemini API")
    print("="*80)
    print("\nThis demo shows how the LangChain Agent autonomously decides which tools to call")
    print("based on the SQL content. Watch for the LLM's reasoning in the decision log!\n")
    
    # Test 1: Dangerous SQL
    print("\n🔴 TEST 1: DANGEROUS SQL (Multiple violations)")
    test_sql_agent("dangerous.sql", DANGEROUS_SQL)
    
    # Test 2: Safe SQL
    print("\n🟢 TEST 2: SAFE SQL (Clean queries)")
    test_sql_agent("safe.sql", SAFE_SQL)
    
    # Test 3: Subtle issues
    print("\n🟡 TEST 3: SUBTLE SQL (Unfiltered operations)")
    test_sql_agent("subtle.sql", SUBTLE_SQL)
    
    print("\nDemo complete! 🎉\n")
