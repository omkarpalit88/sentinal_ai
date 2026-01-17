# SentinAL - Project Context Document
**Last Updated:** 2026-01-17 | **Phase:** 1 Complete ✅ (See STATUS.md for details)

> **Purpose:** This document preserves all project knowledge for crash recovery. If Antigravity crashes or laptop restarts, read this file + `task.md` to rebuild full context.

---

## 🎯 Product Overview

**SentinAL** = Sentinel for Automated Linting  
**Tagline:** AI-powered change management auditor that detects deployment risks before they cause outages

### The Problem
- **64%** of IT outages caused by configuration/change management issues (Uptime Institute 2023)
- Manual CAB (Change Advisory Board) reviews miss subtle risks:
  - Cross-file dependencies
  - Implicit conflicts
  - Context-dependent issues

**Real Example:**
```
File 1: DROP TABLE users;
File 2: SELECT * FROM users WHERE...;
```
❌ Manual review: Each file looks "okay" individually  
✅ SentinAL: Detects cross-file dependency → CRITICAL risk

### The Solution
- **Multi-agent system** using LangGraph
- **Specialist agents**: SQL, Terraform, YAML + Cross-file analyzer
- **Hybrid analysis**: Deterministic rules (70-80%) + LLM semantic (20-30%)
- **Output**: Defense Memo with risk scoring and recommendations
- **Speed**: <60 seconds, pennies per analysis

### Target Market
- Mid-size companies (100-5000 employees)
- Can't afford $50K-500K enterprise AI licenses
- Need GenAI adoption without risk
- Have deployment processes but lack automated guardrails

---

## 🏗️ Architecture

### Core Principles

**1. Agent = LLM (Brain) + Tools (Hands)**
- Agent's LLM decides: "Which tool should I call?"
- Tools execute: Both deterministic (regex, AST) AND LLM-powered (semantic analysis)
- **True agency**: Agent chooses tools based on findings

**2. Hybrid Analysis Approach**
- **Layer 1**: Deterministic (regex, AST parsing) - Fast, 100% reliable, 70-80% coverage
- **Layer 2**: LLM semantic - Slower, contextual, catches 20-30% subtle risks
- Deterministic = source of truth, LLM enhances

**3. Shared State (LangGraph)**
- All agents read/write to shared state
- Enables cross-file intelligence (Agent 1 sees what Agent 2 found)
- Immutable-style updates (functional programming)

**4. Tools Philosophy**
- **Deterministic tools**: Fast (<1s), cheap ($0), always correct (regex, parsing)
- **LLM-powered tools**: Slow (2-10s), expensive ($), context-aware (semantic analysis)
- Agent decides which tools based on file complexity

### Agent Flow (Phase 1)

```
User Upload → Orchestrator Agent
              ├─ File type detection
              ├─ Route to SQL Agent (Phase 1)
              │  ├─ Rules Tool (deterministic)
              │  ├─ Parser Tool (deterministic)
              │  └─ Semantic Tool (LLM - if needed)
              └─ Synthesis Agent
                 └─ Generate Defense Memo
```

**Full Architecture (Phase 5):**
```
Orchestrator → [SQL Agent | Terraform Agent | YAML Agent]
            → Cross-File Agent (dependency detection)
            → Synthesis Agent (Defense Memo)
```

---

## 📁 Project Structure

```
sentinal-ai/
├── backend/
│   ├── state.py              # ✅ LangGraph state schema (Pydantic)
│   ├── orchestrator.py       # ✅ File routing agent
│   ├── workflow.py           # ✅ LangGraph workflow definition
│   ├── config.py             # ✅ Settings + deterministic veto rules
│   ├── agents/
│   │   ├── sql_agent.py      # ⏳ Sub-Phase 1.3
│   │   ├── terraform_agent.py # ⏳ Phase 2
│   │   ├── yaml_agent.py     # ⏳ Phase 2
│   │   ├── cross_file_agent.py # ⏳ Phase 4
│   │   └── synthesis_agent.py # ⏳ Sub-Phase 1.5
│   ├── tools/
│   │   ├── deterministic/
│   │   │   ├── rules_tool.py      # ⏳ Sub-Phase 1.2
│   │   │   ├── parser_tool.py     # ⏳ Sub-Phase 1.2
│   │   │   └── dependency_tool.py # ⏳ Sub-Phase 1.2
│   │   └── llm_powered/
│   │       ├── semantic_tool.py   # ⏳ Sub-Phase 1.4
│   │       └── context_tool.py    # ⏳ Sub-Phase 1.4
│   └── utils/
│       ├── gemini_client.py  # ✅ Gemini API wrapper
│       └── helpers.py        # ✅ Utility functions
├── frontend/                 # ⏳ Sub-Phase 1.6
├── test_data/                # ✅ SQL safe/dangerous/subtle examples
├── tests/                    # ✅ Unit tests (Sub-Phase 1.1 complete)
├── requirements.txt          # ✅ Dependencies installed
├── .env.example              # ✅ Config template
├── README.md                 # ✅ Project documentation
└── CONTEXT.md               # ✅ This file!
```

