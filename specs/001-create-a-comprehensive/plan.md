
# Implementation Plan: NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System

**Branch**: `001-create-a-comprehensive` | **Date**: 17 September 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-create-a-comprehensive/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
NIRAJ is an advanced self-learning algorithmic AI personal trading system targeting Bank Nifty Index F&O with 20 aggressive trading strategies. The system combines Ollama Gemma3 AI integration, dual broker support (Angel One/Dhan), real-time data processing, and comprehensive risk management. Features include paper trading mode with ₹1,00,000 virtual capital, PIN-protected real trading mode (1937), React.js frontend on port 3005, and sub-millisecond execution capabilities for high-frequency trading strategies.

## Technical Context
**Language/Version**: Python 3.11+, React.js with Vite  
**Primary Dependencies**: FastAPI, Ollama Gemma3, SQLite, Redis, Poetry, Angel One Smart API, Dhan HQ API  
**Storage**: SQLite for local data, Redis for caching, CSV files for historical data in /historical_data/ folder  
**Testing**: pytest for Python backend, Jest for React frontend, comprehensive strategy backtesting framework  
**Target Platform**: Ubuntu 22.04 LTS, Lenovo IdeaPad Gaming 3 (AMD Ryzen 7 6800H, 16GB RAM, RTX 3050)  
**Project Type**: web - FastAPI backend + React frontend  
**Performance Goals**: Sub-millisecond execution for HFT strategies, sub-second data processing latency, real-time WebSocket updates  
**Constraints**: <1ms execution for HFT, continuous 24/7 operation during market hours, zero data loss, regulatory compliance  
**Scale/Scope**: 20 trading strategies, 13 securities (Bank Nifty + 12 banks), multi-threaded concurrent processing, real-time AI training

**Arguments from User**: Comprehensive project structure with 28-week development phases covering core infrastructure, API integration, analysis engine, AI/ML integration, 5 batches of strategy implementation, execution engine, frontend development, risk management, testing, and deployment.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since the constitution file is a template, I'll apply general software development principles:
- **Library-First**: ✅ Each component (data_manager, analysis_engine, execution_engine) is designed as standalone, testable modules
- **API-First**: ✅ FastAPI provides REST endpoints, WebSocket for real-time data, and CLI interfaces planned
- **Test-First**: ✅ TDD approach with unit tests, integration tests, and strategy backtesting before implementation
- **Security-First**: ✅ Multi-layer authentication, encrypted data storage, PIN protection for real trading
- **Performance-First**: ✅ Sub-millisecond execution requirements, concurrent processing, optimized data structures
- **Risk-First**: ✅ Comprehensive risk management, compliance checking, audit trails, paper trading default

**Complexity Justification**: The 20 aggressive trading strategies and AI integration add necessary complexity for maximum profit extraction while maintaining regulatory compliance.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 2: Web application (FastAPI backend + React frontend)
backend/
├── src/
│   ├── core/
│   │   ├── data_manager.py
│   │   ├── information_processor.py
│   │   ├── analysis_engine.py
│   │   └── execution_engine.py
│   ├── strategies/
│   │   ├── predatory/
│   │   ├── quantitative/
│   │   ├── psychological/
│   │   ├── mathematical/
│   │   └── extreme/
│   ├── ai/
│   │   ├── gemma3_integration.py
│   │   ├── rag_processor.py
│   │   ├── confidence_tracker.py
│   │   └── learning_engine.py
│   ├── api/
│   │   ├── angel_one_client.py
│   │   ├── dhan_client.py
│   │   ├── news_client.py
│   │   └── auth_manager.py
│   ├── risk/
│   │   ├── position_sizer.py
│   │   ├── risk_manager.py
│   │   └── compliance_checker.py
│   ├── utils/
│   │   ├── data_validators.py
│   │   ├── technical_indicators.py
│   │   ├── market_utils.py
│   │   └── logger.py
│   └── main.py
├── tests/
│   ├── contract/
│   ├── integration/
│   └── unit/
├── data/
│   ├── historical_data/
│   │   ├── bank_nifty/
│   │   └── individual_banks/
│   ├── models/
│   └── logs/
├── config/
│   ├── trading_config.yml
│   ├── api_config.yml
│   └── ai_config.yml
└── pyproject.toml

frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx
│   │   ├── AIMonitor.jsx
│   │   ├── StrategyPerformance.jsx
│   │   ├── RiskManagement.jsx
│   │   └── TradingView.jsx
│   ├── services/
│   │   ├── websocket.js
│   │   └── api.js
│   ├── utils/
│   │   └── formatters.js
│   ├── App.jsx
│   └── index.js
├── public/
├── tests/
├── package.json
└── vite.config.js
```

**Structure Decision**: Option 2 - Web application with FastAPI backend (port 8000) and React frontend (port 3005)

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
