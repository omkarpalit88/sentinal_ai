# SentinAL - AI-Powered Deployment Risk Analyzer

**Tagline:** Detect deployment risks before they cause outages

## Overview
SentinAL is a multi-agent agentic system that analyzes deployment artifacts (SQL migrations, Terraform configs, YAML files) to detect risks that manual Change Advisory Board (CAB) reviews miss.

### The Problem
- 64% of IT outages are caused by configuration/change management issues
- Manual reviews miss subtle risks: cross-file dependencies, implicit conflicts
- Example: File 1 drops a table, File 2 queries it → outage

### The Solution
- **Multi-agent architecture**: Specialist agents (SQL, Terraform, YAML) + Cross-file analyzer
- **Hybrid analysis**: Deterministic rules (fast, 70-80% coverage) + LLM semantic analysis (subtle risks, 20-30%)
- **Fast & cheap**: <60 seconds, pennies per analysis
- **Output**: Defense Memo with risk scores and recommendations

## Project Structure
```
sentinal-ai/
├── backend/
│   ├── state.py              # LangGraph state schema
│   ├── orchestrator.py       # File routing agent
│   ├── workflow.py           # LangGraph workflow
│   ├── config.py             # Configuration + veto rules
│   ├── agents/               # Specialist agents
│   ├── tools/
│   │   ├── deterministic/    # Pattern matching, AST parsing
│   │   └── llm_powered/      # Semantic analysis (Gemini)
│   └── utils/                # Helpers, Gemini client
├── frontend/                 # Upload UI (HTML → React)
├── test_data/                # Test files (safe/dangerous/subtle)
└── tests/                    # Unit tests
```

## Tech Stack
- **LangGraph 0.2.0**: Multi-agent orchestration
- **LangChain**: Agent framework, tools
- **Gemini 2.0 Flash**: LLM (1M+ context, fast, cheap)
- **FastAPI**: REST API
- **Pydantic**: Data validation

## Installation

### 1. Clone repository
```bash
cd sentinal-ai
```

### 2. Create virtual environment
```bash
python3 -m venv .env
source .env/bin/activate  # On Windows: .env\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Usage

### Run tests
```bash
pytest tests/ -v
```

### Run workflow (programmatic)
```python
from backend.workflow import create_workflow
from backend.state import AnalysisState, File, FileType

workflow = create_workflow()

initial_state: AnalysisState = {
    "files": [
        File(
            filename="migration.sql",
            content="DROP TABLE users;",
            file_type=FileType.SQL,
            size_bytes=20
        )
    ],
    "findings": [],
    "cross_file_deps": [],
    "agent_decisions": [],
    "overall_risk": None,
    "recommend_approval": None,
    "defense_memo": None,
    "analysis_started_at": None,
    "analysis_completed_at": None,
    "total_cost_usd": 0.0,
    "next_agent": None
}

result = workflow.invoke(initial_state)
print(result["defense_memo"])
```

## Development Phases

### Phase 1: Foundation (Current)
- ✅ Sub-Phase 1.1: State machine + Orchestrator
- ⏳ Sub-Phase 1.2: Deterministic tools
- ⏳ Sub-Phase 1.3: SQL Agent
- ⏳ Sub-Phase 1.4: LLM semantic tool
- ⏳ Sub-Phase 1.5: Synthesis Agent (Defense Memo)
- ⏳ Sub-Phase 1.6: API + Frontend

### Phase 2: Multi-Agent Specialization
- Add Terraform and YAML agents
- Enhanced routing

### Phase 3: Intelligent Reasoning
- Iterative tool selection
- Context-aware analysis

### Phase 4: Multi-File Intelligence
- Cross-file dependency detection
- Execution order validation

### Phase 5: Production Polish
- Professional UI
- 30-file test suite
- Performance metrics

## Key Features

### Deterministic Veto Rules
Hardcoded safety patterns that auto-flag critical risks:
- `DROP DATABASE` → CRITICAL
- `TRUNCATE TABLE` → CRITICAL
- `force_destroy = true` (Terraform) → CRITICAL
- Unfiltered `DELETE` → HIGH

### Agent Decision Logging
Full transparency into agent reasoning:
- Which tools were called
- Why they were called
- What was found

### Cost Tracking
Track LLM API costs per analysis (currently $0 on free tier)

## Contributing
This is a POC project. See `task.md` for current development status.

## License
MIT