---

## 🔑 Key Technical Decisions

### 1. Why LangGraph?
- Purpose-built for multi-agent systems (not simple chains)
- State management built-in
- Supports cyclic workflows (agents can loop/iterate)
- Conditional routing (orchestrator decides next agent)
- Production-ready, maintained by LangChain team

### 2. Why Gemini 3.0 Flash Preview?
- **2M+ token context window** (can send entire files and more)
- **Faster inference** (1-3 seconds)
- **Lower cost** (improved efficiency)
- **Enhanced reasoning** (better function calling and tool use)
- Native LangChain integration

### 3. Why Multi-Agent vs Monolithic?
- **Scalability**: Easy to add new file types (just add new agent)
- **Specialization**: SQL Agent optimized for SQL patterns
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Can upgrade SQL Agent without touching Terraform Agent
- **Demo appeal**: "Multiple AI agents collaborating" is impressive

### 4. Why Hybrid (Deterministic + LLM)?
- **Speed**: Deterministic is 100x faster
- **Cost**: Regex costs $0, LLM costs money
- **Reliability**: Deterministic never hallucinates
- **Compliance**: Auditors trust regex, skeptical of "AI black box"
- **Quality**: LLM catches subtle patterns regex misses

---

## 🎓 Critical Refinements (from Review)

### Risk Mitigations Implemented

**1. Agent Autonomy Guardrails**
- Added **tool selection heuristics** per agent (not fully free decision-making)
- Example: SQL Agent MUST run `rules_tool` first, THEN decide if `semantic_tool` needed
- **Max iterations** configured (3 per agent) to prevent infinite loops

**2. Deterministic Veto Rules**
- Hardcoded safety patterns that auto-flag CRITICAL regardless of LLM
- Examples in `config.py`:
  - `DROP DATABASE` → CRITICAL
  - `TRUNCATE TABLE` → CRITICAL
  - `force_destroy = true` (Terraform) → CRITICAL
  - `DELETE FROM table;` (no WHERE) → HIGH

**3. Agent Decision Logging**
- Every agent logs: "I called X tool because Y"
- Stored in `AgentDecision` model
- Included in Defense Memo for transparency
- Builds user trust + easier debugging

**4. Strict State Schema**
- Pydantic models for all state objects
- Type safety enforced
- Immutable-style updates (functional programming)
- Each agent has clear read/write boundaries

**5. Planned: Two-Pass Cross-File Analysis (Phase 4)**
- **Pass 1**: Extract all entities (tables, resources, configs)
- **Pass 2**: Analyze with cross-file context
- Build dependency graph FIRST, then analyze in order

---

## 📊 Current Status

### ✅ Completed: Sub-Phase 1.1 (State Machine + Orchestrator)

**Files Created:**
1. `backend/state.py` - Strict Pydantic state schema
   - Models: `File`, `Finding`, `Dependency`, `AgentDecision`, `AnalysisState`
   - Immutable update helpers
   - Type safety with enums

2. `backend/config.py` - Configuration management
   - Pydantic Settings with `.env` support
   - Deterministic veto rules (SQL, Terraform, YAML)
   - Agent behavior settings

3. `backend/utils/gemini_client.py` - Gemini API wrapper
   - LangChain integration
   - Cost tracking support
   - Lazy-loaded LLM instance

4. `backend/utils/helpers.py` - Utility functions
   - File type detection (SQL/Terraform/YAML/Unknown)
   - Code snippet extraction
   - Risk calculation (CRITICAL/HIGH/MEDIUM/LOW)
   - Approval recommendation logic

5. `backend/orchestrator.py` - Orchestrator Agent
   - File type detection
   - Routing to specialist agents (SQL only in Phase 1)
   - State initialization
   - Decision logging

