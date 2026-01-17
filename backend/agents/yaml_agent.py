"""
YAML Agent - Agentic implementation with LangChain + Structured Data
LLM autonomously decides which tools to call, findings added as structured objects
"""
from typing import List
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from backend.state import AnalysisState, File, Finding, AgentDecision, FileType, add_finding, add_decision
from backend.tools.deterministic.yaml_rules_tool import yaml_rules_tool
from backend.tools.deterministic.yaml_parser_tool import yaml_parser_tool
from backend.config import settings
from backend.utils.gemini_client import gemini_client


# YAML Agent Prompt
YAML_AGENT_PROMPT = """You are an expert Kubernetes/YAML security analyst detecting deployment risks.

Your goal: Identify dangerous patterns, security misconfigurations, and availability risks.

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
1. ALWAYS start with yaml_rules_tool (fast pattern matching)
2. Then use yaml_parser_tool (structural analysis)

Guidelines:
- Prioritize CRITICAL and HIGH severity
- Focus on security risks (privileged containers, host network)
- Check for availability issues (zero replicas, missing limits)

Question: {input}
Thought:{agent_scratchpad}"""


class YAMLAgent:
    """
    Agentic YAML Agent using LangChain ReAct framework.
    
    Architecture:
    - LLM Brain: Gemini decides which tools to call autonomously
    - Tools: Return text summaries (for LLM observation)
    - Findings: Extracted as structured objects and added to state
    
    Key: LLM calls tools, but we capture structured findings directly from tool implementations.
    """
    
    def __init__(self):
        self.name = "yaml_agent"
        self.llm = gemini_client.llm
        
        # Import LangChain tool wrappers
        from backend.tools.langchain_tools import yaml_analysis_tools
        
        prompt = PromptTemplate.from_template(YAML_AGENT_PROMPT)
        
        self.agent = create_react_agent(
            llm=self.llm,
            tools=yaml_analysis_tools,
            prompt=prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=yaml_analysis_tools,
            verbose=settings.log_agent_decisions,
            max_iterations=settings.max_iterations_per_agent,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def process(self, state: AnalysisState) -> AnalysisState:
        """
        Process YAML files in state
        
        Args:
            state: Current analysis state
            
        Returns:
            Updated state with YAML findings
        """
        yaml_files = [f for f in state.get("files", []) if f.file_type == FileType.YAML]
        
        if not yaml_files:
            decision = AgentDecision(
                agent_name=self.name,
                decision="No YAML files to analyze",
                justification="No files with file_type=YAML in state"
            )
            state = add_decision(state, decision)
            return state
        
        for yaml_file in yaml_files:
            state = self._analyze_file_with_agent(state, yaml_file)
        
        return state
    
    def _analyze_file_with_agent(self, state: AnalysisState, file: File) -> AnalysisState:
        """
        Analyze YAML file using LangChain Agent (agentic tool selection)
        + Direct structured finding extraction (no text parsing)
        
        Hybrid Approach:
        1. LLM autonomously decides which tools to call (via LangChain)
        2. We track which tools were called
        3. We directly call those tools again to get structured Finding objects
        4. Findings added to state as structured data (no parsing)
        
        Args:
            state: Current state
            file: YAML file to analyze
            
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
                "input": f"Analyze this YAML file for deployment risks:\n\nFilename: {filename}\n\nContent:\n{content}"
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
            
            if "yaml_rules_tool" in tools_called:
                rules_findings = yaml_rules_tool.analyze(filename, content)
                for finding in rules_findings:
                    state = add_finding(state, finding)
            
            if "yaml_parser_tool" in tools_called:
                parser_findings = yaml_parser_tool.analyze(filename, content)
                for finding in parser_findings:
                    state = add_finding(state, finding)
            
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
            rules_findings = yaml_rules_tool.analyze(filename, content)
            for finding in rules_findings:
                state = add_finding(state, finding)
                
            parser_findings = yaml_parser_tool.analyze(filename, content)
            for finding in parser_findings:
                state = add_finding(state, finding)
        
        return state


def create_yaml_agent() -> YAMLAgent:
    """Factory function to create YAML Agent"""
    return YAMLAgent()
