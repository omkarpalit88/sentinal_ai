"""
Unit tests for Sub-Phase 1.2: Deterministic Tools
Tests rules_tool, parser_tool, and dependency_tool
"""
import pytest
from backend.tools.deterministic.rules_tool import RulesTool
from backend.tools.deterministic.parser_tool import ParserTool
from backend.tools.deterministic.dependency_tool import DependencyTool
from backend.state import ConstraintLevel


class TestRulesTool:
    """Test Rules Tool (pattern matching)"""
    
    def test_sql_drop_table(self):
        tool = RulesTool()
        content = "DROP TABLE users;"
        findings = tool.analyze_sql("test.sql", content)
        
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.HIGH
        assert findings[0].category == "DROP_TABLE"
        assert findings[0].detected_by == "rules_tool"
    
    def test_sql_drop_database(self):
        tool = RulesTool()
        content = "DROP DATABASE production;"
        findings = tool.analyze_sql("test.sql", content)
        
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.CRITICAL
        assert findings[0].category == "DROP_DATABASE"
    
    def test_sql_truncate_table(self):
        tool = RulesTool()
        content = "TRUNCATE TABLE sessions;"
        findings = tool.analyze_sql("test.sql", content)
        
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.CRITICAL
        assert findings[0].category == "TRUNCATE_TABLE"
    
    def test_sql_unfiltered_delete(self):
        tool = RulesTool()
        content = "DELETE FROM users;"
        findings = tool.analyze_sql("test.sql", content)
        
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.HIGH
        assert findings[0].category == "UNFILTERED_DELETE"
    
    def test_sql_safe_query(self):
        tool = RulesTool()
        content = "SELECT * FROM users WHERE id = 1;"
        findings = tool.analyze_sql("test.sql", content)
        
        assert len(findings) == 0
    
    def test_sql_multiple_violations(self):
        tool = RulesTool()
        content = """
        DROP TABLE users;
        TRUNCATE TABLE sessions;
        DELETE FROM logs;
        """
        findings = tool.analyze_sql("test.sql", content)
        
        assert len(findings) == 3
        severities = [f.severity for f in findings]
        assert ConstraintLevel.HIGH in severities
        assert ConstraintLevel.CRITICAL in severities
    
    def test_terraform_force_destroy(self):
        tool = RulesTool()
        content = """
        resource "aws_s3_bucket" "data" {
          bucket = "my-bucket"
          force_destroy = true
        }
        """
        findings = tool.analyze_terraform("main.tf", content)
        
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.CRITICAL
        assert findings[0].category == "FORCE_DESTROY"
    
    def test_yaml_zero_replicas(self):
        tool = RulesTool()
        content = """
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: web
        spec:
          replicas: 0
        """
        findings = tool.analyze_yaml("deployment.yaml", content)
        
        assert len(findings) == 1
        assert findings[0].severity == ConstraintLevel.HIGH
        assert findings[0].category == "ZERO_REPLICAS"
    
    def test_analyze_dispatcher_sql(self):
        tool = RulesTool()
        content = "DROP TABLE users;"
        findings = tool.analyze("test.sql", content, "sql")
        
        assert len(findings) == 1
        assert findings[0].category == "DROP_TABLE"
    
    def test_analyze_unknown_type(self):
        tool = RulesTool()
        content = "some content"
        findings = tool.analyze("test.txt", content, "unknown")
        
        assert len(findings) == 0


class TestParserTool:
    """Test Parser Tool (SQL AST parsing)"""
    
    def test_parse_create_table(self):
        tool = ParserTool()
        content = "CREATE TABLE users (id INT, name VARCHAR(100));"
        parsed = tool.parse_sql(content)
        
        assert "users" in parsed["tables_created"]
        assert parsed["has_ddl"] is True
        assert parsed["has_dml"] is False
    
    def test_parse_drop_table(self):
        tool = ParserTool()
        content = "DROP TABLE sessions;"
        parsed = tool.parse_sql(content)
        
        assert "sessions" in parsed["tables_dropped"]
        assert parsed["has_ddl"] is True
    
    def test_parse_select(self):
        tool = ParserTool()
        content = "SELECT * FROM users WHERE id = 1;"
        parsed = tool.parse_sql(content)
        
        assert "users" in parsed["tables_referenced"]
        assert parsed["has_dml"] is True
        assert parsed["has_ddl"] is False
    
    def test_parse_insert(self):
        tool = ParserTool()
        content = "INSERT INTO logs (message) VALUES ('test');"
        parsed = tool.parse_sql(content)
        
        assert "logs" in parsed["tables_referenced"]
        assert parsed["has_dml"] is True
    
    def test_parse_update_with_where(self):
        tool = ParserTool()
        content = "UPDATE users SET name = 'John' WHERE id = 1;"
        parsed = tool.parse_sql(content)
        
        assert "users" in parsed["tables_referenced"]
        assert len(parsed["statements"]) == 1
        assert parsed["statements"][0]["has_where"] is True
    
    def test_parse_update_without_where(self):
        tool = ParserTool()
        content = "UPDATE users SET active = 1;"
        parsed = tool.parse_sql(content)
        
        assert parsed["statements"][0]["has_where"] is False
    
    def test_analyze_unfiltered_delete(self):
        tool = ParserTool()
        content = "DELETE FROM sessions;"
        findings = tool.analyze("test.sql", content)
        
        assert len(findings) >= 1
        # Should detect UNFILTERED_DML
        unfiltered = [f for f in findings if f.category == "UNFILTERED_DML"]
        assert len(unfiltered) == 1
        assert unfiltered[0].severity == ConstraintLevel.HIGH
    
    def test_analyze_orphaned_reference(self):
        tool = ParserTool()
        content = """
        DROP TABLE users;
        SELECT * FROM users;
        """
        findings = tool.analyze("test.sql", content)
        
        # Should detect ORPHANED_REFERENCE
        orphaned = [f for f in findings if f.category == "ORPHANED_REFERENCE"]
        assert len(orphaned) == 1
        assert orphaned[0].severity == ConstraintLevel.CRITICAL
        assert "users" in orphaned[0].description
    
    def test_analyze_ddl_dml_mix(self):
        tool = ParserTool()
        content = """
        CREATE TABLE logs (id INT);
        INSERT INTO logs VALUES (1);
        """
        findings = tool.analyze("test.sql", content)
        
        # Should detect DDL_DML_MIX
        mixed = [f for f in findings if f.category == "DDL_DML_MIX"]
        assert len(mixed) == 1
        assert mixed[0].severity == ConstraintLevel.MEDIUM
    
    def test_get_entities(self):
        tool = ParserTool()
        content = """
        CREATE TABLE users (id INT);
        DROP TABLE sessions;
        SELECT * FROM logs;
        """
        entities = tool.get_entities(content)
        
        assert "users" in entities["tables_created"]
        assert "sessions" in entities["tables_dropped"]
        assert "logs" in entities["tables_referenced"]


