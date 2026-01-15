"""
Unit tests for Sub-Phase 1.1: State Machine + Orchestrator
"""
import pytest
from datetime import datetime
from backend.state import (
    File, Finding, Dependency, AgentDecision, AnalysisState,
    FileType, ConstraintLevel,
    add_finding, add_decision, add_dependency
)
from backend.utils.helpers import (
    detect_file_type, extract_line_snippet,
    calculate_overall_risk, recommend_approval
)
from backend.orchestrator import OrchestratorAgent
from backend.workflow import create_workflow


class TestStateSchema:
    """Test Pydantic state models"""
    
    def test_file_model(self):
        file = File(
            filename="test.sql",
            content="SELECT * FROM users;",
            file_type=FileType.SQL,
            size_bytes=100
        )
        assert file.filename == "test.sql"
        assert file.file_type == FileType.SQL
    
    def test_finding_model(self):
        finding = Finding(
            file_id="test.sql",
            line_number=5,
            severity=ConstraintLevel.HIGH,
            category="DROP_TABLE",
            description="Dropping table detected",
            detected_by="rules_tool"
        )
        assert finding.severity == ConstraintLevel.HIGH
        assert finding.line_number == 5
    
    def test_immutable_state_update(self):
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
        
        finding = Finding(
            file_id="test.sql",
            severity=ConstraintLevel.HIGH,
            category="TEST",
            description="Test finding",
            detected_by="test"
        )
        
        new_state = add_finding(state, finding)
        
        # Original state unchanged
        assert len(state["findings"]) == 0
        # New state has finding
        assert len(new_state["findings"]) == 1


class TestHelpers:
    """Test utility helper functions"""
    
    def test_detect_file_type_sql(self):
        assert detect_file_type("migration_001.sql") == FileType.SQL
        assert detect_file_type("test.SQL") == FileType.SQL
    
    def test_detect_file_type_terraform(self):
        assert detect_file_type("main.tf") == FileType.TERRAFORM
        assert detect_file_type("variables.tfvars") == FileType.TERRAFORM
    
    def test_detect_file_type_yaml(self):
        assert detect_file_type("config.yaml") == FileType.YAML
        assert detect_file_type("deployment.yml") == FileType.YAML
    
    def test_detect_file_type_unknown(self):
        assert detect_file_type("readme.txt") == FileType.UNKNOWN
    
    def test_extract_line_snippet(self):
        content = "line1\nline2\nline3\nline4\nline5"
        snippet = extract_line_snippet(content, 3, context_lines=1)
        
        assert "line2" in snippet
        assert "line3" in snippet
        assert "line4" in snippet
        assert ">>>" in snippet  # Highlight marker
    
    def test_calculate_overall_risk_critical(self):
        findings = [
            Finding(
                file_id="test.sql",
                severity=ConstraintLevel.CRITICAL,
                category="TEST",
                description="Critical issue",
                detected_by="test"
            )
        ]
        assert calculate_overall_risk(findings) == "CRITICAL"
    
    def test_calculate_overall_risk_high(self):
        findings = [
            Finding(
                file_id="test.sql",
                severity=ConstraintLevel.HIGH,
                category="TEST",
                description="High issue",
                detected_by="test"
            )
        ]
        assert calculate_overall_risk(findings) == "HIGH"
    
    def test_recommend_approval_safe(self):
        assert recommend_approval("LOW") is True
        assert recommend_approval("INFO") is True
    
    def test_recommend_approval_unsafe(self):
        assert recommend_approval("CRITICAL") is False
        assert recommend_approval("HIGH") is False


class TestOrchestrator:
    """Test Orchestrator Agent"""
    
    def test_orchestrator_initialization(self):
        orchestrator = OrchestratorAgent()
        assert orchestrator.name == "orchestrator"
    
    def test_orchestrator_routing_sql(self):
        orchestrator = OrchestratorAgent()
        
        state: AnalysisState = {
            "files": [
                File(
                    filename="test.sql",
                    content="SELECT 1;",
                    file_type=FileType.SQL,
                    size_bytes=10
                )
            ],
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
        
        result = orchestrator.process(state)
        
        assert result["next_agent"] == "sql_agent"
        assert len(result["agent_decisions"]) > 0
        assert result["analysis_started_at"] is not None


class TestWorkflow:
    """Test LangGraph workflow"""
    
    def test_workflow_compilation(self):
        workflow = create_workflow()
        assert workflow is not None
    
    def test_workflow_execution_placeholder(self):
        """Test workflow with placeholder agents"""
        workflow = create_workflow()
        
        initial_state: AnalysisState = {
            "files": [
                File(
                    filename="test.sql",
                    content="SELECT * FROM users;",
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
            "analysis_started_at": None,
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        result = workflow.invoke(initial_state)
        
        # Should complete without errors
        assert result["analysis_completed_at"] is not None
        assert result["defense_memo"] is not None
        assert "Placeholder" in result["defense_memo"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
