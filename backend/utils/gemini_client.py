"""
Gemini API wrapper for LangChain integration
"""
import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import settings


class GeminiClient:
    """Wrapper for Gemini API with cost tracking"""
    
    def __init__(self, temperature: Optional[float] = None):
        self.temperature = temperature or settings.gemini_temperature
        self.model_name = settings.gemini_model
        self._llm = None
    
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
        """Lazy-loaded LangChain LLM instance"""
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=self.api_key,
                max_output_tokens=settings.gemini_max_tokens
            )
        return self._llm
    
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
