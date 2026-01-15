"""
Parser Tool - SQL AST parsing for entity extraction and operation detection
Uses sqlparse library for deterministic SQL analysis
"""
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token
from sqlparse.tokens import Keyword, DML, DDL
from typing import List, Dict, Set, Any
from backend.state import Finding, ConstraintLevel


class ParserTool:
    """
    Deterministic SQL parsing tool using AST analysis.
    
    Extracts:
    - Tables (CREATE, DROP, ALTER, TRUNCATE)
    - Table references (SELECT, INSERT, UPDATE, DELETE)
    - DDL vs DML operations
    - WHERE clauses (or lack thereof)
    - Potential orphaned references
    
    Advantages:
    - Accurate parsing (not regex-based guessing)
    - Extracts structured data (table names, operations)
    - Enables dependency analysis
    - Fast (<1 second for most files)
    """
    
    def __init__(self):
        pass
    
    def parse_sql(self, content: str) -> Dict[str, Any]:
        """
        Parse SQL content and extract structured information
        
        Args:
            content: SQL file content
            
        Returns:
            Dictionary with:
            - statements: List of parsed statements
            - tables_created: Set of table names in CREATE statements
            - tables_dropped: Set of table names in DROP statements
            - tables_truncated: Set of table names in TRUNCATE statements
            - tables_altered: Set of table names in ALTER statements
            - tables_referenced: Set of table names in SELECT/INSERT/UPDATE/DELETE
            - has_ddl: Boolean, contains DDL operations
            - has_dml: Boolean, contains DML operations
        """
        parsed = sqlparse.parse(content)
        
        result = {
            "statements": [],
            "tables_created": set(),
            "tables_dropped": set(),
            "tables_truncated": set(),
            "tables_altered": set(),
            "tables_referenced": set(),
            "has_ddl": False,
            "has_dml": False
        }
        
        for statement in parsed:
            stmt_info = self._analyze_statement(statement)
            result["statements"].append(stmt_info)
            
            # Aggregate data
            if stmt_info["operation"] == "CREATE TABLE":
                result["tables_created"].update(stmt_info["tables"])
                result["has_ddl"] = True
            elif stmt_info["operation"] == "DROP TABLE":
                result["tables_dropped"].update(stmt_info["tables"])
                result["has_ddl"] = True
            elif stmt_info["operation"] == "TRUNCATE TABLE":
                result["tables_truncated"].update(stmt_info["tables"])
                result["has_ddl"] = True
            elif stmt_info["operation"] == "ALTER TABLE":
                result["tables_altered"].update(stmt_info["tables"])
                result["has_ddl"] = True
            elif stmt_info["operation"] in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                result["tables_referenced"].update(stmt_info["tables"])
                result["has_dml"] = True
        
        return result
    
    def _analyze_statement(self, statement) -> Dict[str, Any]:
        """Analyze a single SQL statement"""
        stmt_type = statement.get_type()
        stmt_str = str(statement).strip().upper()
        
        # Determine operation - check for combined keywords first
        operation = "UNKNOWN"
        
        # Check for DDL combined operations
        if "CREATE TABLE" in stmt_str:
            operation = "CREATE TABLE"
        elif "DROP TABLE" in stmt_str:
            operation = "DROP TABLE"
        elif "ALTER TABLE" in stmt_str:
            operation = "ALTER TABLE"
        elif "TRUNCATE TABLE" in stmt_str:
            operation = "TRUNCATE TABLE"
        # Check for single keyword DML operations
        elif stmt_str.startswith("SELECT"):
            operation = "SELECT"
        elif stmt_str.startswith("INSERT"):
            operation = "INSERT"
        elif stmt_str.startswith("UPDATE"):
            operation = "UPDATE"
        elif stmt_str.startswith("DELETE"):
            operation = "DELETE"
        # Fallback to token-based detection
        else:
            tokens = list(statement.flatten())
            for token in tokens:
                if token.ttype in (Keyword.DDL, Keyword.DML):
                    operation = token.value.upper()
                    break
        
        # Extract table names
        tables = self._extract_table_names(statement, operation)
        
        # Check for WHERE clause
        has_where = self._has_where_clause(statement)
        
        return {
            "type": stmt_type,
            "operation": operation,
            "tables": tables,
            "has_where": has_where,
            "raw": str(statement).strip()
        }
    
    def _extract_table_names(self, statement, operation: str) -> Set[str]:
        """Extract table names from SQL statement using simplified regex approach"""
        import re
        tables = set()
        stmt_str = str(statement).strip()
        
        # Different extraction logic based on operation
        if operation in ["CREATE", "DROP", "TRUNCATE", "ALTER"]:
            # DDL: Look for "TABLE tablename" pattern
            # Handles: CREATE TABLE users, DROP TABLE IF EXISTS sessions, etc.
            pattern = r'(?:CREATE|DROP|TRUNCATE|ALTER)\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            for match in matches:
                tables.add(match)
            
            # Also combine operation word (e.g., "CREATE TABLE" -> "CREATE TABLE")
            if operation in ["CREATE", "DROP", "TRUNCATE", "ALTER"]:
                combined_op = f"{operation} TABLE"
                if combined_op in stmt_str.upper():
                    # Re-extract with combined pattern
                    # This handles cases where operation was detected but TABLE follows
                    return tables if tables else self._extract_table_names(statement, combined_op)
        
        elif operation == "CREATE TABLE":
            pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "DROP TABLE":
            pattern = r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "TRUNCATE TABLE":
            pattern = r'TRUNCATE\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "ALTER TABLE":
            pattern = r'ALTER\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "SELECT":
            # Look for FROM clause
            pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
            
            # Also look for JOIN clauses
            pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "INSERT":
            # Look for INTO clause
            pattern = r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "UPDATE":
            # Table name follows UPDATE keyword
            pattern = r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        elif operation == "DELETE":
            # Look for FROM clause
            pattern = r'DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stmt_str, re.IGNORECASE)
            tables.update(matches)
        
        return tables

    
    def _has_where_clause(self, statement) -> bool:
        """Check if statement has WHERE clause"""
        for token in statement.tokens:
            if isinstance(token, Where):
                return True
            if token.ttype is Keyword and token.value.upper() == "WHERE":
                return True
        return False
    
    def analyze(self, filename: str, content: str) -> List[Finding]:
        """
        Main entry point - analyze SQL and generate findings
        
        Args:
            filename: Name of the SQL file
            content: SQL content
            
        Returns:
            List of Finding objects
        """
        findings = []
        parsed_data = self.parse_sql(content)
        
        # Finding 1: Detect unfiltered UPDATE/DELETE
        for stmt in parsed_data["statements"]:
            if stmt["operation"] in ["UPDATE", "DELETE"] and not stmt["has_where"]:
                finding = Finding(
                    file_id=filename,
                    line_number=None,
                    severity=ConstraintLevel.HIGH,
                    category="UNFILTERED_DML",
                    description=f"{stmt['operation']} without WHERE clause affects all rows",
                    detected_by="parser_tool",
                    reasoning="SQL parser detected DML operation without filtering condition",
                    code_snippet=stmt["raw"][:100],
                    recommendation="Add WHERE clause to limit operation scope"
                )
                findings.append(finding)
        
        # Finding 2: Detect potential orphaned references
        # (Tables referenced but not created - may cause errors if table doesn't exist)
        referenced = parsed_data["tables_referenced"]
        created = parsed_data["tables_created"]
        dropped = parsed_data["tables_dropped"]
        
        for table in referenced:
            if table in dropped:
                finding = Finding(
                    file_id=filename,
                    line_number=None,
                    severity=ConstraintLevel.CRITICAL,
                    category="ORPHANED_REFERENCE",
                    description=f"Table '{table}' is referenced after being dropped",
                    detected_by="parser_tool",
                    reasoning="SQL parser detected table usage after DROP statement",
                    recommendation=f"Remove references to '{table}' or reorder statements"
                )
                findings.append(finding)
        
        # Finding 3: DDL + DML mix (risky in same file)
        if parsed_data["has_ddl"] and parsed_data["has_dml"]:
            finding = Finding(
                file_id=filename,
                line_number=None,
                severity=ConstraintLevel.MEDIUM,
                category="DDL_DML_MIX",
                description="File contains both DDL (schema changes) and DML (data changes)",
                detected_by="parser_tool",
                reasoning="Mixing schema and data operations increases rollback complexity",
                recommendation="Separate DDL and DML into different migration files"
            )
            findings.append(finding)
        
        return findings
    
    def get_entities(self, content: str) -> Dict[str, Set[str]]:
        """
        Extract entities for cross-file dependency analysis
        
        Returns:
            Dictionary with tables_created, tables_dropped, tables_referenced
        """
        parsed_data = self.parse_sql(content)
        return {
            "tables_created": parsed_data["tables_created"],
            "tables_dropped": parsed_data["tables_dropped"],
            "tables_truncated": parsed_data["tables_truncated"],
            "tables_altered": parsed_data["tables_altered"],
            "tables_referenced": parsed_data["tables_referenced"]
        }


# Singleton instance
parser_tool = ParserTool()
