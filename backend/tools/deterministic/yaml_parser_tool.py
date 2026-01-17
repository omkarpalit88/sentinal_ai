"""
YAML Parser Tool - YAML structural analysis
"""
import re
from typing import List, Dict
from backend.state import Finding, ConstraintLevel


class YAMLParserTool:
    """Parse YAML to extract structure and detect issues"""
    
    def analyze(self, filename: str, content: str) -> List[Finding]:
        """
        Analyze YAML structure for issues
        
        Args:
            filename: Name of the YAML file
            content: YAML content to analyze
            
        Returns:
            List of Finding objects for structural issues
        """
        findings = []
        entities = self.get_entities(content)
        
        # Check for deployments without resource limits
        if entities["has_deployment"] and not entities["has_resource_limits"]:
            findings.append(Finding(
                file_id=filename,
                line_number=None,
                severity=ConstraintLevel.MEDIUM,
                category="MISSING_RESOURCE_LIMITS",
                description="No resource limits found - can cause cluster instability",
                detected_by="yaml_parser_tool",
                reasoning="Best practice: Add resource limits and requests",
                recommendation="Add resources.limits and resources.requests to containers"
            ))
        
        return findings
    
    def get_entities(self, content: str) -> Dict:
        """
        Extract YAML/Kubernetes entities from content
        
        Args:
            content: YAML content to parse
            
        Returns:
            Dictionary with extracted entities
        """
        return {
            "kind": re.findall(r'kind:\s*(\w+)', content),
            "has_deployment": bool(re.search(r'kind:\s*Deployment', content)),
            "has_service": bool(re.search(r'kind:\s*Service', content)),
            "has_resource_limits": bool(re.search(r'limits:', content))
        }


# Singleton instance
yaml_parser_tool = YAMLParserTool()
