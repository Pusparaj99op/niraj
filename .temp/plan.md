
# Implementation Plan: NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System

**Branch**: `001-create-a-comprehensive` | **Date**: 17 September 2025 | **Spec**: /home/pranay/Music/niraj/specs/001-create-a-comprehensive/spec.md
**Input**: Feature specification from `/home/pranay/Music/niraj/specs/001-create-a-comprehensive/spec.md`

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
NIRAJ is an advanced self-learning algorithmic AI personal trading system designed for maximum profit extraction through aggressive and intelligent trading strategies targeting Bank Nifty Index futures and options. The system integrates multiple data sources, implements 20+ trading strategies, uses Ollama Gemma3 for AI-driven decision making, and provides a React.js frontend for real-time monitoring.

## Technical Context
**Language/Version**: Python 3.11+  
**Primary Dependencies**: Poetry, FastAPI, React.js, SQLite, Redis, Ollama Gemma3, Angel One Smart API, Dhan HQ API  
**Storage**: SQLite for local data, Redis for caching, CSV files for historical data  
**Testing**: pytest for unit tests, integration tests, strategy backtesting  
**Target Platform**: Ubuntu 22.04 LTS, Linux server  
**Project Type**: Web application (Python backend + React frontend)  
**Performance Goals**: Sub-millisecond execution for HFT strategies, sub-second data processing latency  
**Constraints**: Multi-threaded concurrent processing, auto-reauthentication every 12 hours, real-time WebSocket connections  
**Scale/Scope**: Bank Nifty Index F&O primary, 12 constituent banks secondary, NSE exchange, INR currency

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file is currently a template with no specific requirements defined. All checks pass by default.

## Project Structure

### Documentation (this feature)
```
specs/001-create-a-comprehensive/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Trading-specific additions
NIRAJ/
├── src/
│ ├── core/
│ │ ├── data_manager.py
│ │ ├── information_processor.py
│ │ ├── analysis_engine.py
│ │ └── execution_engine.py
│ ├── strategies/
│ │ ├── predatory/
│ │ │ ├── predator_strategy.py
│ │ │ ├── vulture_approach.py
│ │ │ ├── shadow_trader.py
│ │ │ └── liquidation_hunter.py
│ │ ├── quantitative/
│ │ │ ├── time_arbitrage.py
│ │ │ ├── volatility_vampire.py
│ │ │ ├── news_flash.py
│ │ │ └── manipulation_detector.py
│ │ ├── psychological/
│ │ │ ├── fear_exploiter.py
│ │ │ ├── greed_trap.py
│ │ │ └── squeeze_play.py
│ │ ├── mathematical/
│ │ │ ├── black_swan_hunter.py
│ │ │ ├── gamma_scalper.py
│ │ │ ├── theta_destroyer.py
│ │ │ └── market_maker_killer.py
│ │ └── extreme/
│ │ ├── all_or_nothing.py
│ │ ├── system_breaker.py
│ │ ├── regulatory_gap.py
│ │ ├── swarm_intelligence.py
│ │ └── information_harvester.py
│ ├── ai/
│ │ ├── gemma3_integration.py
│ │ ├── rag_processor.py
│ │ ├── confidence_tracker.py
│ │ └── learning_engine.py
│ ├── api/
│ │ ├── angel_one_client.py
│ │ ├── dhan_client.py
│ │ ├── news_client.py
│ │ └── auth_manager.py
│ ├── risk/
│ │ ├── position_sizer.py
│ │ ├── risk_manager.py
│ │ └── compliance_checker.py
│ ├── utils/
│ │ ├── data_validators.py
│ │ ├── technical_indicators.py
│ │ ├── market_utils.py
│ │ └── logger.py
│ └── main.py
├── frontend/
│ ├── src/
│ │ ├── components/
│ │ │ ├── Dashboard.jsx
│ │ │ ├── AIMonitor.jsx
│ │ │ ├── StrategyPerformance.jsx
│ │ │ ├── RiskManagement.jsx
│ │ │ └── TradingView.jsx
│ │ ├── services/
│ │ │ ├── websocket.js
│ │ │ └── api.js
│ │ ├── utils/
│ │ │ └── formatters.js
│ │ ├── App.jsx
│ │ │ └── index.js
│ │ ├── public/
│ │ ├── package.json
│ │ └── vite.config.js
├── data/
│ ├── historical_data/
│ │ ├── bank_nifty/
│ │ └── individual_banks/
│ ├── models/
│ └── logs/
├── tests/
│ ├── unit/
│ ├── integration/
│ └── strategy_tests/
├── docs/
├── config/
│ ├── trading_config.yml
│ ├── api_config.yml
│ └── ai_config.yml
├── pyproject.toml
├── README.md
└── .gitignore
```

**Structure Decision**: Option 2 - Web application structure with trading-specific backend modules

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context**:
   - Ollama Gemma3:4b-it-q4_K_M integration patterns and RAG implementation
   - Angel One Smart API and Dhan HQ API authentication and rate limits
   - Real-time WebSocket connections for market data
   - Multi-threaded concurrent processing for HFT strategies
   - CSV-based historical data management with gap filling

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for algorithmic trading system"
   For each technology choice:
     Task: "Find best practices for {tech} in financial trading applications"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all technical unknowns resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Trade, Strategy, MarketData, Portfolio, User, AuditLog, AIModel, NewsFeed entities
   - Validation rules for financial data integrity
   - State transitions for trade lifecycle

2. **Generate API contracts** from functional requirements:
   - RESTful endpoints for trade execution, portfolio management, strategy monitoring
   - WebSocket endpoints for real-time data streaming
   - OpenAPI schema for broker API integrations

3. **Generate contract tests** from contracts:
   - Authentication and authorization tests
   - Trade execution and validation tests
   - Real-time data streaming tests

4. **Extract test scenarios** from user stories:
   - Paper trading mode validation
   - Real trading mode with PIN authentication
   - AI confidence scoring and adaptation
   - Risk management and compliance checks

5. **Update agent file incrementally**:
   - Generate .github/copilot-instructions.md for GitHub Copilot
   - Include trading domain knowledge and best practices
   - Preserve existing context and add new technical requirements

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, .github/copilot-instructions.md

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
- Dependency order: Core modules before strategies before AI before frontend
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 40-50 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No constitution violations detected - constitution file is currently template.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/home/pranay/Music/niraj/.specify/memory/constitution.md`*
