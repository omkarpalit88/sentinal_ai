"""
Utility helper functions
"""
import re
from typing import Optional
from backend.state import FileType


def detect_file_type(filename: str, content: Optional[str] = None) -> FileType:
    """
    Detect file type from filename and optionally content
    
    Args:
        filename: Name of the file
        content: Optional file content for deeper inspection
        
    Returns:
        FileType enum value
    """
    filename_lower = filename.lower()
    
    # Extension-based detection
    if filename_lower.endswith('.sql'):
        return FileType.SQL
    elif filename_lower.endswith('.tf') or filename_lower.endswith('.tfvars'):
        return FileType.TERRAFORM
    elif filename_lower.endswith(('.yaml', '.yml')):
        return FileType.YAML
    
    # Content-based detection (if extension ambiguous)
    if content:
        # SQL keywords
        if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b', 
                    content, re.IGNORECASE):
            return FileType.SQL
        
        # Terraform keywords
        if re.search(r'\b(resource|provider|variable|output|module)\s+"', 
                    content, re.IGNORECASE):
            return FileType.TERRAFORM
        
        # YAML structure
        if re.search(r'^\s*\w+:\s*$', content, re.MULTILINE):
            return FileType.YAML
    
    return FileType.UNKNOWN


def extract_line_snippet(content: str, line_number: int, context_lines: int = 2) -> str:
    """
    Extract code snippet around a specific line
    
    Args:
        content: Full file content
        line_number: Target line (1-indexed)
        context_lines: Number of lines before/after to include
        
    Returns:
        Code snippet with line numbers
    """
    lines = content.split('\n')
    start = max(0, line_number - context_lines - 1)
    end = min(len(lines), line_number + context_lines)
    
    snippet_lines = []
    for i in range(start, end):
        prefix = ">>> " if i == line_number - 1 else "    "
        snippet_lines.append(f"{prefix}{i+1:4d} | {lines[i]}")
    
    return '\n'.join(snippet_lines)


def calculate_overall_risk(findings: list) -> str:
    """
    Calculate overall risk level from findings
    
    Args:
        findings: List of Finding objects
        
    Returns:
        Overall risk level (CRITICAL/HIGH/MEDIUM/LOW/INFO)
    """
    if not findings:
        return "INFO"
    
    # Count by severity
    severity_counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "INFO": 0
    }
    
    for finding in findings:
        severity = finding.severity.value if hasattr(finding.severity, 'value') else finding.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Decision logic
    if severity_counts["CRITICAL"] > 0:
        return "CRITICAL"
    elif severity_counts["HIGH"] >= 3:
        return "CRITICAL"
    elif severity_counts["HIGH"] >= 1:
        return "HIGH"
    elif severity_counts["MEDIUM"] >= 5:
        return "HIGH"
    elif severity_counts["MEDIUM"] >= 1:
        return "MEDIUM"
    elif severity_counts["LOW"] > 0:
        return "LOW"
    else:
        return "INFO"


def recommend_approval(overall_risk: str) -> bool:
    """
    Recommend approval/rejection based on overall risk
    
    Args:
        overall_risk: Overall risk level
        
    Returns:
        True if recommend approval, False otherwise
    """
    return overall_risk in ["LOW", "INFO"]
