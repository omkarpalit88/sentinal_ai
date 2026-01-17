"""
YAML Rules Tool - Pattern matching for YAML/Kubernetes risk detection
"""
import re
from typing import List
from backend.state import Finding, ConstraintLevel
from backend.config import VETO_RULES_YAML


class YAMLRulesTool:
    """Deterministic pattern matching for YAML files"""
    
    def __init__(self):
        self.yaml_rules = VETO_RULES_YAML
    
    def analyze(self, filename: str, content: str) -> List[Finding]:
        """
        Apply YAML veto rules to file content
        
        Args:
            filename: Name of the YAML file
            content: YAML content to analyze
            
        Returns:
            List of Finding objects for each matched pattern
        """
        findings = []
        
        for rule in self.yaml_rules:
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
                
                # Extract snippet
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                snippet = content[start:end].strip()
                
                finding = Finding(
                    file_id=filename,
                    line_number=line_number,
                    severity=severity,
                    category=category,
                    description=f"{description} (Line {line_number})",
                    detected_by="yaml_rules_tool",
                    reasoning=f"Pattern matched: {pattern}",
                    code_snippet=snippet,
                    recommendation=recommendation
                )
                findings.append(finding)
        
        return findings


# Singleton instance
yaml_rules_tool = YAMLRulesTool()
