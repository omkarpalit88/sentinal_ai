"""
FastAPI Application for SentinAL
REST API for SQL file analysis
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
from datetime import datetime
from pathlib import Path

from backend.api_models import AnalysisResponse, ErrorResponse, HealthResponse
from backend.workflow import create_workflow
from backend.state import File as StateFile, FileType, AnalysisState, ConstraintLevel
from backend.utils.helpers import detect_file_type
from backend.config import settings


# Create FastAPI app
app = FastAPI(
    title="SentinAL API",
    description="Agentic Code Analysis for Deployment Safety",
    version="1.0.0"
)

# Add CORS middleware (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_file(file: UploadFile = File(...)):
    """
    Analyze uploaded SQL/Terraform/YAML file
    
    Returns Defense Memo and risk assessment
    """
    try:
        # Validate file type
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = [".sql", ".tf", ".yaml", ".yml"]
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content_bytes = await file.read()
        content = content_bytes.decode('utf-8')
        
        # Check file size
        file_size = len(content_bytes)
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_file_size_bytes} bytes"
            )
        
        # Detect file type
        file_type = detect_file_type(file.filename)
        
        # Create state file
        state_file = StateFile(
            filename=file.filename,
            content=content,
            file_type=file_type,
            size_bytes=file_size
        )
        
        # Initialize analysis state
        start_time = datetime.now()
        initial_state: AnalysisState = {
            "files": [state_file],
            "findings": [],
            "cross_file_deps": [],
            "agent_decisions": [],
            "overall_risk": None,
            "defense_memo": None,
            "analysis_started_at": start_time,
            "analysis_completed_at": None,
            "total_cost_usd": 0.0,
            "next_agent": None
        }
        
        # Run workflow
        workflow = create_workflow()
        final_state = workflow.invoke(initial_state)
        
        # Calculate analysis time
        end_time = datetime.now()
        analysis_time = (end_time - start_time).total_seconds()
        
        # Count findings by severity
        findings = final_state.get("findings", [])
        critical_count = sum(1 for f in findings if f.severity == ConstraintLevel.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == ConstraintLevel.HIGH)
        medium_count = sum(1 for f in findings if f.severity == ConstraintLevel.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == ConstraintLevel.LOW)
        
        # Calculate risk score
        from backend.utils.risk_scoring import calculate_risk_score
        risk_score = calculate_risk_score(findings)
        
        # Build response
        response = AnalysisResponse(
            defense_memo=final_state.get("defense_memo", "# No memo generated"),
            risk_score=risk_score,
            risk_classification=final_state.get("overall_risk", "INFO"),
            total_findings=len(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            analysis_cost_usd=final_state.get("total_cost_usd", 0.0),
            analysis_time_seconds=analysis_time
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
