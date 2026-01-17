"""
SQL Agent - Agentic implementation with LangChain + Structured Data
LLM autonomously decides which tools to call, findings added as structured objects
"""
from typing import List, Dict, Any
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from backend.state import AnalysisState, File, Finding, AgentDecision, FileType, ConstraintLevel, add_finding, add_decision
from backend.tools.deterministic.rules_tool import rules_tool
from backend.tools.deterministic.parser_tool import parser_tool
from backend.config import settings
from backend.utils.gemini_client import gemini_client


# SQL Agent Prompt
SQL_AGENT_PROMPT = """You are an expert SQL security analyst detecting deployment risks.

Your goal: Identify dangerous patterns, structural issues, and data loss scenarios.

Available tools:
{tools}

Use this format:
Question: the input question
Thought: think about what to do
Action: one of [{tool_names}]
Action Input: JSON parameters for the action
Observation: result of the action
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: summary of your analysis

Strategy:
1. ALWAYS start with rules_tool (fast pattern matching)
2. Then use parser_tool (structural analysis)
3. Optionally use semantic_tool if complex patterns found

Guidelines:
- Prioritize CRITICAL and HIGH severity
- Be cost-conscious with semantic_tool

Question: {input}
Thought:{agent_scratchpad}"""


class SQLAgent:
    """
    Agentic SQL Agent using LangChain ReAct framework.
    
    Architecture:
    - LLM Brain: Gemini decides which tools to call autonomously
    - Tools: Return text summaries (for LLM observation)
    - Findings: Extracted as structured objects and added to state
    
    Key Fix: Tools called by LLM, but we capture structured findings
    directly from tool implementations, not by parsing LLM observations.
    """
    
    def __init__(self):
        self.name = "sql_agent"
        self.llm = gemini_client.llm
        
        # Import LangChain tool wrappers
        from backend.tools.langchain_tools import sql_analysis_tools
        
        prompt = PromptTemplate.from_template(SQL_AGENT_PROMPT)
        
        self.agent = create_react_agent(
            llm=self.llm,
            tools=sql_analysis_tools,
            prompt=prompt
        )
        
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
        Analyze SQL file using LangChain Agent (agentic tool selection)
        + Direct structured finding extraction (no text parsing)
        
        Hybrid Approach:
        1. LLM autonomously decides which tools to call (via LangChain)
        2. We track which tools were called
        3. We directly call those tools again to get structured Finding objects
        4. Findings added to state as structured data (no parsing)
        
        Args:
            state: Current state
            file: SQL file to analyze
            
        Returns:
            Updated state with findings
        """
        filename = file.filename
        content = file.content
        
        # Log start
        decision = AgentDecision(
            agent_name=self.name,
            decision=f"Starting agentic analysis of '{filename}'",
            justification="Using LangChain Agent with Gemini for autonomous tool selection"
        )
        state = add_decision(state, decision)
        
        try:
            # Step 1: Let LLM agent decide which tools to call
            result = self.agent_executor.invoke({
                "input": f"Analyze this SQL file for deployment risks:\n\nFilename: {filename}\n\nContent:\n{content}"
            })
            
            # Step 2: Track which tools the LLM decided to call
            tools_called = []
            if result.get("intermediate_steps"):
                for step in result["intermediate_steps"]:
                    action, observation = step
                    tools_called.append(action.tool)
                    
                    decision = AgentDecision(
                        agent_name=self.name,
                        decision=f"LLM chose to call: {action.tool}",
                        tool_called=action.tool,
                        justification=f"Autonomous reasoning led to this tool choice"
                    )
                    state = add_decision(state, decision)
            
            # Step 3: Extract structured findings directly from tools
            # (not by parsing LLM observations)
            
            if "rules_tool" in tools_called:
                rules_findings = rules_tool.analyze(filename, content, "sql")
                for finding in rules_findings:
                    state = add_finding(state, finding)
            
            if "parser_tool" in tools_called:
                parser_findings = parser_tool.analyze(filename, content)
                for finding in parser_findings:
                    state = add_finding(state, finding)
            
            # semantic_tool findings would be handled here if called
            # (not implemented in Phase 1)
            
            # Log completion
            total_findings = len(state.get("findings", []))
            decision = AgentDecision(
                agent_name=self.name,
                decision=f"Completed agentic analysis of '{filename}'",
                justification=f"LLM made {len(tools_called)} tool decisions. Total findings: {total_findings}"
            )
            state = add_decision(state, decision)
            
        except Exception as e:
            # Log error but also run fallback deterministic analysis
            decision = AgentDecision(
                agent_name=self.name,
                decision=f"LLM agent error - running fallback deterministic analysis",
                justification=f"Error: {str(e)}"
            )
            state = add_decision(state, decision)
            
            # Fallback: Always run deterministic tools if agent fails
            rules_findings = rules_tool.analyze(filename, content, "sql")
            for finding in rules_findings:
                state = add_finding(state, finding)
                
            parser_findings = parser_tool.analyze(filename, content)
            for finding in parser_findings:
                state = add_finding(state, finding)
        
        return state
    


# Factory function to create agent instance
def create_sql_agent() -> SQLAgent:
    """
    Create SQL Agent instance.
    Deferred creation to avoid API key check during module import.
    """
    return SQLAgent()