class TestDependencyTool:
    """Test Dependency Tool (cross-file analysis)"""
    
    def test_build_graph(self):
        tool = DependencyTool()
        file_entities = {
            "file1.sql": {
                "tables_created": {"users"},
                "tables_referenced": set()
            },
            "file2.sql": {
                "tables_created": set(),
                "tables_referenced": {"users"}
            }
        }
        tool.build_graph(file_entities)
        
        assert "file2.sql" in tool.dependency_graph
        assert "users" in tool.dependency_graph["file2.sql"]
    
    def test_detect_positive_dependency(self):
        tool = DependencyTool()
        file_entities = {
            "001_create_users.sql": {
                "tables_created": {"users"},
                "tables_referenced": set(),
                "tables_dropped": set()
            },
            "002_add_data.sql": {
                "tables_created": set(),
                "tables_referenced": {"users"},
                "tables_dropped": set()
            }
        }
        deps = tool.detect_cross_file_dependencies(file_entities)
        
        # Should detect positive dependency
        creation_deps = [d for d in deps if d.dependency_type == "TABLE_CREATION"]
        assert len(creation_deps) == 1
        assert creation_deps[0].risk_level == ConstraintLevel.INFO
        assert "users" in creation_deps[0].description
    
    def test_detect_drop_conflict(self):
        tool = DependencyTool()
        file_entities = {
            "file1.sql": {
                "tables_created": set(),
                "tables_referenced": {"users"},
                "tables_dropped": set()
            },
            "file2.sql": {
                "tables_created": set(),
                "tables_referenced": set(),
                "tables_dropped": {"users"}
            }
        }
        deps = tool.detect_cross_file_dependencies(file_entities)
        
        # Should detect CRITICAL conflict
        conflicts = [d for d in deps if d.dependency_type == "TABLE_DROP_CONFLICT"]
        assert len(conflicts) == 1
        assert conflicts[0].risk_level == ConstraintLevel.CRITICAL
        assert "users" in conflicts[0].description
    
    def test_validate_execution_order_correct(self):
        tool = DependencyTool()
        file_entities = {
            "001_create.sql": {
                "tables_created": {"users"},
                "tables_referenced": set(),
                "tables_dropped": set(),
                "tables_altered": set(),
                "tables_truncated": set()
            },
            "002_insert.sql": {
                "tables_created": set(),
                "tables_referenced": {"users"},
                "tables_dropped": set(),
                "tables_altered": set(),
                "tables_truncated": set()
            }
        }
        files = ["001_create.sql", "002_insert.sql"]
        violations = tool.validate_execution_order(files, file_entities)
        
        # No violations for correct order
        assert len(violations) == 0
    
    def test_validate_execution_order_violation(self):
        tool = DependencyTool()
        file_entities = {
            "001_insert.sql": {
                "tables_created": set(),
                "tables_referenced": {"users"},
                "tables_dropped": set(),
                "tables_altered": set(),
                "tables_truncated": set()
            },
            "002_create.sql": {
                "tables_created": {"users"},
                "tables_referenced": set(),
                "tables_dropped": set(),
                "tables_altered": set(),
                "tables_truncated": set()
            }
        }
        files = ["001_insert.sql", "002_create.sql"]
        violations = tool.validate_execution_order(files, file_entities)
        
        # Should detect order violation
        assert len(violations) >= 1
        assert violations[0].risk_level == ConstraintLevel.HIGH
        assert violations[0].dependency_type == "EXECUTION_ORDER_VIOLATION"
    
    def test_suggest_execution_order(self):
        tool = DependencyTool()
        file_entities = {
            "create_tables.sql": {
                "tables_created": {"users", "logs"},
                "tables_referenced": set()
            },
            "insert_data.sql": {
                "tables_created": set(),
                "tables_referenced": {"users", "logs"}
            },
            "mixed.sql": {
                "tables_created": {"sessions"},
                "tables_referenced": {"users"}
            }
        }
        suggested, reasoning = tool.suggest_execution_order(file_entities)
        
        # create_tables should be first (creates but doesn't reference)
        assert suggested[0] == "create_tables.sql"
        # insert_data should be last (references but doesn't create)
        assert suggested[-1] == "insert_data.sql"
        # Reasoning should be present
        assert len(reasoning) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
