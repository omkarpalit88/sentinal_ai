""" Pydantic settings for SentinAL configuration
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Gemini API
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3-flash-preview", env="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.1, env="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(default=8192, env="GEMINI_MAX_TOKENS")
    
    # Cost tracking (Gemini 2.0 Flash pricing)
    cost_per_1m_input_tokens: float = 0.0  # Free tier
    cost_per_1m_output_tokens: float = 0.0  # Free tier
    
    # Agent behavior
    max_iterations_per_agent: int = Field(default=3, env="MAX_ITERATIONS")
    enable_llm_tools: bool = Field(default=True, env="ENABLE_LLM_TOOLS")
    
    # Analysis thresholds
    llm_tool_threshold: int = Field(
        default=2, 
        env="LLM_TOOL_THRESHOLD",
        description="Min deterministic findings before calling LLM tools"
    )
    
    # File size limits
    max_file_size_bytes: int = Field(default=1_000_000, env="MAX_FILE_SIZE")  # 1MB
    max_files_per_analysis: int = Field(default=10, env="MAX_FILES")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_agent_decisions: bool = Field(default=True, env="LOG_DECISIONS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
settings = Settings()


# Deterministic veto rules (hardcoded safety patterns)
VETO_RULES_SQL = [
    {
        "pattern": r"DROP\s+DATABASE",
        "severity": "CRITICAL",
        "category": "DROP_DATABASE",
        "description": "Dropping entire database - VETO",
        "recommendation": "Never drop databases in production. Use schema migrations."
    },
    {
        "pattern": r"TRUNCATE\s+TABLE",
        "severity": "CRITICAL",
        "category": "TRUNCATE_TABLE",
        "description": "Truncating table - data loss risk",
        "recommendation": "Use DELETE with WHERE clause for selective removal."
    },
    {
        "pattern": r"DROP\s+TABLE",
        "severity": "CRITICAL",
        "category": "DROP_TABLE",
        "description": "Dropping table - permanent data loss",
        "recommendation": "Verify no downstream dependencies. Consider soft delete."
    },
    {
        "pattern": r"DELETE\s+FROM\s+\w+\s*;",
        "severity": "HIGH",
        "category": "UNFILTERED_DELETE",
        "description": "DELETE without WHERE clause - deletes all rows",
        "recommendation": "Add WHERE clause to limit deletion scope."
    },
    {
        "pattern": r"--\s*ROLLBACK",
        "severity": "MEDIUM",
        "category": "COMMENTED_ROLLBACK",
        "description": "Rollback logic is commented out",
        "recommendation": "Uncomment rollback for migration safety."
    }
]

VETO_RULES_TERRAFORM = [
    {
        "pattern": r"force_destroy\s*=\s*true",
        "severity": "CRITICAL",
        "category": "FORCE_DESTROY",
        "description": "force_destroy=true allows data loss",
        "recommendation": "Remove force_destroy unless intentional data deletion."
    },
    {
        "pattern": r"prevent_destroy\s*=\s*false",
        "severity": "HIGH",
        "category": "PREVENT_DESTROY_DISABLED",
        "description": "prevent_destroy disabled - allows accidental deletion",
        "recommendation": "Enable prevent_destroy for critical resources."
    },
    {
        "pattern": r"terraform\s+destroy",
        "severity": "CRITICAL",
        "category": "TERRAFORM_DESTROY",
        "description": "Terraform destroy command - infrastructure removal",
        "recommendation": "Verify this is intentional. Use targeted destroy if possible."
    },
    {
        "pattern": r"count\s*=\s*0",
        "severity": "HIGH",
        "category": "RESOURCE_COUNT_ZERO",
        "description": "Resource count set to 0 - removes infrastructure",
        "recommendation": "Ensure intentional resource removal."
    }
]

VETO_RULES_YAML = [
    {
        "pattern": r"replicas:\s*0",
        "severity": "HIGH",
        "category": "ZERO_REPLICAS",
        "description": "Deployment scaled to 0 replicas - service downtime",
        "recommendation": "Verify intentional scaling to zero."
    },
    {
        "pattern": r"privileged:\s*true",
        "severity": "CRITICAL",
        "category": "PRIVILEGED_CONTAINER",
        "description": "Container runs with privileged mode - security risk",
        "recommendation": "Remove privileged mode unless absolutely required. Use capabilities instead."
    },
    {
        "pattern": r"hostNetwork:\s*true",
        "severity": "CRITICAL",
        "category": "HOST_NETWORK",
        "description": "Pod uses host network namespace - security risk",
        "recommendation": "Remove hostNetwork unless required for network appliances."
    },
    {
        "pattern": r"imagePullPolicy:\s*Always",
        "severity": "MEDIUM",
        "category": "ALWAYS_PULL_IMAGE",
        "description": "Always pulling images can cause downtime if registry is unavailable",
        "recommendation": "Use IfNotPresent for production stability."
    }
]
