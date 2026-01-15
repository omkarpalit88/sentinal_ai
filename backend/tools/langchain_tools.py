"""
LangChain Tool Wrappers for Deterministic Tools
Converts our deterministic tools to LangChain Tool format
"""
from typing import List, Dict, Optional
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.tools.deterministic.rules_tool import rules_tool as rules_tool_impl
from backend.tools.deterministic.parser_tool import parser_tool as parser_tool_impl
from backend.state import Finding


# Input schemas for LangChain tools
class RulesToolInput(BaseModel):
    """Input schema for rules_tool"""
    filename: str = Field(description="Name of the SQL file to analyze")
    content: str = Field(description="SQL file content to scan for dangerous patterns")


class ParserToolInput(BaseModel):
    """Input schema for parser_tool"""
    filename: str = Field(description="Name of the SQL file to analyze")
    content: str = Field(description="SQL file content to parse and extract entities")


# Tool wrapper functions
def rules_tool_func(filename: str, content: str) -> str:
    """
    Scans SQL for dangerous patterns using regex-based veto rules.
    
    Detects: DROP TABLE, DROP DATABASE, TRUNCATE, unfiltered DELETE/UPDATE.
    Fast (<1s), deterministic, never hallucinates.
    Use this FIRST for quick pattern matching.
    
    Args:
        filename: Name of SQL file
        content: SQL file content
        
    Returns:
        Human-readable summary of findings with severity levels
    """
    findings = rules_tool_impl.analyze(filename, content, "sql")
    
    if not findings:
        return f"✅ No dangerous patterns detected in {filename}"
    
    # Format findings for LLM
    result = f"Found {len(findings)} issue(s) in {filename}:\n\n"
    for i, finding in enumerate(findings, 1):
        result += f"{i}. [{finding.severity.value}] {finding.category}\n"
        result += f"   Line {finding.line_number}: {finding.description}\n"
        result += f"   Recommendation: {finding.recommendation}\n\n"
    
    return result


def parser_tool_func(filename: str, content: str) -> str:
    """
    Parses SQL using AST to extract tables and detect structural issues.
    
    Detects: Unfiltered DML, orphaned references, DDL/DML mixing.
    Extracts: Tables created, dropped, truncated, referenced.
    Use this for dependency analysis and entity extraction.
    
    Args:
        filename: Name of SQL file
        content: SQL file content
        
    Returns:
        Human-readable summary of structure and findings
    """
    # Get findings
    findings = parser_tool_impl.analyze(filename, content)
    
    # Get entities
    entities = parser_tool_impl.get_entities(content)
    
    # Format results
    result = f"SQL Structure Analysis for {filename}:\n\n"
    
    # Report entities
    if entities["tables_created"]:
        result += f"📝 Tables Created: {', '.join(entities['tables_created'])}\n"
    if entities["tables_dropped"]:
        result += f"🗑️  Tables Dropped: {', '.join(entities['tables_dropped'])}\n"
    if entities["tables_truncated"]:
        result += f"⚠️  Tables Truncated: {', '.join(entities['tables_truncated'])}\n"
    if entities["tables_referenced"]:
        result += f"🔗 Tables Referenced: {', '.join(entities['tables_referenced'])}\n"
    
    result += "\n"
    
    # Report findings
    if not findings:
        result += "✅ No structural issues detected"
    else:
        result += f"Found {len(findings)} structural issue(s):\n\n"
        for i, finding in enumerate(findings, 1):
            result += f"{i}. [{finding.severity.value}] {finding.category}\n"
            result += f"   {finding.description}\n"
            result += f"   Recommendation: {finding.recommendation}\n\n"
    
    return result


# Create LangChain StructuredTools
rules_tool = StructuredTool.from_function(
    func=rules_tool_func,
    name="rules_tool",
    description=(
        "Scans SQL for dangerous patterns like DROP TABLE, TRUNCATE, unfiltered DELETE. "
        "Fast pattern matching using regex. Use this FIRST for quick risk detection."
    ),
    args_schema=RulesToolInput
)

parser_tool = StructuredTool.from_function(
    func=parser_tool_func,
    name="parser_tool",
    description=(
        "Parses SQL using AST to extract tables and detect structural issues. "
        "Finds unfiltered DML, orphaned references, DDL/DML mixing. "
        "Use this for dependency analysis after initial pattern scan."
    ),
    args_schema=ParserToolInput
)


# Export tools list for agent
sql_analysis_tools = [rules_tool, parser_tool]
