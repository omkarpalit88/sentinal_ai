"""
Unit tests for LangChain-based SQL Agent (Path C refactor)
Tests LLM-driven tool selection and agentic behavior
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from backend.agents.sql_agent import SQLAgent
from backend.state import (
    AnalysisState, File, FileType, ConstraintLevel
)


class TestLangChainSQLAgent:
    """Test SQL Agent with LangChain framework"""
    
    def test_agent_initialization(self):
        """Test that agent initializes with LangChain components"""
        agent = SQLAgent()
        assert agent.name == "sql_agent"
        assert agent.llm is not None
        assert agent.agent is not None
        assert agent.agent_executor is not None
    
    @patch('backend.agents.sql_agent.sql_agent.agent_executor')
    def test_process_no_sql_files(self, mock_executor):
        """Test agent handles state with no SQL files"""
        agent = SQLAgent()
        state: AnalysisState = {
            "files": [],
            "findings": [],
            "cross_file_deps": [],
            "agent_decisions": [],
            "overall_risk": None,
            "recommend_approval": None,
            "defense_memo": None,
            "analysis_started_at": None,
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        result = agent.process(state)
        
        # Should log decision about no SQL files
        assert len(result["agent_decisions"]) == 1
        assert "No SQL files" in result["agent_decisions"][0].decision
        
        # Should not call LLM
        mock_executor.invoke.assert_not_called()
    
    @patch('backend.agents.sql_agent.sql_agent.agent_executor.invoke')
    def test_llm_agent_invoked_with_file(self, mock_invoke):
        """Test that LLM agent is invoked with SQL file content"""
        # Mock agent result
        mock_invoke.return_value = {
            "output": "Analysis complete",
            "intermediate_steps": []
        }
        
        agent = SQLAgent()
        state: AnalysisState = {
            "files": [
                File(
                    filename="test.sql",
                    content="SELECT * FROM users;",
                    file_type=FileType.SQL,
                    size_bytes=25
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
        
        result = agent.process(state)
        
        # Should have called LLM
        mock_invoke.assert_called_once()
        
        # Check that invoke was called with file content
        call_args = mock_invoke.call_args[0][0]
        assert "test.sql" in call_args["input"]
        assert "SELECT * FROM users" in call_args["input"]
        
        # Should have agent decisions logged
        assert len(result["agent_decisions"]) >= 2  # Start + completion
    
    @patch('backend.agents.sql_agent.sql_agent.agent_executor.invoke')
    def test_llm_tool_selection_logged(self, mock_invoke):
        """Test that LLM's tool selection decisions are logged"""
        # Mock agent with intermediate steps (tool calls)
        mock_action = MagicMock()
        mock_action.tool = "rules_tool"
        mock_action.log = "I should check for dangerous patterns first"
        
        mock_invoke.return_value = {
            "output": "Found HIGH severity DROP TABLE",
            "intermediate_steps": [
                (mock_action, "Found 1 issue: [HIGH] DROP_TABLE")
            ]
        }
        
        agent = SQLAgent()
        state: AnalysisState = {
            "files": [
                File(
                    filename="drop.sql",
                    content="DROP TABLE users;",
                    file_type=FileType.SQL,
                    size_bytes=20
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
        
        result = agent.process(state)
        
        # Should have logged LLM's tool choice
        tool_decisions = [d for d in result["agent_decisions"] if d.tool_called == "rules_tool"]
        assert len(tool_decisions) >= 1
        assert "LLM chose" in tool_decisions[0].decision or "LLM reasoning" in tool_decisions[0].justification
    
    @patch('backend.agents.sql_agent.sql_agent.agent_executor.invoke')
    def test_findings_extracted_from_llm_output(self, mock_invoke):
        """Test that findings are extracted from LLM tool outputs"""
        mock_action = MagicMock()
        mock_action.tool = "rules_tool"
        mock_action.log = "Checking patterns"
        
        mock_invoke.return_value = {
            "output": "Analysis complete",
            "intermediate_steps": [
                (mock_action, "Found 1 issue: [CRITICAL] DROP DATABASE detected at line 5")
            ]
        }
        
        agent = SQLAgent()
        state: AnalysisState = {
            "files": [
                File(
                    filename="dangerous.sql",
                    content="DROP DATABASE production;",
                    file_type=FileType.SQL,
                    size_bytes=30
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
        
        result = agent.process(state)
        
        # Should have extracted findings
        assert len(result["findings"]) >= 1
        
        # Should have CRITICAL severity
        severities = [f.severity for f in result["findings"]]
        assert ConstraintLevel.CRITICAL in severities


class TestLangChainTools:
    """Test LangChain tool wrappers"""
    
    def test_rules_tool_import(self):
        """Test that rules_tool can be imported"""
        from backend.tools.langchain_tools import rules_tool
        assert rules_tool is not None
        assert rules_tool.name == "rules_tool"
    
    def test_parser_tool_import(self):
        """Test that parser_tool can be imported"""
        from backend.tools.langchain_tools import parser_tool
        assert parser_tool is not None
        assert parser_tool.name == "parser_tool"
    
    def test_tools_have_schemas(self):
        """Test that tools have proper input schemas"""
        from backend.tools.langchain_tools import rules_tool, parser_tool
        
        # Rules tool should have schema
        assert rules_tool.args_schema is not None
        assert hasattr(rules_tool.args_schema, '__fields__')
        
        # Parser tool should have schema
        assert parser_tool.args_schema is not None
        assert hasattr(parser_tool.args_schema, '__fields__')
    
    def test_rules_tool_function(self):
        """Test rules_tool wrapper function"""
        from backend.tools.langchain_tools import rules_tool_func
        
        result = rules_tool_func("test.sql", "SELECT * FROM users;")
        assert isinstance(result, str)
        assert "test.sql" in result
    
    def test_parser_tool_function(self):
        """Test parser_tool wrapper function"""
        from backend.tools.langchain_tools import parser_tool_func
        
        result = parser_tool_func("test.sql", "CREATE TABLE users (id INT);")
        assert isinstance(result, str)
        assert "test.sql" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
