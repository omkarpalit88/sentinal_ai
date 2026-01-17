"""
LLM-Powered Semantic Analysis Tool
Detects SQL risks beyond regex and AST parsing using Gemini
"""
from typing import List, Dict, Optional, Any
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.state import Finding, ConstraintLevel


# Semantic Analysis Prompt for Gemini
SEMANTIC_ANALYSIS_PROMPT = """You are an expert database migration reviewer analyzing SQL for deployment risks.

Your task: Perform deep semantic analysis to find risks that simple pattern matching cannot detect.

SQL File: {filename}
SQL Content:
```sql
{content}
```

Context from AST Parser:
{context}

Focus on these risk categories:

1. **Business Logic Violations**
   - Deleting data without archiving
   - Modifying critical tables without safeguards
   - Breaking referential integrity

2. **Implicit Assumptions**
   - Assuming specific execution order
   - Relying on undefined behavior
   - Missing transaction boundaries

3. **Data Integrity Risks**
   - Orphaned foreign key references
   - Cascade delete dangers
   - Missing constraints after schema changes

4. **Performance Anti-Patterns**
   - N+1 query patterns in migrations
   - Missing indexes on new columns
   - Full table scans on large tables

5. **Security Issues**
   - SQL injection vectors in dynamic SQL
   - Exposed PII in new columns
   - Missing access controls

For each risk found, provide:
- **Severity**: CRITICAL, HIGH, MEDIUM, or LOW
- **Category**: One of the 5 categories above
- **Description**: What the risk is (1-2 sentences)
- **Reasoning**: Why this is risky (2-3 sentences)
- **Recommendation**: How to fix it (1-2 sentences)

Format your response as a JSON array:
```json
[
  {{
    "severity": "HIGH",
    "category": "Business Logic Violation",
    "description": "...",
    "reasoning": "...",
    "recommendation": "..."
  }}
]
```

If no semantic risks are found, return an empty array: []

Be conservative - only flag real risks, not hypothetical issues."""


class SemanticTool:
    """
    LLM-powered semantic analysis tool for SQL
    
    Uses Gemini to detect context-dependent risks that deterministic tools miss:
    - Business logic violations
    - Implicit assumptions
    - Data integrity risks
    - Performance anti-patterns
    - Security issues
    """
    
    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        """
        Initialize semantic tool
        
        Args:
            llm: Optional LangChain LLM instance (uses gemini_client if None)
        """
        if llm is None:
            from backend.utils.gemini_client import gemini_client
            self.llm = gemini_client.llm
        else:
            self.llm = llm
        
        self.name = "semantic_tool"
    
    def analyze(
        self, 
        filename: str, 
        content: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Finding], float]:
        """
        Perform semantic analysis on SQL using LLM
        
        Args:
            filename: SQL file name
            content: SQL code
            context: Optional context from parser (tables created/dropped, etc.)
            
        Returns:
            Tuple of (List of Finding objects, cost in USD)
        """
        # Format context for LLM
        context_str = self._format_context(context) if context else "No parser context available"
        
        # Build prompt
        prompt = SEMANTIC_ANALYSIS_PROMPT.format(
            filename=filename,
            content=content,
            context=context_str
        )
        
        try:
            # Get cost before call
            from backend.utils.gemini_client import gemini_client
            gemini_client.reset_cost_tracking()
            
            # Call Gemini
            response = self.llm.invoke(prompt)
            
            # Get cost after call
            cost_summary = gemini_client.get_cost_summary()
            cost = cost_summary.get('total_cost_usd', 0.0)
            
            # Extract text from response
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse findings from JSON
            findings = self._parse_llm_response(response_text, filename)
            
            return findings, cost
            
        except Exception as e:
            # Log error but don't fail - return empty findings
            print(f"Warning: Semantic analysis failed for {filename}: {e}")
            return [], 0.0
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format parser context for LLM"""
        lines = []
        
        if context.get("tables_created"):
            lines.append(f"Tables Created: {', '.join(context['tables_created'])}")
        if context.get("tables_dropped"):
            lines.append(f"Tables Dropped: {', '.join(context['tables_dropped'])}")
        if context.get("tables_truncated"):
            lines.append(f"Tables Truncated: {', '.join(context['tables_truncated'])}")
        if context.get("tables_referenced"):
            lines.append(f"Tables Referenced: {', '.join(context['tables_referenced'])}")
        if context.get("has_ddl"):
            lines.append("Contains DDL operations")
        if context.get("has_dml"):
            lines.append("Contains DML operations")
        
        return "\n".join(lines) if lines else "No entities detected"
    
    def _parse_llm_response(self, response_text: str, filename: str) -> List[Finding]:
        """
        Parse LLM JSON response into Finding objects
        
        Args:
            response_text: Raw LLM response
            filename: File being analyzed
            
        Returns:
            List of Finding objects
        """
        import json
        import re
        
        findings = []
        
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```json\s*(\[.*?\])\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array directly
            json_match = re.search(r'(\[.*?\])', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                return []  # No valid JSON found
        
        try:
            llm_findings = json.loads(json_str)
            
            for item in llm_findings:
                # Map severity string to ConstraintLevel
                severity_map = {
                    "CRITICAL": ConstraintLevel.CRITICAL,
                    "HIGH": ConstraintLevel.HIGH,
                    "MEDIUM": ConstraintLevel.MEDIUM,
                    "LOW": ConstraintLevel.LOW
                }
                severity = severity_map.get(item.get("severity", "MEDIUM"), ConstraintLevel.MEDIUM)
                
                finding = Finding(
                    file_id=filename,
                    line_number=None,  # LLM doesn't provide line numbers
                    severity=severity,
                    category=item.get("category", "LLM_SEMANTIC_ISSUE"),
                    description=item.get("description", ""),
                    detected_by="semantic_tool_llm",
                    reasoning=item.get("reasoning", ""),
                    recommendation=item.get("recommendation")
                )
                findings.append(finding)
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            return []
        
        return findings


# Singleton instance
semantic_tool = SemanticTool()
