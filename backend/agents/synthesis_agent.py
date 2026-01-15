"""
Synthesis Agent - Final analysis and Defense Memo generation
Aggregates findings and creates objective risk report using LLM
"""
from typing import Dict, Any
from datetime import datetime
from backend.state import AnalysisState, update_state
from backend.utils.risk_scoring import (
    calculate_risk_score,
    get_risk_classification,
    get_findings_by_severity
)
from backend.utils.gemini_client import gemini_client


# Defense Memo Generation Prompt
DEFENSE_MEMO_PROMPT = """You are a technical analyst creating an objective Defense Memo for a code deployment review.

Your task: Generate a clear, professional analysis report based on the findings below.

## Input Data

**File Analyzed:** {filename}
**Risk Score:** {risk_score}/100
**Risk Classification:** {risk_classification}
**Total Findings:** {total_findings}

**Critical Findings:**
{critical_findings_text}

**High-Priority Findings:**  
{high_findings_text}

**All Findings Summary:**
{all_findings_summary}

## Your Task

Generate a Defense Memo in the following markdown format:

# Defense Memo: {filename}

## Executive Summary
[Write 2-3 sentences: What was analyzed, what was found, overall risk picture. Be factual and concise.]

## Risk Assessment
- **Overall Risk Score:** {risk_score}/100
- **Risk Classification:** {risk_classification}
- **Analysis Date:** {analysis_date}

## Critical Issues
[For EACH critical finding, explain in this format:]

### [Issue Title]
**Location:** [Line number or operation]
**Risk:** [What specific danger does this pose?]
**Context:** [Why does this matter in a production environment?]

[If no critical findings, write: "No critical issues detected."]

## High-Priority Issues
[Brief list of HIGH severity findings with 1-line explanations. If none, write: "No high-priority issues detected."]

## Summary
[Write 2-3 sentences: Overall deployment risk conclusion. Be objective - state facts, don't prescribe actions.]

---
*Analysis Cost: ${total_cost} | Completed: {analysis_date}*

IMPORTANT:
- Be objective and factual - NO recommendations like "APPROVE" or "REJECT"
- Focus on explaining WHY issues are risky, not what to do about them
- Use clear, professional language
- Keep the memo concise but informative
"""


