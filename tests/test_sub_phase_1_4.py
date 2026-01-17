"""
Unit tests for Sub-Phase 1.4: LLM Semantic Tool and Cost Tracking
Tests semantic analysis tool, cost tracking, and LangChain integration
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.tools.deterministic.semantic_tool import SemanticTool
from backend.utils.gemini_client import CostTrackingCallback, gemini_client
from backend.state import Finding, ConstraintLevel


class TestSemanticTool:
    """Tests for LLM-powered semantic analysis tool"""
    
    def test_semantic_tool_initialization(self):
        """Test semantic tool initializes correctly"""
        tool = SemanticTool()
        assert tool.name == "semantic_tool"
        assert tool.llm is not None
    
    def test_semantic_tool_with_mock_llm(self):
        """Test semantic tool with mocked LLM response"""
        # Mock LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = """```json
[
  {
    "severity": "HIGH",
    "category": "Business Logic Violation",
    "description": "Deleting user data without archiving",
    "reasoning": "This DELETE operation removes data permanently without backup",
    "recommendation": "Add archiving step before deletion"
  }
]
```"""
        mock_llm.invoke.return_value = mock_response
        
        # Create tool with mock
        tool = SemanticTool(llm=mock_llm)
        
        # Analyze SQL
        findings, cost = tool.analyze(
            filename="test.sql",
            content="DELETE FROM users WHERE inactive = true;",
            context={"tables_referenced": ["users"]}
        )
        
        # Verify
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.HIGH
        assert findings[0].category == "Business Logic Violation"
        assert "archiving" in findings[0].description.lower()
        assert findings[0].detected_by == "semantic_tool_llm"
        # Cost should be 0 since we mocked the LLM
        assert cost == 0.0
    
    def test_semantic_tool_no_findings(self):
        """Test semantic tool with clean SQL"""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "```json\n[]\n```"
        mock_llm.invoke.return_value = mock_response
        
        tool = SemanticTool(llm=mock_llm)
        findings, cost = tool.analyze(
            filename="safe.sql",
            content="SELECT * FROM users WHERE id = 1;",
            context=None
        )
        
        assert len(findings) == 0
        assert cost == 0.0
    
    def test_semantic_tool_multiple_findings(self):
        """Test semantic tool detecting multiple risks"""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = """```json
[
  {
    "severity": "CRITICAL",
    "category": "Data Integrity Risk",
    "description": "Cascade delete without safeguards",
    "reasoning": "Foreign key cascade can delete related data unexpectedly",
    "recommendation": "Add explicit checks"
  },
  {
    "severity": "MEDIUM",
    "category": "Performance Anti-Pattern",
    "description": "Missing index on new column",
    "reasoning": "Queries will be slow without index",
    "recommendation": "Add index"
  }
]
```"""
        mock_llm.invoke.return_value = mock_response
        
        tool = SemanticTool(llm=mock_llm)
        findings, cost = tool.analyze("test.sql", "ALTER TABLE...", None)
        
        assert len(findings) == 2
        assert findings[0].severity == ConstraintLevel.CRITICAL
        assert findings[1].severity == ConstraintLevel.MEDIUM
    
    def test_semantic_tool_malformed_json(self):
        """Test semantic tool handles malformed LLM response"""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "This is not JSON"
        mock_llm.invoke.return_value = mock_response
        
        tool = SemanticTool(llm=mock_llm)
        findings, cost = tool.analyze("test.sql", "SELECT 1;", None)
        
        # Should return empty findings without crashing
        assert len(findings) == 0
    
    def test_semantic_tool_llm_error(self):
        """Test semantic tool handles LLM errors gracefully"""
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API Error")
        
        tool = SemanticTool(llm=mock_llm)
        findings, cost = tool.analyze("test.sql", "SELECT 1;", None)
        
        # Should return empty findings without raising
        assert len(findings) == 0
        assert cost == 0.0
    
    def test_format_context(self):
        """Test context formatting for LLM"""
        tool = SemanticTool(llm=Mock())
        
        context = {
            "tables_created": ["users", "sessions"],
            "tables_dropped": ["old_table"],
            "has_ddl": True,
            "has_dml": True
        }
        
        formatted = tool._format_context(context)
        
        assert "users" in formatted
        assert "sessions" in formatted
        assert "old_table" in formatted
        assert "DDL" in formatted
        assert "DML" in formatted


class TestCostTracking:
    """Tests for cost tracking functionality"""
    
    def test_cost_callback_initialization(self):
        """Test cost callback initializes with zeros"""
        callback = CostTrackingCallback()
        
        assert callback.total_tokens == 0
        assert callback.prompt_tokens == 0
        assert callback.completion_tokens == 0
        assert callback.total_cost == 0.0
        assert callback.call_count == 0
    
    def test_cost_callback_tracks_call_count(self):
        """Test callback increments call count"""
        callback = CostTrackingCallback()
        
        callback.on_llm_start({}, ["test prompt"])
        callback.on_llm_start({}, ["another prompt"])
        
        assert callback.call_count == 2
    
    def test_cost_callback_calculates_tokens(self):
        """Test callback extracts and accumulates token counts"""
        callback = CostTrackingCallback()
        
        # Mock response with token usage
        mock_response = Mock()
        mock_response.llm_output = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }
        
        callback.on_llm_end(mock_response)
        
        assert callback.prompt_tokens == 100
        assert callback.completion_tokens == 50
        assert callback.total_tokens == 150
        # Cost should be calculated (>= 0)
        assert callback.total_cost >= 0.0
    
    def test_cost_callback_accumulates_multiple_calls(self):
        """Test callback accumulates across multiple LLM calls"""
        callback = CostTrackingCallback()
        
        # First call
        mock_response1 = Mock()
        mock_response1.llm_output = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }
        callback.on_llm_end(mock_response1)
        
        # Second call
        mock_response2 = Mock()
        mock_response2.llm_output = {
            "token_usage": {
                "prompt_tokens": 200,
                "completion_tokens": 75
            }
        }
        callback.on_llm_end(mock_response2)
        
        assert callback.prompt_tokens == 300
        assert callback.completion_tokens == 125
        assert callback.total_tokens == 425
    
    def test_cost_callback_summary(self):
        """Test cost summary returns correct format"""
        callback = CostTrackingCallback()
        callback.total_tokens = 1000
        callback.prompt_tokens = 700
        callback.completion_tokens = 300
        callback.total_cost = 0.000123
        callback.call_count = 3
        
        summary = callback.get_summary()
        
        assert summary["total_tokens"] == 1000
        assert summary["prompt_tokens"] == 700
        assert summary["completion_tokens"] == 300
        assert summary["total_cost_usd"] == 0.000123
        assert summary["call_count"] == 3
    
    def test_cost_callback_reset(self):
        """Test callback reset clears all counters"""
        callback = CostTrackingCallback()
        callback.total_tokens = 1000
        callback.prompt_tokens = 700
        callback.completion_tokens = 300
        callback.total_cost = 0.000123
        callback.call_count = 3
        
        callback.reset()
        
        assert callback.total_tokens == 0
        assert callback.prompt_tokens == 0
        assert callback.completion_tokens == 0
        assert callback.total_cost == 0.0
        assert callback.call_count == 0
    
    def test_gemini_client_cost_tracking(self):
        """Test GeminiClient integrates cost tracking"""
        # Reset global callback
        gemini_client.reset_cost_tracking()
        
        initial_summary = gemini_client.get_cost_summary()
        assert initial_summary["total_cost_usd"] == 0.0
    
    def test_cost_estimate(self):
        """Test cost estimation utility"""
        cost = gemini_client.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000
        )
        
        # Cost should be >= 0 (0 for free tier, >0 for paid tier)
        assert cost >= 0.0
        # If not free tier, cost should be reasonable
        if cost > 0:
            # With Gemini default pricing (~$0.075 input + $0.30 output per 1M)
            # 1M input + 1M output = ~$0.375
            assert 0.2 < cost < 1.0


class TestLangChainToolIntegration:
    """Tests for LangChain tool wrappers"""
    
    def test_semantic_tool_wrapper_loads(self):
        """Test semantic tool can be imported from langchain_tools"""
        from backend.tools.langchain_tools import semantic_tool
        
        assert semantic_tool is not None
        assert semantic_tool.name == "semantic_tool"
    
    def test_semantic_tool_in_tools_list(self):
        """Test semantic tool is in SQL analysis tools"""
        from backend.tools.langchain_tools import sql_analysis_tools
        
        tool_names = [t.name for t in sql_analysis_tools]
        assert "semantic_tool" in tool_names
        assert len(sql_analysis_tools) == 3  # rules, parser, semantic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
