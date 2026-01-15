"""
Risk Scoring Utilities for SentinAL
Deterministic risk calculation and classification
"""
from typing import List
from backend.state import Finding, ConstraintLevel


def calculate_risk_score(findings: List[Finding]) -> int:
    """
    Calculate weighted risk score (0-100) based on finding severity
    
    Scoring:
    - CRITICAL: 40 points
    - HIGH: 20 points
    - MEDIUM: 10 points
    - LOW: 5 points
    
    Args:
        findings: List of Finding objects
        
    Returns:
        Risk score (0-100, capped at 100)
    """
    score = 0
    
    for finding in findings:
        if finding.severity == ConstraintLevel.CRITICAL:
            score += 40
        elif finding.severity == ConstraintLevel.HIGH:
            score += 20
        elif finding.severity == ConstraintLevel.MEDIUM:
            score += 10
        else:  # LOW
            score += 5
    
    # Cap at 100
    return min(score, 100)


def get_risk_classification(score: int) -> str:
    """
    Map numerical risk score to classification level
    
    Classification thresholds:
    - 60+: CRITICAL
    - 40-59: HIGH
    - 20-39: MEDIUM
    - 0-19: LOW
    
    Args:
        score: Risk score (0-100)
        
    Returns:
        Classification string: CRITICAL, HIGH, MEDIUM, or LOW
    """
    if score >= 60:
        return "CRITICAL"
    elif score >= 40:
        return "HIGH"
    elif score >= 20:
        return "MEDIUM"
    else:
        return "LOW"


def get_findings_by_severity(findings: List[Finding]) -> dict:
    """
    Group findings by severity level
    
    Args:
        findings: List of Finding objects
        
    Returns:
        Dict with severity levels as keys, lists of findings as values
    """
    grouped = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": []
    }
    
    for finding in findings:
        grouped[finding.severity.value].append(finding)
    
    return grouped
