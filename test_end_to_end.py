#!/usr/bin/env python3
"""
End-to-End Test for SentinAL Phase 1
Tests the complete workflow from file upload to Defense Memo generation
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported"""
    print("✓ Testing imports...")
    try:
        from backend.state import AnalysisState, File, FileType, ConstraintLevel
        from backend.workflow import create_workflow
        from backend.config import settings
        print("  ✅ All imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_workflow():
    """Test the complete workflow with a sample SQL file"""
    print("\n✓ Testing workflow execution...")
    try:
        from backend.state import AnalysisState, File, FileType
        from backend.workflow import create_workflow
        from datetime import datetime
        
        # Create test file
        test_sql = """
        -- Dangerous operation
        DROP TABLE users;
        DELETE FROM orders;
        """
        
        # Initialize state
        initial_state: AnalysisState = {
            "files": [
                File(
                    filename="test_migration.sql",
                    content=test_sql,
                    file_type=FileType.SQL,
                    size_bytes=len(test_sql)
                )
            ],
            "findings": [],
            "cross_file_deps": [],
            "agent_decisions": [],
            "overall_risk": None,
            "defense_memo": None,
            "analysis_started_at": datetime.now(),
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        # Run workflow
        print("  → Running LangGraph workflow...")
        workflow = create_workflow()
        result = workflow.invoke(initial_state)
        
        # Validate results
        assert result.get("defense_memo") is not None, "Defense memo not generated"
        assert result.get("overall_risk") is not None, "Risk level not set"
        assert len(result.get("findings", [])) > 0, "No findings detected"
        
        print(f"  ✅ Workflow executed successfully")
        print(f"     - Findings: {len(result.get('findings', []))}")
        print(f"     - Risk Level: {result.get('overall_risk')}")
        print(f"     - Memo Length: {len(result.get('defense_memo', '')) if result.get('defense_memo') else 0} chars")
        return True
    except Exception as e:
        print(f"  ❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_models():
    """Test API models"""
    print("\n✓ Testing API models...")
    try:
        from backend.api_models import AnalysisResponse, HealthResponse
        
        # Test creating response
        response = AnalysisResponse(
            defense_memo="# Test Memo",
            risk_score=40,
            risk_classification="HIGH",
            total_findings=2,
            critical_count=0,
            high_count=2,
            medium_count=0,
            low_count=0,
            analysis_cost_usd=0.001,
            analysis_time_seconds=2.5
        )
        
        assert response.risk_score == 40
        print("  ✅ API models working correctly")
        return True
    except Exception as e:
        print(f"  ❌ API models test failed: {e}")
        return False

def test_risk_scoring():
    """Test risk scoring utilities"""
    print("\n✓ Testing risk scoring...")
    try:
        from backend.utils.risk_scoring import calculate_risk_score, get_risk_classification
        from backend.state import Finding, ConstraintLevel
        
        # Create test findings
        findings = [
            Finding(
                file_id="test.sql",
                severity=ConstraintLevel.CRITICAL,
                category="DROP_TABLE",
                description="Dangerous DROP statement",
                detected_by="rules_tool"
            ),
            Finding(
                file_id="test.sql",
                severity=ConstraintLevel.HIGH,
                category="DELETE_UNFILTERED",
                description="DELETE without WHERE",
                detected_by="rules_tool"
            )
        ]
        
        score = calculate_risk_score(findings)
        classification = get_risk_classification(score)
        
        assert score == 60  # 40 (CRITICAL) + 20 (HIGH)
        assert classification == "CRITICAL"  # >= 60
        
        print(f"  ✅ Risk scoring working correctly (score: {score}, class: {classification})")
        return True
    except Exception as e:
        print(f"  ❌ Risk scoring test failed: {e}")
        return False

def main():
    print("=" * 70)
    print("SentinAL - Phase 1 End-to-End Test")
    print("=" * 70)
    
    results = []
    
    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("Risk Scoring", test_risk_scoring()))
    results.append(("API Models", test_api_models()))
    results.append(("Workflow", test_workflow()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:.<50} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Phase 1 is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED. Please review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
