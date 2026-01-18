"""
Custom callback handler to log LangChain agent thinking process
"""
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List
import sys


class AgentLoggingCallback(BaseCallbackHandler):
    """Custom callback to log agent's thought process"""
    
    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Called when agent takes an action"""
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"🤖 ACTION: {action.tool}", file=sys.stderr)
        print(f"📝 INPUT: {action.tool_input}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        sys.stderr.flush()
    
    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        """Called when agent finishes"""
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"✅ AGENT FINISHED", file=sys.stderr)
        print(f"📊 OUTPUT: {finish.return_values}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)
        sys.stderr.flush()
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when chain starts"""
        if "agent" in str(serialized.get("name", "")).lower():
            print(f"\n🚀 STARTING AGENT CHAIN", file=sys.stderr)
            sys.stderr.flush()
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when chain ends"""
        print(f"\n🏁 CHAIN COMPLETE", file=sys.stderr)
        sys.stderr.flush()
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when tool starts"""
        tool_name = serialized.get("name", "unknown")
        print(f"\n🔧 TOOL START: {tool_name}", file=sys.stderr)
        sys.stderr.flush()
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when tool ends"""
        print(f"✓ TOOL COMPLETE (output length: {len(str(output))} chars)", file=sys.stderr)
        sys.stderr.flush()
