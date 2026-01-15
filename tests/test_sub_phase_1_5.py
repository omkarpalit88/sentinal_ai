"""
Unit tests for Sub-Phase 1.5: Synthesis Agent and Risk Scoring
Tests risk calculation, classification, and Defense Memo generation
"""
import pytest
from unittest.mock import Mock, MagicMock
from backend.utils.risk_scoring import (
    calculate_risk_score,
    get_risk_classification,
    get_findings_by_severity
)
from backend.agents.synthesis_agent import SynthesisAgent
from backend.state import Finding, ConstraintLevel, File, FileType, AnalysisState
from datetime import datetime


class TestRiskScoring:
    """Tests for risk scoring utilities"""
    
    def test_calculate_risk_score_single_critical(self):
        """Test risk score with single CRITICAL finding"""
        findings = [
            Finding(
                file_id="test.sql",
                severity=ConstraintLevel.CRITICAL,
                category="DROP_DATABASE",
                description="Test",
                detected_by="test"
            )
        ]
        score = calculate_risk_score(findings)
        assert score == 40
    
    def test_calculate_risk_score_multiple_severities(self):
        """Test risk score with mixed severities"""
        findings = [
            Finding(file_id="test.sql", severity=ConstraintLevel.CRITICAL, category="TEST", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.HIGH, category="TEST", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.MEDIUM, category="TEST", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.LOW, category="TEST", description="", detected_by="test"),
        ]
        score = calculate_risk_score(findings)
        # 40 + 20 + 10 + 5 = 75
        assert score == 75
    
    def test_calculate_risk_score_capped_at_100(self):
        """Test risk score caps at 100"""
        findings = [
            Finding(file_id="test.sql", severity=ConstraintLevel.CRITICAL, category="TEST", description="", detected_by="test")
            for _ in range(5)  # 5 * 40 = 200
        ]
        score = calculate_risk_score(findings)
        assert score == 100
    
    def test_calculate_risk_score_empty(self):
        """Test risk score with no findings"""
        score = calculate_risk_score([])
        assert score == 0
    
    def test_get_risk_classification_critical(self):
        """Test classification for CRITICAL level"""
        assert get_risk_classification(60) == "CRITICAL"
        assert get_risk_classification(100) == "CRITICAL"
    
    def test_get_risk_classification_high(self):
        """Test classification for HIGH level"""
        assert get_risk_classification(40) == "HIGH"
        assert get_risk_classification(59) == "HIGH"
    
    def test_get_risk_classification_medium(self):
        """Test classification for MEDIUM level"""
        assert get_risk_classification(20) == "MEDIUM"
        assert get_risk_classification(39) == "MEDIUM"
    
    def test_get_risk_classification_low(self):
        """Test classification for LOW level"""
        assert get_risk_classification(0) == "LOW"
        assert get_risk_classification(19) == "LOW"
    
    def test_get_findings_by_severity(self):
        """Test grouping findings by severity"""
        findings = [
            Finding(file_id="test.sql", severity=ConstraintLevel.CRITICAL, category="C1", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.CRITICAL, category="C2", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.HIGH, category="H1", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.MEDIUM, category="M1", description="", detected_by="test"),
        ]
        
        grouped = get_findings_by_severity(findings)
        
        assert len(grouped["CRITICAL"]) == 2
        assert len(grouped["HIGH"]) == 1
        assert len(grouped["MEDIUM"]) == 1
        assert len(grouped["LOW"]) == 0


class TestSynthesisAgent:
    """Tests for Synthesis Agent"""
    
    def test_synthesis_agent_initialization(self):
        """Test agent initializes correctly"""
        agent = SynthesisAgent()
        assert agent.name == "synthesis_agent"
        assert agent.llm is not None
    
    def test_process_updates_state_fields(self):
        """Test that process updates required state fields"""
        agent = SynthesisAgent()
        
        # Mock LLM to return simple memo
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "# Defense Memo\nTest memo"
        mock_llm.invoke.return_value = mock_response
        agent.llm = mock_llm
        
        # Create test state
        state: AnalysisState = {
            "files": [File(filename="test.sql", content="SELECT 1;", file_type=FileType.SQL, size_bytes=10)],
            "findings": [
                Finding(file_id="test.sql", severity=ConstraintLevel.HIGH, category="TEST", description="Test finding", detected_by="test")
            ],
            "cross_file_deps": [],
            "agent_decisions": [],
            "overall_risk": None,
            "defense_memo": None,
            "analysis_started_at": datetime.now(),
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        result = agent.process(state)
        
        # Check state was updated
        assert result["defense_memo"] is not None
        assert result["overall_risk"] is not None
        assert result["analysis_completed_at"] is not None
        assert isinstance(result["overall_risk"], str)  # Should be string classification
    
    def test_fallback_memo_on_llm_failure(self):
        """Test fallback memo generation when LLM fails"""
        agent = SynthesisAgent()
        
        # Mock LLM to raise exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM Error")
        agent.llm = mock_llm
        
        state: AnalysisState = {
            "files": [File(filename="test.sql", content="SELECT 1;", file_type=FileType.SQL, size_bytes=10)],
            "findings": [
                Finding(file_id="test.sql", severity=ConstraintLevel.CRITICAL, category="DROP_TABLE", description="Dangerous operation", detected_by="test")
            ],
            "cross_file_deps": [],
            "agent_decisions": [],
            "overall_risk": None,
            "defense_memo": None,
            "analysis_started_at": datetime.now(),
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        result = agent.process(state)
        
        # Should still generate a memo (fallback)
        assert result["defense_memo"] is not None
        assert "Defense Memo" in result["defense_memo"]
        assert result["overall_risk"] == "HIGH"  # 40 score = HIGH
    
    def test_risk_classification_in_state(self):
        """Test that overall_risk is set to classification string"""
        agent = SynthesisAgent()
        
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "# Memo"
        mock_llm.invoke.return_value = mock_response
        agent.llm = mock_llm
        
        # Create findings with 65 score (CRITICAL level)
        findings = [
            Finding(file_id="test.sql", severity=ConstraintLevel.CRITICAL, category="T1", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.HIGH, category="T2", description="", detected_by="test"),
            Finding(file_id="test.sql", severity=ConstraintLevel.MEDIUM, category="T3", description="", detected_by="test"),
        ]
        # 40 + 20 + 10 = 70 -> CRITICAL
        
        state: AnalysisState = {
            "files": [File(filename="test.sql", content="", file_type=FileType.SQL, size_bytes=0)],
            "findings": findings,
            "cross_file_deps": [],
            "agent_decisions": [],
            "overall_risk": None,
            "defense_memo": None,
            "analysis_started_at": datetime.now(),
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        result = agent.process(state)
        assert result["overall_risk"] == "CRITICAL"


class TestSynthesisMemoFormatting:
    """Tests for memo formatting helpers"""
    
    def test_format_critical_findings(self):
        """Test critical findings formatting"""
        agent = SynthesisAgent()
        findings = [
            Finding(
                file_id="test.sql",
                severity=ConstraintLevel.CRITICAL,
                category="DROP_DATABASE",
                description="Dropping production database",
                detected_by="rules_tool",
                reasoning="This will delete all data permanently"
            )
        ]
        
        formatted = agent._format_critical_findings(findings)
        assert "DROP_DATABASE" in formatted
        assert "Dropping production database" in formatted
    
    def test_format_critical_findings_empty(self):
        """Test formatting with no critical findings"""
        agent = SynthesisAgent()
        formatted = agent._format_critical_findings([])
        assert formatted == "None"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