6. `backend/workflow.py` - LangGraph workflow
   - State graph with nodes: Orchestrator → SQL Agent → Synthesis Agent
   - Conditional routing edges
   - Placeholder agents (implemented in later sub-phases)

7. `tests/test_sub_phase_1_1.py` - Unit tests
   - 16 tests, all passing ✅
   - Coverage: State models, helpers, orchestrator, workflow
   - Integration test of full workflow

8. `requirements.txt` - Dependencies
   - All installed successfully ✅
   - 66 packages total

**Test Results:**
```
======================= 16 passed, 18 warnings in 3.23s ========================
```

**Known Issues (Non-blocking):**
- 18 Pydantic deprecation warnings (cosmetic, can fix later)
- Using `Config` class instead of `ConfigDict` (Pydantic V2 style)
- Using `env` parameter in `Field` instead of `json_schema_extra`

---

## 📝 Development Phases

### Phase 1: Foundation (Days 1-2, 14-16 hours)
**Goal:** Working single-agent system with orchestrator

- [x] **Sub-Phase 1.1**: State Machine + Orchestrator ✅ COMPLETE
- [ ] **Sub-Phase 1.2**: Deterministic Tools (rules, parser, dependency)
- [ ] **Sub-Phase 1.3**: SQL Agent with tool usage
- [ ] **Sub-Phase 1.4**: LLM-powered semantic tool
- [ ] **Sub-Phase 1.5**: Synthesis Agent (Defense Memo generation)
- [ ] **Sub-Phase 1.6**: API + Frontend (FastAPI + HTML)

**Success Criteria:** Upload SQL file → Agent analyzes → Returns Defense Memo

### Phase 2: Multi-Agent Specialization (Days 3-4, 12-14 hours)
- Add Terraform Agent
- Add YAML Agent
- Enhanced orchestrator routing (3 agent types)
- Shared state for cross-agent communication

### Phase 3: Intelligent Reasoning (Days 5-6, 14-16 hours)
- Agents can call tools multiple times (iterative reasoning)
- Context Analyzer Tool (LLM): Production vs staging, blast radius
- Enhanced Dependency Tool: Cross-statement analysis
- Agent decision logging (reasoning trail)
- 10+ additional best practice rules

### Phase 4: Multi-File Intelligence (Days 7-8, 12-14 hours)
- Multi-file orchestration (2-10 files)
- Cross-File Agent (detects dependencies)
- Execution Order Validator Tool
- Enhanced Defense Memo (per-file + cross-file findings)

### Phase 5: Production Polish (Days 9-10, 10-12 hours)
- Professional UI (multi-file upload, progress indicators)
- 30-file test suite (SQL/Terraform/YAML, safe/dangerous/subtle)
- Performance metrics dashboard
- Complete documentation + demo video
- Error handling + graceful degradation

---

## 🛠️ Tech Stack

**Backend:**
- Python 3.9+
- **LangGraph 0.6.11** - Multi-agent orchestration
- **LangChain 0.3.27** - Agent framework, tools
- **Gemini 3.0 Flash Preview** - LLM via `langchain-google-genai`
- **FastAPI 0.128.0** - REST API (Sub-Phase 1.6)
- **Pydantic 2.12.5** - Data validation, settings
- **Pytest 8.4.2** - Testing

**Tools/Libraries:**
- `sqlparse` - SQL parsing
- `pyyaml` - YAML parsing
- `uvicorn` - ASGI server

**Frontend (Sub-Phase 1.6):**
- Week 1: Simple HTML/CSS/JavaScript
- Week 2: Upgrade to React (if time permits)

---

## 🔄 State Schema Reference

```python
class AnalysisState(TypedDict):
    # Input
    files: List[File]
    
    # Analysis results
    findings: List[Finding]
    cross_file_deps: List[Dependency]
    agent_decisions: List[AgentDecision]
    
    # Overall assessment
    overall_risk: Optional[ConstraintLevel]
    recommend_approval: Optional[bool]
    defense_memo: Optional[str]
    
    # Metadata
    analysis_started_at: Optional[datetime]
    analysis_completed_at: Optional[datetime]
    total_cost_usd: float
    
    # Internal routing
    next_agent: Optional[str]
```

**Key Models:**
- `File`: filename, content, file_type, size_bytes
- `Finding`: file_id, line_number, severity, category, description, detected_by, reasoning
- `Dependency`: source_file, target_file, dependency_type, risk_level
- `AgentDecision`: agent_name, decision, tool_called, justification

