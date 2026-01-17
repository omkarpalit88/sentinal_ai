"""
LangChain Tool Wrappers for Deterministic Tools with Gemini JSON Fix
Handles Gemini's double-wrapped JSON format issue
"""
import json
from typing import Any, Callable, Optional, Dict
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, validator

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
    """
    Flexible input schema for rules_tool - accepts multiple parameter name variations
    that Gemini might use
    """
    filename: Optional[str] = Field(None, description="Name of the SQL file to analyze")
    content: Optional[str] = Field(None, description="SQL file content to scan for dangerous patterns")
    
    # Gemini often uses these alternative names
    sql_content: Optional[str] = Field(None, description="Alternative name for SQL content")
    query: Optional[str] = Field(None, description="Alternative name for SQL content")
    sql: Optional[str] = Field(None, description="Alternative name for SQL content")
    code: Optional[str] = Field(None, description="Alternative name for SQL content")
    
    @validator('content', pre=True, always=True)
    def normalize_content(cls, v, values):
        """Accept content from any of the alternative field names"""
        if v:
            return v
        # Try alternative names in order of preference
        return (
            values.get('sql_content') or 
            values.get('query') or 
            values.get('sql') or 
            values.get('code')
        )
    
    @validator('filename', pre=True, always=True)
    def normalize_filename(cls, v, values):
        """Provide default filename if not specified"""
        return v or "gemini_input.sql"
    
    @validator('content')
    def content_required(cls, v):
        """Ensure we have content from somewhere"""
        if not v:
            raise ValueError("Content is required (tried: content, sql_content, query, sql, code)")
        return v
    
    class Config:
        extra = 'allow'  # Allow Gemini to send extra fields we don't use


class ParserToolInput(BaseModel):
    """
    Flexible input schema for parser_tool - accepts multiple parameter name variations
    """
    filename: Optional[str] = Field(None, description="Name of the SQL file to analyze")
    content: Optional[str] = Field(None, description="SQL file content to parse and extract entities")
    
    # Gemini alternatives
    sql_content: Optional[str] = Field(None, description="Alternative name for SQL content")
    query: Optional[str] = Field(None, description="Alternative name for SQL content")
    sql: Optional[str] = Field(None, description="Alternative name for SQL content")
    code: Optional[str] = Field(None, description="Alternative name for SQL content")
    
    @validator('content', pre=True, always=True)
    def normalize_content(cls, v, values):
        """Accept content from any of the alternative field names"""
        if v:
            return v
        return (
            values.get('sql_content') or 
            values.get('query') or 
            values.get('sql') or 
            values.get('code')
        )
    
    @validator('filename', pre=True, always=True)
    def normalize_filename(cls, v, values):
        """Provide default filename if not specified"""
        return v or "gemini_input.sql"
    
    @validator('content')
    def content_required(cls, v):
        """Ensure we have content from somewhere"""
        if not v:
            raise ValueError("Content is required (tried: content, sql_content, query, sql, code)")
        return v
    
    class Config:
        extra = 'allow'  # Allow Gemini to send extra fields



def create_gemini_safe_tool(
    name: str,
    description: str,
    func: Callable,
    args_schema: type[BaseModel]
) -> StructuredTool:
    """
    Create a LangChain tool that handles Gemini's JSON wrapping issue AND parameter remapping
    
    Args:
        name: Tool name
        description: Tool description
        func: Function to call
        args_schema: Pydantic model for arguments
        
    Returns:
        StructuredTool that unwraps Gemini JSON and remaps parameters
    """
    def wrapper(**kwargs):
        # File logging since LangChain swallows stdout
        import os
        log_file = "/tmp/gemini_tool_debug.log"
        
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Tool: {name}\n")
            f.write(f"Raw kwargs: {kwargs}\n")
        
        # Step 1: Unwrap any Gemini JSON wrapping
        unwrapped = unwrap_gemini_json(kwargs)
        
        with open(log_file, "a") as f:
            f.write(f"Unwrapped: {unwrapped}\n")
        
        # Step 2: Smart parameter remapping
        # Get expected field names from schema
        expected_fields = set(args_schema.__fields__.keys())
        provided_fields = set(unwrapped.keys())
        
        # If we have exact match, great!
        if expected_fields == provided_fields:
            with open(log_file, "a") as f:
                f.write(f"✅ Exact match! Calling function directly.\n")
            validated = args_schema(**unwrapped)
            return func(**validated.dict())
        
        # Otherwise, intelligently remap
        remapped = {}
        
        # Common remappings for SQL tools
        if 'filename' in expected_fields and 'filename' not in provided_fields:
            # Gemini didn't provide filename, generate one
            remapped['filename'] = "gemini_input.sql"
        
        if 'content' in expected_fields:
            # Try to find content in various possible field names
            for possible_content_field in ['content', 'sql_content', 'query', 'sql', 'code']:
                if possible_content_field in unwrapped:
                    remapped['content'] = unwrapped[possible_content_field]
                    break
            
            # If still not found, use the first non-filename field
            if 'content' not in remapped:
                for key, value in unwrapped.items():
                    if key != 'filename' and isinstance(value, str):
                        remapped['content'] = value
                        break
        
        # Copy any matching fields
        for field in expected_fields:
            if field in unwrapped:
                remapped[field] = unwrapped[field]
        
        with open(log_file, "a") as f:
            f.write(f"Expected: {list(expected_fields)}\n")
            f.write(f"Got: {list(provided_fields)}\n")
            f.write(f"Remapped: {remapped}\n")
        
        # Validate with Pydantic
        try:
            validated = args_schema(**remapped)
        except Exception as e:
            with open(log_file, "a") as f:
                f.write(f"❌ Validation error: {e}\n")
            raise
        
        with open(log_file, "a") as f:
            f.write(f"✅ Calling function with: {validated.dict()}\n")
        
        # Call the actual function with validated args
        result = func(**validated.dict())
        
        with open(log_file, "a") as f:
            f.write(f"Result preview: {result[:200] if isinstance(result, str) else result}...\n")
        
        return result

    
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



