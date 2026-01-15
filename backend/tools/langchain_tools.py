"""
LangChain Tool Wrappers for Deterministic Tools with Gemini JSON Fix
Handles Gemini's double-wrapped JSON format issue
"""
import json
from typing import Any, Callable
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.tools.deterministic.rules_tool import rules_tool as rules_tool_impl
from backend.tools.deterministic.parser_tool import parser_tool as parser_tool_impl
from backend.state import Finding


def unwrap_gemini_json(raw_input: Any) -> dict:
    """
    Unwrap Gemini's double-wrapped JSON format.
    
    Gemini sometimes wraps the entire JSON in quotes:
    {"filename": "{\"filename\": \"test.sql\", \"content\": \"...\"}"}
    
    This function detects and unwraps it to:
    {"filename": "test.sql", "content": "..."}
    """
    # If it's already a dict, return as-is
    if isinstance(raw_input, dict):
        # Check if any value is a JSON string that should be unwrapped
        for key, value in raw_input.items():
            if isinstance(value, str) and value.startswith('{'):
                try:
                    # Try to parse as JSON
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        # This was a wrapped JSON! Return the unwrapped version
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
        return raw_input
    
    # If it's a string, try to parse it
    if isinstance(raw_input, str):
        try:
            return json.loads(raw_input)
        except (json.JSONDecodeError, ValueError):
            return {"error": "Invalid JSON format"}
    
    return raw_input


class RulesToolInput(BaseModel):
    """Input schema for rules_tool"""
    filename: str = Field(description="Name of the SQL file to analyze")
    content: str = Field(description="SQL file content to scan for dangerous patterns")


class ParserToolInput(BaseModel):
    """Input schema for parser_tool"""
    filename: str = Field(description="Name of the SQL file to analyze")
    content: str = Field(description="SQL file content to parse and extract entities")


def create_gemini_safe_tool(
    name: str,
    description: str,
    func: Callable,
    args_schema: type[BaseModel]
) -> StructuredTool:
    """
    Create a LangChain tool that handles Gemini's JSON wrapping issue
    
    Args:
        name: Tool name
        description: Tool description
        func: Function to call
        args_schema: Pydantic model for arguments
        
    Returns:
        StructuredTool that unwraps Gemini JSON before validation
    """
    def wrapper(**kwargs):
        # Debug: Print what Gemini sends
        print(f"\n🔍 Raw input to {name}: {kwargs}\n")
        
        # Unwrap any Gemini JSON wrapping
        unwrapped = unwrap_gemini_json(kwargs)
        
        print(f"🔄 After unwrapping: {unwrapped}\n")
        
        # Validate with Pydantic
        try:
            validated = args_schema(**unwrapped)
        except Exception as e:
            print(f"❌ Validation error: {e}")
            print(f"   Expected fields: {list(args_schema.__fields__.keys())}")
            print(f"   Got fields: {list(unwrapped.keys())}")
            raise
        
        # Call the actual function with validated args
        return func(**validated.dict())
    
    return StructuredTool.from_function(
        func=wrapper,
        name=name,
        description=description,
        args_schema=args_schema
    )


def rules_tool_func(filename: str, content: str) -> str:
    """
    Scans SQL for dangerous patterns using regex-based veto rules.
    
    Args:
        filename: Name of SQL file
        content: SQL file content
        
    Returns:
        Human-readable summary of findings
    """
    findings = rules_tool_impl.analyze(filename, content, "sql")
    
    if not findings:
        return f"✅ No dangerous patterns detected in {filename}"
    
    result = f"Found {len(findings)} issue(s) in {filename}:\n\n"
    for i, finding in enumerate(findings, 1):
        result += f"{i}. [{finding.severity.value}] {finding.category}\n"
        result += f"   Line {finding.line_number}: {finding.description}\n"
        result += f"   Recommendation: {finding.recommendation}\n\n"
    
    return result


def parser_tool_func(filename: str, content: str) -> str:
    """
    Parses SQL using AST to extract tables and detect structural issues.
    
    Args:
        filename: Name of SQL file
        content: SQL file content
        
    Returns:
        Human-readable summary of structure and findings
    """
    findings = parser_tool_impl.analyze(filename, content)
    entities = parser_tool_impl.get_entities(content)
    
    result = f"SQL Structure Analysis for {filename}:\n\n"
    
    if entities["tables_created"]:
        result += f"📝 Tables Created: {', '.join(entities['tables_created'])}\n"
    if entities["tables_dropped"]:
        result += f"🗑️  Tables Dropped: {', '.join(entities['tables_dropped'])}\n"
    if entities["tables_truncated"]:
        result += f"⚠️  Tables Truncated: {', '.join(entities['tables_truncated'])}\n"
    if entities["tables_referenced"]:
        result += f"🔗 Tables Referenced: {', '.join(entities['tables_referenced'])}\n"
    
    result += "\n"
    
    if not findings:
        result += "✅ No structural issues detected"
    else:
        result += f"Found {len(findings)} structural issue(s):\n\n"
        for i, finding in enumerate(findings, 1):
            result += f"{i}. [{finding.severity.value}] {finding.category}\n"
            result += f"   {finding.description}\n"
            result += f"   Recommendation: {finding.recommendation}\n\n"
    
    return result


# Create Gemini-safe tools
rules_tool = create_gemini_safe_tool(
    name="rules_tool",
    description=(
        "Scans SQL for dangerous patterns like DROP TABLE, TRUNCATE, unfiltered DELETE. "
        "Fast pattern matching using regex. Use this FIRST for quick risk detection."
    ),
    func=rules_tool_func,
    args_schema=RulesToolInput
)

parser_tool = create_gemini_safe_tool(
    name="parser_tool",
    description=(
        "Parses SQL using AST to extract tables and detect structural issues. "
        "Finds unfiltered DML, orphaned references, DDL/DML mixing. "
        "Use this for dependency analysis after initial pattern scan."
    ),
    func=parser_tool_func,
    args_schema=ParserToolInput
)

# Export tools list for agent
sql_analysis_tools = [rules_tool, parser_tool]
