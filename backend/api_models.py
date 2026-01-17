"""
API Request/Response Models for SentinAL
Pydantic schemas for FastAPI endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class AnalysisResponse(BaseModel):
    """Response from /api/analyze endpoint"""
    defense_memo: str = Field(description="Markdown-formatted Defense Memo")
    risk_score: int = Field(description="Overall risk score (0-100)")
    risk_classification: str = Field(description="CRITICAL, HIGH, MEDIUM, or LOW")
    total_findings: int = Field(description="Total number of findings")
    critical_count: int = Field(description="Number of CRITICAL findings")
    high_count: int = Field(description="Number of HIGH findings")
    medium_count: int = Field(description="Number of MEDIUM findings")
    low_count: int = Field(description="Number of LOW findings")
    analysis_cost_usd: float = Field(description="Total cost of LLM API calls")
    analysis_time_seconds: float = Field(description="Time taken for analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "defense_memo": "# Defense Memo: migration.sql\n\n## Executive Summary\n...",
                "risk_score": 65,
                "risk_classification": "CRITICAL",
                "total_findings": 3,
                "critical_count": 1,
                "high_count": 2,
                "medium_count": 0,
                "low_count": 0,
                "analysis_cost_usd": 0.000123,
                "analysis_time_seconds": 2.5
            }
        }


class ErrorResponse(BaseModel):
    """Error response for API endpoints"""
    error: str = Field(description="Error type")
    detail: str = Field(description="Detailed error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "InvalidFileType",
                "detail": "Only .sql, .tf, and .yaml files are supported"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0"
            }
        }
