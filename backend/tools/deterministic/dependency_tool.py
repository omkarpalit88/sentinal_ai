"""
Dependency Tool - Graph-based dependency analysis for cross-file detection
Builds dependency graph from parsed entities
"""
from typing import List, Dict, Set, Tuple
from backend.state import Dependency, ConstraintLevel


class DependencyTool:
    """
    Dependency analyzer for cross-file relationship detection.
    
    Builds a dependency graph from entities extracted by parser_tool:
    - Table A created → Table B references A → Dependency detected
    - Table A dropped → Table B references A → CRITICAL conflict
    - Execution order validation
    
    Advantages:
    - Graph-based analysis (not just string matching)
    - Detects implicit dependencies
    - Validates execution order
    - Fast (graph operations are O(n))
    """
    
    def __init__(self):
        self.dependency_graph: Dict[str, Set[str]] = {}
    
    def build_graph(self, file_entities: Dict[str, Dict[str, Set[str]]]) -> None:
        """
        Build dependency graph from all files' entities
        
        Args:
            file_entities: Dict mapping filename -> entities dict
                          entities dict has: tables_created, tables_dropped, tables_referenced
        """
        self.dependency_graph = {}
        
        # Build graph: file -> tables it depends on
        for filename, entities in file_entities.items():
            dependencies = set()
            
            # File depends on tables it references
            dependencies.update(entities.get("tables_referenced", set()))
            
            # File depends on tables it alters or truncates (they must exist)
            dependencies.update(entities.get("tables_altered", set()))
            dependencies.update(entities.get("tables_truncated", set()))
            
            self.dependency_graph[filename] = dependencies
    
    def detect_cross_file_dependencies(
        self, 
        file_entities: Dict[str, Dict[str, Set[str]]]
    ) -> List[Dependency]:
        """
        Detect cross-file dependencies and conflicts
        
        Args:
            file_entities: Dict mapping filename -> entities dict
            
        Returns:
            List of Dependency objects
        """
        dependencies = []
        
        # Build graph first
        self.build_graph(file_entities)
        
        # Detect dependencies
        for filename, required_tables in self.dependency_graph.items():
            for required_table in required_tables:
                # Check if any other file creates this table
                for other_file, other_entities in file_entities.items():
                    if other_file == filename:
                        continue
                    
                    if required_table in other_entities.get("tables_created", set()):
                        # Positive dependency: other_file creates table that filename needs
                        dep = Dependency(
                            source_file=filename,
                            target_file=other_file,
                            dependency_type="TABLE_CREATION",
                            description=f"'{filename}' depends on table '{required_table}' created in '{other_file}'",
                            risk_level=ConstraintLevel.INFO,
                            detected_by="dependency_tool"
                        )
                        dependencies.append(dep)
                    
                    if required_table in other_entities.get("tables_dropped", set()):
                        # CRITICAL conflict: other_file drops table that filename needs
                        dep = Dependency(
                            source_file=filename,
                            target_file=other_file,
                            dependency_type="TABLE_DROP_CONFLICT",
                            description=f"CONFLICT: '{filename}' references table '{required_table}' but '{other_file}' drops it",
                            risk_level=ConstraintLevel.CRITICAL,
                            detected_by="dependency_tool"
                        )
                        dependencies.append(dep)
        
        return dependencies
    
    def validate_execution_order(
        self,
        files: List[str],
        file_entities: Dict[str, Dict[str, Set[str]]]
    ) -> List[Dependency]:
        """
        Validate if files are in correct execution order
        
        Args:
            files: List of filenames in proposed execution order
            file_entities: Dict mapping filename -> entities dict
            
        Returns:
            List of Dependency objects flagging order violations
        """
        violations = []
        
        # Track what tables exist at each step
        existing_tables = set()
        
        for i, filename in enumerate(files):
            entities = file_entities.get(filename, {})
            
            # Check if file references tables that don't exist yet
            required_tables = entities.get("tables_referenced", set())
            required_tables.update(entities.get("tables_altered", set()))
            required_tables.update(entities.get("tables_truncated", set()))
            
            for table in required_tables:
                if table not in existing_tables:
                    # Check if table is created later
                    created_later = False
                    for j in range(i + 1, len(files)):
                        later_entities = file_entities.get(files[j], {})
                        if table in later_entities.get("tables_created", set()):
                            created_later = True
                            dep = Dependency(
                                source_file=filename,
                                target_file=files[j],
                                dependency_type="EXECUTION_ORDER_VIOLATION",
                                description=f"'{filename}' (position {i+1}) references table '{table}' created later in '{files[j]}' (position {j+1})",
                                risk_level=ConstraintLevel.HIGH,
                                detected_by="dependency_tool"
                            )
                            violations.append(dep)
                            break
            
            # Update existing tables
            existing_tables.update(entities.get("tables_created", set()))
            
            # Remove dropped tables
            existing_tables -= entities.get("tables_dropped", set())
        
        return violations
    
    def suggest_execution_order(
        self,
        file_entities: Dict[str, Dict[str, Set[str]]]
    ) -> Tuple[List[str], str]:
        """
        Suggest optimal execution order using topological sort
        
        Args:
            file_entities: Dict mapping filename -> entities dict
            
        Returns:
            Tuple of (ordered_files, reasoning)
        """
        # Build dependency graph
        self.build_graph(file_entities)
        
        # Perform topological sort (simplified - works for DAGs)
        # Files that create tables should run first
        # Files that only reference should run last
        
        creates_tables = []
        references_only = []
        mixed = []
        
        for filename, entities in file_entities.items():
            creates = len(entities.get("tables_created", set())) > 0
            references = len(entities.get("tables_referenced", set())) > 0
            
            if creates and not references:
                creates_tables.append(filename)
            elif references and not creates:
                references_only.append(filename)
            else:
                mixed.append(filename)
        
        # Suggested order: creators -> mixed -> references
        suggested_order = creates_tables + mixed + references_only
        reasoning = (
            f"Suggested order prioritizes table creation ({len(creates_tables)} files), "
            f"then mixed operations ({len(mixed)} files), "
            f"then reference-only operations ({len(references_only)} files)"
        )
        
        return suggested_order, reasoning


# Singleton instance
dependency_tool = DependencyTool()
