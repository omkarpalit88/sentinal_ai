"""
SQL Agent - LangChain Agent with Gemini LLM for autonomous tool selection
TRUE AGENTIC IMPLEMENTATION: LLM decides which tools to call based on findings
"""
from typing import List, Dict, Any
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.state import AnalysisState, File, Finding, AgentDecision, FileType, ConstraintLevel, add_finding, add_decision
from backend.tools.langchain_tools import sql_analysis_tools
from backend.config import settings
from backend.utils.gemini_client import gemini_client


# SQL Agent Prompt - Guides LLM on how to analyze SQL files
SQL_AGENT_PROMPT = """You are an expert SQL security analyst tasked with detecting deployment risks in SQL migration files.

Your goal: Identify dangerous patterns, structural issues, and potential data loss scenarios.

Available Tools:
{tools}

Tool Descriptions:
{tool_names}

Analysis Strategy:
1. ALWAYS start with rules_tool for fast pattern matching (DROP, TRUNCATE, etc.)
2. If rules_tool finds issues OR file is complex, use parser_tool for structural analysis
3. Combine findings from both tools for comprehensive assessment
4. Be cost-conscious: Skip redundant tool calls if findings are already clear

Important Guidelines:
- Prioritize CRITICAL and HIGH severity issues
- Consider context: migrations often have legitimate DROP statements
- Focus on unprotected operations (no WHERE clause, no IF EXISTS, etc.)
- Flag cross-cutting concerns (DDL + DML in same file)

Use this format for your analysis:

Question: What SQL file should I analyze?
Thought: I need to scan for dangerous patterns first using rules_tool
Action: rules_tool
Action Input: {{"filename": "example.sql", "content": "<sql content>"}}
Observation: <tool output>
Thought: Based on findings, I should check structure with parser_tool
Action: parser_tool
Action Input: {{"filename": "example.sql", "content": "<sql content>"}}
Observation: <tool output>
Thought: I now have enough information to provide final assessment
Final Answer: <comprehensive analysis summary>

Begin!

Question: {input}
Thought: {agent_scratchpad}"""


