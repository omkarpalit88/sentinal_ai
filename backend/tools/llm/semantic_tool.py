"""
Semantic Tool - LLM-powered business logic risk detection
Uses Gemini to understand context beyond pattern matching
"""
from typing import List
import json
from backend.state import Finding, ConstraintLevel
from backend.utils.gemini_client import gemini_client


SEMANTIC_ANALYSIS_PROMPT = """You are a database security expert analyzing SQL for business logic risks.

Analyze this SQL script for risks that require BUSINESS CONTEXT understanding:

SQL Script:
```sql
{sql_content}
```

Focus on:
1. **GDPR/Privacy Risks:**
   - Personal data deletion without explicit consent logging
   - Data anonymization that might be irreversible
   - User data operations on production tables

2. **Financial Data Risks:**
   - Transaction modifications (UPDATE/DELETE on payment/order tables)
   - Balance adjustments without audit trail
   - Price changes without approval workflow

3. **Audit Trail Risks:**
   - Deleting logs or audit records
   - Modifications to immutable data (invoices, receipts)
   - Removing historical compliance data

4. **Coordination Requirements:**
   - Schema changes requiring app deployment coordination
   - Breaking changes without deprecation period
   - Missing transaction boundaries for multi-statement operations

**IMPORTANT:**
- Only flag truly risky operations (HIGH or MEDIUM severity)
- Ignore safe operations (SELECT, safe UPDATEs with WHERE)
- Consider table names for context (payment*, customer*, user*, transaction*, audit*, log*)
- Be conservative - only flag real business risks

Output format (JSON only, no markdown):
{{
  "findings": [
    {{
      "severity": "HIGH" | "MEDIUM",
      "category": "GDPR_RISK" | "FINANCIAL_DATA_RISK" | "AUDIT_TRAIL_RISK" | "COORDINATION_REQUIRED",
      "description": "Brief description of the risk",
      "line_number": null,
      "recommendation": "Specific mitigation advice"
    }}
  ]
}}

If NO semantic risks found, return: {{"findings": []}}

Return ONLY valid JSON, no other text."""


class SemanticTool:
    """LLM-powered semantic analysis for business logic risks"""
    
    def __init__(self):
        self.llm = gemini_client.llm
    
    def analyze(self, filename: str, content: str) -> List[Finding]:
        """
        Use LLM to detect business logic risks
        
        Args:
            filename: SQL filename
            content: SQL content
            
        Returns:
            List of Finding objects for semantic risks
        """
        # Call Gemini for semantic analysis
        prompt = SEMANTIC_ANALYSIS_PROMPT.format(sql_content=content)
        
        try:
            response = self.llm.invoke(prompt)
            
            # Extract JSON from response
            response_text = response.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse LLM response as JSON
            result = json.loads(response_text)
            
            findings = []
            for f in result.get("findings", []):
                finding = Finding(
                    file_id=filename,
                    line_number=f.get("line_number"),
                    severity=ConstraintLevel[f["severity"]],
                    category=f["category"],
                    description=f["description"],
                    detected_by="semantic_tool",
                    reasoning="LLM semantic analysis detected business logic risk",
                    recommendation=f["recommendation"]
                )
                findings.append(finding)
            
            return findings
            
        except json.JSONDecodeError as e:
            # Log error but don't block analysis
            print(f"Semantic tool JSON parse error: {e}")
            print(f"Response was: {response_text[:200]}")
            return []
        except Exception as e:
            # If LLM fails, return empty (don't block analysis)
            print(f"Semantic tool error: {e}")
            return []


# Singleton
semantic_tool = SemanticTool()
