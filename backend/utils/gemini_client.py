"""
Gemini API wrapper for LangChain integration with cost tracking
"""
import os
from typing import Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.callbacks.base import BaseCallbackHandler
from backend.config import settings


class CostTrackingCallback(BaseCallbackHandler):
    """Callback to track token usage and cost for Gemini API calls"""
    
    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: list, **kwargs) -> None:
        """Called when LLM starts"""
        self.call_count += 1
    
    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM completes - extract token counts"""
        try:
            # LangChain response has usage_metadata
            if hasattr(response, 'llm_output') and response.llm_output:
                token_usage = response.llm_output.get('token_usage', {})
                prompt_tokens = token_usage.get('prompt_tokens', 0)
                completion_tokens = token_usage.get('completion_tokens', 0)
                
                self.prompt_tokens += prompt_tokens
                self.completion_tokens += completion_tokens
                self.total_tokens += (prompt_tokens + completion_tokens)
                
                # Calculate cost
                cost = self._calculate_cost(prompt_tokens, completion_tokens)
                self.total_cost += cost
        except Exception as e:
            # Don't fail on cost tracking errors
            print(f"Warning: Cost tracking failed: {e}")
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD"""
        # Gemini 3.0 Flash pricing (as of 2024)
        # Input: $0.075 per 1M tokens
        # Output: $0.30 per 1M tokens
        input_cost = (prompt_tokens / 1_000_000) * settings.cost_per_1m_input_tokens
        output_cost = (completion_tokens / 1_000_000) * settings.cost_per_1m_output_tokens
        return input_cost + output_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary"""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "call_count": self.call_count
        }
    
    def reset(self):
        """Reset counters"""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0


class GeminiClient:
    """Wrapper for Gemini API with cost tracking"""
    
    def __init__(self, temperature: Optional[float] = None):
        self.temperature = temperature or settings.gemini_temperature
        self.model_name = settings.gemini_model
        self._llm = None
        self.cost_callback = CostTrackingCallback()
    
    @property
    def api_key(self) -> str:
        """Get API key from settings or environment"""
        api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in .env or environment."
            )
        return api_key
    
    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Lazy-loaded LangChain LLM instance with cost tracking"""
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=self.api_key,
                max_output_tokens=settings.gemini_max_tokens,
                callbacks=[self.cost_callback]  # Add cost tracking
            )
        return self._llm
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get current cost tracking summary"""
        return self.cost_callback.get_summary()
    
    def reset_cost_tracking(self):
        """Reset cost counters"""
        self.cost_callback.reset()
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost of API call
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * settings.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * settings.cost_per_1m_output_tokens
        return input_cost + output_cost


# Singleton instance
gemini_client = GeminiClient()
