"""
Terraform Parser Tool - HCL structural analysis
"""
import re
from typing import List, Dict
from backend.state import Finding, ConstraintLevel


class TerraformParserTool:
    """Parse Terraform HCL to extract structure and detect issues"""
    
    def analyze(self, filename: str, content: str) -> List[Finding]:
        """
        Analyze Terraform structure for issues
        
        Args:
            filename: Name of the Terraform file
            content: HCL content to analyze
            
        Returns:
            List of Finding objects for structural issues
        """
        findings = []
        entities = self.get_entities(content)
        
        # Check for resources without lifecycle blocks
        if entities["resources"] and not entities["has_lifecycle"]:
            findings.append(Finding(
                file_id=filename,
                line_number=None,
                severity=ConstraintLevel.MEDIUM,
                category="MISSING_LIFECYCLE",
                description="No lifecycle blocks found - consider prevent_destroy for critical resources",
                detected_by="terraform_parser_tool",
                reasoning="Best practice: Add lifecycle blocks to critical resources",
                recommendation="Add lifecycle { prevent_destroy = true } to critical resources"
            ))
        
        return findings
    
    def get_entities(self, content: str) -> Dict:
        """
        Extract Terraform entities from HCL content
        
        Args:
            content: HCL content to parse
            
        Returns:
            Dictionary with extracted entities
        """
        return {
            "resources": re.findall(r'resource\s+"([^"]+)"\s+"([^"]+)"', content),
            "data_sources": re.findall(r'data\s+"([^"]+)"\s+"([^"]+)"', content),
            "modules": re.findall(r'module\s+"([^"]+)"', content),
            "has_lifecycle": bool(re.search(r'lifecycle\s*{', content))
        }


# Singleton instance
terraform_parser_tool = TerraformParserTool()