**Risk Levels:**
- `CRITICAL` → Auto-reject
- `HIGH` → Recommend rejection
- `MEDIUM` → Caution
- `LOW` → Monitor
- `INFO` → No action

---

## 🚀 Quick Start (After Crash Recovery)

### 1. Verify Environment
```bash
cd /Users/omkarpalit/Documents/AI\ Projects/sentinal-ai
source venv/bin/activate  # If venv exists
python3 -m pytest tests/test_sub_phase_1_1.py -v  # Should pass
```

### 2. Check Dependencies
```bash
python3 -c "import langgraph, langchain, pydantic; print('✅ All imports work')"
```

### 3. Review Progress
```bash
cat task.md  # Check current phase
cat CONTEXT.md  # Rebuild context
```

### 4. Continue Development
- Read `task.md` to see next unchecked item
- Typically: Sub-Phase 1.2 (Deterministic Tools)

---

## 📚 Key Concepts

### Defense Memo
- **Format**: Markdown
- **Content**: Risk breakdown, line-by-line findings, recommendations, overall score
- **Output**: Approve/Reject recommendation

### Deterministic Tools
- Non-LLM tools (regex, AST parsing, graph algorithms)
- Fast (<1 second), 100% reproducible, never hallucinate
- Cheap ($0 - no API costs)

### LLM-Powered Tools
- Use Gemini for semantic analysis
- Slower (2-10 seconds), context-aware
- Can detect subtle patterns deterministic tools miss
- Requires API calls (costs money)

### Agency
- Agent's ability to make decisions
- "Should I call this tool?"
- "Do I need more information?"
- "Is this analysis sufficient?"

### Tool Selection Heuristics (Planned for Sub-Phase 1.3)
- SQL Agent: ALWAYS run `rules_tool` → IF 2+ findings → THEN run `semantic_tool`
- Prevents unnecessary LLM calls (cost control)
- Ensures deterministic baseline always runs

---

## 🎯 Next Immediate Steps

**Sub-Phase 1.2: Deterministic Tools**
1. Create `backend/tools/deterministic/rules_tool.py`
   - Pattern matching with regex
   - Apply veto rules from `config.py`
   - Return `Finding` objects

2. Create `backend/tools/deterministic/parser_tool.py`
   - SQL AST parsing with `sqlparse`
   - Extract entities (tables, columns)
   - Detect DDL vs DML operations

3. Create `backend/tools/deterministic/dependency_tool.py`
   - Graph-based dependency analysis
   - Detect table references
   - Build dependency map

4. Write unit tests: `tests/test_sub_phase_1_2.py`

**Estimated Time:** 3-4 hours

---

## 💡 Important Notes

### Environment Setup
- Virtual environment: `venv/` (may not be fully set up)
- Dependencies installed via: `python3 -m pip install --user -r requirements.txt`
- Gemini API key: Set in `.env` file (copy from `.env.example`)

### Git Version Control (RECOMMENDED)
```bash
git init
git add .
git commit -m "Sub-Phase 1.1 complete - State machine + Orchestrator"
```

### Testing Philosophy
- Unit tests per sub-phase
- Test deterministic tools with fixed inputs
- Mock LLM calls in tests (don't waste API credits)
- Integration test at end of each phase

### Cost Tracking
- Currently using Gemini free tier ($0)
- Track tokens in `state["total_cost_usd"]`
- Target: <$0.01 per analysis

---

## 🐛 Known Gotchas

1. **Pydantic V2 Deprecations**: Using old `Config` class style (works fine, just warnings)
2. **Virtual environment**: Initial `python3 -m venv venv` hung - used `--user` install instead
3. **File paths**: Always use absolute paths in code
4. **LangGraph state**: Must be TypedDict (not BaseModel)
5. **Test execution**: Use `python3 -m pytest` (not just `pytest`)

---

## 📞 Recovery Instructions

**If Antigravity crashes:**

1. **Open new conversation** in Antigravity
2. **Navigate to project**: `/Users/omkarpalit/Documents/AI Projects/sentinal-ai`
3. **Say to AI**: 
   > "I'm working on SentinAL project. Read CONTEXT.md and task.md to understand where we are. We just completed Sub-Phase 1.1. What should we build next?"

4. **AI will rebuild context** from these files and continue seamlessly

---

**End of Context Document**  
**Version:** 1.0 | **Last Update:** 2026-01-14 21:36 IST