class SemanticToolInput(BaseModel):
    """
    Flexible input schema for semantic_tool - accepts multiple parameter name variations
    """
    filename: Optional[str] = Field(None, description="Name of the SQL file to analyze")
    content: Optional[str] = Field(None, description="SQL file content for semantic analysis")
    context: Optional[Dict] = Field(None, description="Optional context from parser tool")
    
    # Gemini alternatives
    sql_content: Optional[str] = Field(None, description="Alternative name for SQL content")
    query: Optional[str] = Field(None, description="Alternative name for SQL content")
    sql: Optional[str] = Field(None, description="Alternative name for SQL content")
    code: Optional[str] = Field(None, description="Alternative name for SQL content")
    
    @validator('content', pre=True, always=True)
    def normalize_content(cls, v, values):
        """Accept content from any of the alternative field names"""
        if v:
            return v
        return (
            values.get('sql_content') or 
            values.get('query') or 
            values.get('sql') or 
            values.get('code')
        )
    
    @validator('filename', pre=True, always=True)
    def normalize_filename(cls, v, values):
        """Provide default filename if not specified"""
        return v or "gemini_input.sql"
    
    @validator('content')
    def content_required(cls, v):
        """Ensure we have content from somewhere"""
        if not v:
            raise ValueError("Content is required (tried: content, sql_content, query, sql, code)")
        return v
    
    class Config:
        extra = 'allow'  # Allow Gemini to send extra fields


def semantic_tool_func(filename: str, content: str, context: Optional[Dict] = None) -> str:
    """
    Performs LLM-powered semantic analysis on SQL
    
    Args:
        filename: Name of SQL file
        content: SQL file content
        context: Optional context from parser tool
        
    Returns:
        Human-readable summary of semantic findings with cost info
    """
    from backend.tools.deterministic.semantic_tool import semantic_tool as semantic_tool_impl
    
    findings, cost = semantic_tool_impl.analyze(filename, content, context)
    
    if not findings:
        return f"✅ No semantic risks detected in {filename} by LLM analysis (Cost: ${cost:.6f})"
    
    result = f"LLM Semantic Analysis found {len(findings)} risk(s) in {filename}:\n\n"
    for i, finding in enumerate(findings, 1):
        result += f"{i}. [{finding.severity.value}] {finding.category}\n"
        result += f"   {finding.description}\n"
        result += f"   Reasoning: {finding.reasoning}\n"
        if finding.recommendation:
            result += f"   Recommendation: {finding.recommendation}\n"
        result += "\n"
    
    result += f"\n💰 LLM Cost: ${cost:.6f}"
    
    return result


# Create tools with wrapper that extracts only required fields
def make_rules_tool_wrapper(validated_input: RulesToolInput) -> str:
    """Wrapper that extracts only filename and content"""
    return rules_tool_func(
        filename=validated_input.filename,
        content=validated_input.content
    )

def make_parser_tool_wrapper(validated_input: ParserToolInput) -> str:
    """Wrapper that extracts only filename and content"""
    return parser_tool_func(
        filename=validated_input.filename,
        content=validated_input.content
    )

def make_semantic_tool_wrapper(validated_input: SemanticToolInput) -> str:
    """Wrapper that extracts filename, content, and optional context"""
    return semantic_tool_func(
        filename=validated_input.filename,
        content=validated_input.content,
        context=validated_input.context
    )

rules_tool = StructuredTool.from_function(
    func=make_rules_tool_wrapper,
    name="rules_tool",
    description=(
        "Scans SQL for dangerous patterns like DROP TABLE, TRUNCATE, unfiltered DELETE. "
        "Fast pattern matching using regex. Use this FIRST for quick risk detection."
    ),
    args_schema=RulesToolInput
)

parser_tool = StructuredTool.from_function(
    func=make_parser_tool_wrapper,
    name="parser_tool",
    description=(
        "Parses SQL using AST to extract tables and detect structural issues. "
        "Finds unfiltered DML, orphaned references, DDL/DML mixing. "
        "Use this for dependency analysis after initial pattern scan."
    ),
    args_schema=ParserToolInput
)

semantic_tool = StructuredTool.from_function(
    func=make_semantic_tool_wrapper,
    name="semantic_tool",
    description=(
        "LLM-powered deep semantic analysis of SQL for context-dependent risks. "
        "Detects business logic violations, implicit assumptions, data integrity issues, "
        "performance anti-patterns, and security risks. Use AFTER deterministic tools "
        "for comprehensive analysis or when deterministic tools find few issues."
    ),
    args_schema=SemanticToolInput
)

# Export tools list for agent
sql_analysis_tools = [rules_tool, parser_tool, semantic_tool]
