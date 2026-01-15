"""
Rules Tool - Pattern matching for SQL risk detection
Uses regex patterns to detect dangerous SQL operations (deterministic, fast, reliable)
"""
import re
from typing import List, Dict, Any
from backend.state import Finding, ConstraintLevel
from backend.config import VETO_RULES_SQL, VETO_RULES_TERRAFORM, VETO_RULES_YAML


class RulesTool:
    """
    Deterministic pattern-matching tool for risk detection.
    
    Applies hardcoded veto rules from config.py to detect:
    - DROP DATABASE/TABLE
    - TRUNCATE TABLE
    - Unfiltered DELETE/UPDATE
    - Commented rollback logic
    - force_destroy in Terraform
    - Zero replicas in YAML
    
    Advantages:
    - Fast (<1 second for any file)
    - 100% reproducible
    - Never hallucinates
    - Zero API cost
    """
    
    def __init__(self):
        self.sql_rules = VETO_RULES_SQL
        self.terraform_rules = VETO_RULES_TERRAFORM
        self.yaml_rules = VETO_RULES_YAML
    
    def analyze_sql(self, filename: str, content: str) -> List[Finding]:
        """
        Apply SQL veto rules to file content
        
        Args:
            filename: Name of the SQL file
            content: SQL file content
            
        Returns:
            List of Finding objects
        """
        findings = []
        
        for rule in self.sql_rules:
            pattern = rule["pattern"]
            severity = ConstraintLevel[rule["severity"]]
            category = rule["category"]
            description = rule["description"]
            recommendation = rule["recommendation"]
            
            # Find all matches
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                # Calculate line number
                line_number = content[:match.start()].count('\n') + 1
                
                # Extract code snippet (20 chars before/after)
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                snippet = content[start:end].strip()
                
                finding = Finding(
                    file_id=filename,
                    line_number=line_number,
                    severity=severity,
                    category=category,
                    description=f"{description} (Line {line_number})",
                    detected_by="rules_tool",
                    reasoning=f"Pattern matched: {pattern}",
                    code_snippet=snippet,
                    recommendation=recommendation
                )
                findings.append(finding)
        
        return findings
    
    def analyze_terraform(self, filename: str, content: str) -> List[Finding]:
        """Apply Terraform veto rules"""
        findings = []
        
        for rule in self.terraform_rules:
            pattern = rule["pattern"]
            severity = ConstraintLevel[rule["severity"]]
            category = rule["category"]
            description = rule["description"]
            recommendation = rule["recommendation"]
            
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                snippet = content[start:end].strip()
                
                finding = Finding(
                    file_id=filename,
                    line_number=line_number,
                    severity=severity,
                    category=category,
                    description=f"{description} (Line {line_number})",
                    detected_by="rules_tool",
                    reasoning=f"Pattern matched: {pattern}",
                    code_snippet=snippet,
                    recommendation=recommendation
                )
                findings.append(finding)
        
        return findings
    
    def analyze_yaml(self, filename: str, content: str) -> List[Finding]:
        """Apply YAML veto rules"""
        findings = []
        
        for rule in self.yaml_rules:
            pattern = rule["pattern"]
            severity = ConstraintLevel[rule["severity"]]
            category = rule["category"]
            description = rule["description"]
            recommendation = rule["recommendation"]
            
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                snippet = content[start:end].strip()
                
                finding = Finding(
                    file_id=filename,
                    line_number=line_number,
                    severity=severity,
                    category=category,
                    description=f"{description} (Line {line_number})",
                    detected_by="rules_tool",
                    reasoning=f"Pattern matched: {pattern}",
                    code_snippet=snippet,
                    recommendation=recommendation
                )
                findings.append(finding)
        
        return findings
    
    def analyze(self, filename: str, content: str, file_type: str) -> List[Finding]:
        """
        Main entry point - analyze file based on type
        
        Args:
            filename: Name of the file
            content: File content
            file_type: Type of file (sql, terraform, yaml)
            
        Returns:
            List of Finding objects
        """
        file_type_lower = file_type.lower()
        
        if file_type_lower == "sql":
            return self.analyze_sql(filename, content)
        elif file_type_lower == "terraform":
            return self.analyze_terraform(filename, content)
        elif file_type_lower == "yaml":
            return self.analyze_yaml(filename, content)
        else:
            return []


# Singleton instance
rules_tool = RulesTool()