class SynthesisAgent:
    """
    Final agent that synthesizes all findings into Defense Memo
    
    Responsibilities:
    - Calculate overall risk score
    - Generate LLM-powered Defense Memo
    - Provide objective risk classification
    """
    
    def __init__(self):
        self.name = "synthesis_agent"
        self.llm = gemini_client.llm
    
    def process(self, state: AnalysisState) -> AnalysisState:
        """
        Process state to generate Defense Memo
        
        Args:
            state: Current analysis state with findings
            
        Returns:
            Updated state with defense_memo and overall_risk
        """
        findings = state["findings"]
        
        # Calculate risk score
        risk_score = calculate_risk_score(findings)
        risk_classification = get_risk_classification(risk_score)
        
        # Group findings by severity
        grouped_findings = get_findings_by_severity(findings)
        
        # Generate Defense Memo using LLM
        defense_memo = self._generate_memo(
            state=state,
            risk_score=risk_score,
            risk_classification=risk_classification,
            grouped_findings=grouped_findings
        )
        
        # Update state
        state = update_state(state, "defense_memo", defense_memo)
        state = update_state(state, "overall_risk", risk_classification)
        state = update_state(state, "analysis_completed_at", datetime.now())
        
        return state
    
    def _generate_memo(
        self,
        state: AnalysisState,
        risk_score: int,
        risk_classification: str,
        grouped_findings: Dict
    ) -> str:
        """
        Generate Defense Memo using LLM
        
        Args:
            state: Current state
            risk_score: Calculated risk score
            risk_classification: CRITICAL/HIGH/MEDIUM/LOW
            grouped_findings: Findings grouped by severity
            
        Returns:
            Markdown-formatted Defense Memo
        """
        # Get filename
        filename = state["files"][0].filename if state["files"] else "Unknown"
        
        # Format critical findings
        critical_findings_text = self._format_critical_findings(grouped_findings["CRITICAL"])
        
        # Format high findings
        high_findings_text = self._format_high_findings(grouped_findings["HIGH"])
        
        # Format all findings summary
        all_findings_summary = self._format_all_findings_summary(grouped_findings)
        
        # Build prompt
        prompt = DEFENSE_MEMO_PROMPT.format(
            filename=filename,
            risk_score=risk_score,
            risk_classification=risk_classification,
            total_findings=len(state["findings"]),
            critical_findings_text=critical_findings_text,
            high_findings_text=high_findings_text,
            all_findings_summary=all_findings_summary,
            total_cost=f"{state['total_cost_usd']:.6f}",
            analysis_date=datetime.now().isoformat()
        )
        
        try:
            # Reset cost tracking for this LLM call
            gemini_client.reset_cost_tracking()
            
            # Call LLM
            response = self.llm.invoke(prompt)
            
            # Get cost
            cost_summary = gemini_client.get_cost_summary()
            memo_cost = cost_summary.get('total_cost_usd', 0.0)
            
            # Update total cost
            new_total_cost = state["total_cost_usd"] + memo_cost
            state = update_state(state, "total_cost_usd", new_total_cost)
            
            # Extract memo text
            memo = response.content if hasattr(response, 'content') else str(response)
            
            return memo
            
        except Exception as e:
            # Fallback to template if LLM fails
            return self._generate_fallback_memo(
                filename=filename,
                risk_score=risk_score,
                risk_classification=risk_classification,
                grouped_findings=grouped_findings,
                total_cost=state["total_cost_usd"]
            )
    
    def _format_critical_findings(self, critical_findings: list) -> str:
        """Format critical findings for prompt"""
        if not critical_findings:
            return "None"
        
        text = ""
        for i, finding in enumerate(critical_findings, 1):
            text += f"{i}. [{finding.category}] {finding.description}\n"
            if finding.reasoning:
                text += f"   Reasoning: {finding.reasoning}\n"
        
        return text
    
    def _format_high_findings(self, high_findings: list) -> str:
        """Format high findings for prompt"""
        if not high_findings:
            return "None"
        
        text = ""
        for i, finding in enumerate(high_findings, 1):
            text += f"{i}. [{finding.category}] {finding.description}\n"
        
        return text
    
    def _format_all_findings_summary(self, grouped_findings: Dict) -> str:
        """Format summary of all findings"""
        summary = []
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = len(grouped_findings[severity])
            if count > 0:
                summary.append(f"- {severity}: {count} issue(s)")
        
        return "\n".join(summary) if summary else "No findings"
    
    def _generate_fallback_memo(
        self,
        filename: str,
        risk_score: int,
        risk_classification: str,
        grouped_findings: Dict,
        total_cost: float
    ) -> str:
        """Generate basic memo if LLM fails"""
        memo = f"""# Defense Memo: {filename}

## Executive Summary
Analysis completed with {risk_score}/100 risk score ({risk_classification} level).

## Risk Assessment
- **Overall Risk Score:** {risk_score}/100
- **Risk Classification:** {risk_classification}
- **Analysis Date:** {datetime.now().isoformat()}

## Critical Issues
"""
        
        if grouped_findings["CRITICAL"]:
            for finding in grouped_findings["CRITICAL"]:
                memo += f"\n### {finding.category}\n"
                memo += f"**Risk:** {finding.description}\n"
        else:
            memo += "No critical issues detected.\n"
        
        memo += f"\n---\n*Analysis Cost: ${total_cost:.6f} | Completed: {datetime.now().isoformat()}*\n"
        
        return memo


# Singleton instance
synthesis_agent = SynthesisAgent()