class SQLAgent:
    """
    SQL Agent using LangChain's ReAct framework with Gemini LLM.
    
    Architecture:
    - LLM Brain: Gemini 2.0 Flash (decides which tools to call)
    - Tools: rules_tool, parser_tool (deterministic analysis)
    - Framework: LangChain Agent (iterative reasoning with tools)
    
    The agent autonomously:
    1. Reads SQL file content
    2. Thinks about what tools would be helpful
    3. Calls tools based on its reasoning
    4. Aggregates findings
    5. Decides if more analysis is needed
    """
    
    def __init__(self):
        self.name = "sql_agent"
        self.llm = gemini_client.llm
        
        # Create prompt template
        prompt = PromptTemplate.from_template(SQL_AGENT_PROMPT)
        
        # Create ReAct agent with tools
        self.agent = create_react_agent(
            llm=self.llm,
            tools=sql_analysis_tools,
            prompt=prompt
        )
        
        # Wrap in executor for error handling and logging
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=sql_analysis_tools,
            verbose=settings.log_agent_decisions,
            max_iterations=settings.max_iterations_per_agent,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def process(self, state: AnalysisState) -> AnalysisState:
        """
        Main SQL agent processing logic using LangChain Agent
        
        Args:
            state: Current analysis state
            
        Returns:
            Updated state with findings and LLM decisions
        """
        # Get SQL files from state
        sql_files = [f for f in state.get("files", []) if f.file_type == FileType.SQL]
        
        if not sql_files:
            decision = AgentDecision(
                agent_name=self.name,
                decision="No SQL files to analyze",
                justification="No files with file_type=SQL in state"
            )
            state = add_decision(state, decision)
            return state
        
        # Process each SQL file with LangChain Agent
        for sql_file in sql_files:
            state = self._analyze_file_with_agent(state, sql_file)
        
        return state
    
    def _analyze_file_with_agent(self, state: AnalysisState, file: File) -> AnalysisState:
        """
        Analyze SQL file using LangChain Agent (LLM-driven tool selection)
        
        Args:
            state: Current state
            file: SQL file to analyze
            
        Returns:
            Updated state
        """
        filename = file.filename
        content = file.content
        
        # Log start
        decision = AgentDecision(
            agent_name=self.name,
            decision=f"Starting LLM-driven analysis of '{filename}'",
            justification="Using LangChain Agent with Gemini for autonomous tool selection"
        )
        state = add_decision(state, decision)
        
        try:
            # Invoke LangChain Agent - LLM autonomously decides which tools to call
            result = self.agent_executor.invoke({
                "input": f"Analyze this SQL file for deployment risks:\n\nFilename: {filename}\n\nContent:\n{content}"
            })
            
            # Log LLM's reasoning steps
            if result.get("intermediate_steps"):
                for step in result["intermediate_steps"]:
                    action, observation = step
                    decision = AgentDecision(
                        agent_name=self.name,
                        decision=f"LLM chose to call: {action.tool}",
                        tool_called=action.tool,
                        justification=f"LLM reasoning: {action.log}"
                    )
                    state = add_decision(state, decision)
            
            # Parse findings from tool outputs
            state = self._extract_findings_from_agent_output(state, filename, result)
            
            # Log completion
            decision = AgentDecision(
                agent_name=self.name,
                decision=f"Completed LLM analysis of '{filename}'",
                justification=f"Agent made {len(result.get('intermediate_steps', []))} autonomous tool calls"
            )
            state = add_decision(state, decision)
            
        except Exception as e:
            # Log error
            decision = AgentDecision(
                agent_name=self.name,
                decision=f"Error during LLM analysis of '{filename}'",
                justification=f"Error: {str(e)}"
            )
            state = add_decision(state, decision)
        
        return state
    
    def _extract_findings_from_agent_output(
        self, 
        state: AnalysisState, 
        filename: str, 
        agent_result: Dict[str, Any]
    ) -> AnalysisState:
        """
        Extract findings from agent's tool call results
        
        The agent calls tools which return findings. We need to collect those
        and add them to state.
        
        Args:
            state: Current state
            filename: File being analyzed
            agent_result: Result from agent_executor
            
        Returns:
            Updated state with findings
        """
        # Extract findings from intermediate steps
        for step in agent_result.get("intermediate_steps", []):
            action, observation = step
            tool_name = action.tool
            
            # Parse observations to extract severity indicators
            if any(keyword in observation for keyword in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]):
                # Create finding from LLM analysis
                # Determine severity from observation text
                if "CRITICAL" in observation:
                    severity = ConstraintLevel.CRITICAL
                elif "HIGH" in observation:
                    severity = ConstraintLevel.HIGH
                elif "MEDIUM" in observation:
                    severity = ConstraintLevel.MEDIUM
                else:
                    severity = ConstraintLevel.LOW
                
                # Extract category (simplified - in production would parse more carefully)
                category = "LLM_DETECTED_ISSUE"
                if "DROP" in observation:
                    category = "DROP_OPERATION"
                elif "DELETE" in observation:
                    category = "DELETE_OPERATION"
                elif "TRUNCATE" in observation:
                    category = "TRUNCATE_OPERATION"
                
                finding = Finding(
                    file_id=filename,
                    line_number=None,
                    severity=severity,
                    category=category,
                    description=f"{tool_name} via LLM: {observation[:200]}",
                    detected_by=f"{self.name}_llm",
                    reasoning=f"LLM analyzed using {tool_name}"
                )
                state = add_finding(state, finding)
        
        return state

# Factory function to create agent instance
def create_sql_agent() -> SQLAgent:
    """
    Create SQL Agent instance.
    Deferred creation to avoid API key check during module import.
    """
    return SQLAgent()
