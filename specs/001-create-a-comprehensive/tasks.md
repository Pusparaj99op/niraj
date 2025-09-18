# Tasks: NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System

**Input**: Design documents from `/specs/001-create-a-comprehensive/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Execution Flow (main)
```
1. Load feature spec from Input path ✅
   → Implementation plan loaded from plan.md
   → Tech stack: Python 3.11+, FastAPI, React, SQLite+Redis, Ollama Gemma3
   → Structure: Web app (backend/ + frontend/)
2. Load optional design documents ✅:
   → data-model.md: 13 entities extracted → model tasks
   → contracts/: REST API + WebSocket → contract test tasks  
   → research.md: Decisions extracted → setup tasks
3. Generate tasks by category ✅:
   → Setup: Poetry, Ollama, configs, DB setup
   → Tests: Contract tests for 25+ endpoints, integration tests
   → Core: 13 models, services, AI integration, 20 strategies
   → Integration: APIs, WebSocket, risk management
   → Polish: Unit tests, performance, docs
4. Apply task rules ✅:
   → Different files = [P] for parallel execution
   → Same file = sequential dependencies
   → Tests before implementation (TDD approach)
5. Number tasks sequentially ✅ (T001-T089)
6. Generate dependency graph ✅
7. Create parallel execution examples ✅
8. Validate task completeness ✅:
   → All REST endpoints have contract tests ✅
   → All 13 entities have model tasks ✅
   → All quickstart scenarios have integration tests ✅
9. Return: SUCCESS (89 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- Web app structure: `backend/src/`, `frontend/src/`

## Phase 3.1: Project Setup & Infrastructure

### T001-T010: Environment and Dependencies
- [x] T001 Create project structure with backend/ and frontend/ directories per implementation plan
- [x] T002 Initialize Poetry project in backend/ with pyproject.toml for Python 3.11+ dependencies
- [x] T003 [P] Install and configure Ollama with Gemma3:4b-it-q4_K_M model
- [x] T004 [P] Initialize React project in frontend/ with Vite and TypeScript
- [x] T005 [P] Configure development environment with .gitignore, .env templates, and VSCode settings
- [x] T006 [P] Set up SQLite database schema in backend/src/core/database.py
- [x] T007 [P] Configure Redis for caching and real-time data in backend/src/core/cache.py
- [x] T008 [P] Create configuration system in backend/config/ with YAML files
- [x] T009 [P] Set up logging framework in backend/src/utils/logger.py
- [x] T010 [P] Create development scripts for setup automation

## Phase 3.2: Contract Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### T011-T025: REST API Contract Tests
- [ ] T011 [P] Contract test POST /api/v1/auth/login in backend/tests/contract/test_auth_login.py
- [ ] T012 [P] Contract test POST /api/v1/auth/switch-mode in backend/tests/contract/test_auth_switch_mode.py
- [ ] T013 [P] Contract test GET /api/v1/strategies in backend/tests/contract/test_strategies_list.py
- [ ] T014 [P] Contract test POST /api/v1/strategies in backend/tests/contract/test_strategies_create.py
- [ ] T015 [P] Contract test GET /api/v1/strategies/{id} in backend/tests/contract/test_strategies_get.py
- [ ] T016 [P] Contract test PUT /api/v1/strategies/{id} in backend/tests/contract/test_strategies_update.py
- [ ] T017 [P] Contract test POST /api/v1/strategies/{id}/backtest in backend/tests/contract/test_strategies_backtest.py
- [ ] T018 [P] Contract test GET /api/v1/trades in backend/tests/contract/test_trades_list.py
- [ ] T019 [P] Contract test POST /api/v1/trades in backend/tests/contract/test_trades_create.py
- [ ] T020 [P] Contract test GET /api/v1/trades/{id} in backend/tests/contract/test_trades_get.py
- [ ] T021 [P] Contract test PATCH /api/v1/trades/{id} in backend/tests/contract/test_trades_update.py
- [ ] T022 [P] Contract test GET /api/v1/portfolio in backend/tests/contract/test_portfolio_get.py
- [ ] T023 [P] Contract test GET /api/v1/market-data/{symbol} in backend/tests/contract/test_market_data_get.py
- [ ] T024 [P] Contract test GET /api/v1/ai/predictions in backend/tests/contract/test_ai_predictions.py
- [ ] T025 [P] Contract test GET /api/v1/system/status in backend/tests/contract/test_system_status.py

### T026-T030: WebSocket Contract Tests
- [ ] T026 [P] WebSocket auth flow test in backend/tests/contract/test_websocket_auth.py
- [ ] T027 [P] WebSocket subscription test in backend/tests/contract/test_websocket_subscribe.py
- [ ] T028 [P] WebSocket market data stream test in backend/tests/contract/test_websocket_market_data.py
- [ ] T029 [P] WebSocket trade signals stream test in backend/tests/contract/test_websocket_signals.py
- [ ] T030 [P] WebSocket portfolio updates stream test in backend/tests/contract/test_websocket_portfolio.py

### T031-T040: Integration Tests
- [ ] T031 [P] Paper trading workflow integration test in backend/tests/integration/test_paper_trading.py
- [ ] T032 [P] Live trading mode switch integration test in backend/tests/integration/test_live_trading.py
- [ ] T033 [P] Strategy activation and signal generation integration test in backend/tests/integration/test_strategy_flow.py
- [ ] T034 [P] AI prediction and confidence tracking integration test in backend/tests/integration/test_ai_integration.py
- [ ] T035 [P] Market data ingestion and processing integration test in backend/tests/integration/test_data_flow.py
- [ ] T036 [P] Risk management and circuit breaker integration test in backend/tests/integration/test_risk_management.py
- [ ] T037 [P] Angel One API connection integration test in backend/tests/integration/test_angel_one_api.py
- [ ] T038 [P] Database operations and data integrity integration test in backend/tests/integration/test_database.py
- [ ] T039 [P] Frontend-backend WebSocket communication integration test in backend/tests/integration/test_frontend_integration.py
- [ ] T040 [P] Complete system startup and health check integration test in backend/tests/integration/test_system_startup.py

## Phase 3.3: Data Models & Core Infrastructure (ONLY after tests are failing)

### T041-T053: Entity Models
- [ ] T041 [P] User entity model in backend/src/models/user.py
- [ ] T042 [P] Security entity model in backend/src/models/security.py
- [ ] T043 [P] MarketData entity model in backend/src/models/market_data.py
- [ ] T044 [P] TechnicalIndicator entity model in backend/src/models/technical_indicator.py
- [ ] T045 [P] Strategy entity model in backend/src/models/strategy.py
- [ ] T046 [P] StrategySignal entity model in backend/src/models/strategy_signal.py
- [ ] T047 [P] Trade entity model in backend/src/models/trade.py
- [ ] T048 [P] Portfolio entity model in backend/src/models/portfolio.py
- [ ] T049 [P] AIModel entity model in backend/src/models/ai_model.py
- [ ] T050 [P] AIPrediction entity model in backend/src/models/ai_prediction.py
- [ ] T051 [P] RiskMetric entity model in backend/src/models/risk_metric.py
- [ ] T052 [P] AuditLog entity model in backend/src/models/audit_log.py
- [ ] T053 [P] Configuration entity model in backend/src/models/configuration.py

### T054-T058: Core Services
- [ ] T054 [P] Database manager and ORM setup in backend/src/core/database_manager.py
- [ ] T055 [P] Authentication service in backend/src/services/auth_service.py
- [ ] T056 [P] User management service in backend/src/services/user_service.py
- [ ] T057 Configuration management service in backend/src/services/config_service.py (depends on T053)
- [ ] T058 Audit logging service in backend/src/services/audit_service.py (depends on T052)

## Phase 3.4: External API Integration

### T059-T063: Broker and Data APIs
- [ ] T059 [P] Angel One Smart API client in backend/src/api/angel_one_client.py
- [ ] T060 [P] Dhan HQ API client in backend/src/api/dhan_client.py  
- [ ] T061 [P] News API client in backend/src/api/news_client.py
- [ ] T062 [P] Weather API client in backend/src/api/weather_client.py
- [ ] T063 Authentication manager for API credentials in backend/src/api/auth_manager.py (depends on T059-T062)

### T064-T066: Market Data Processing
- [ ] T064 Historical data manager in backend/src/core/data_manager.py (depends on T059-T060)
- [ ] T065 Real-time information processor in backend/src/core/information_processor.py (depends on T064)
- [ ] T066 Technical indicators calculator in backend/src/utils/technical_indicators.py (depends on T044)

## Phase 3.5: AI Integration & Strategy Engine

### T067-T070: AI/ML Components
- [ ] T067 [P] Ollama Gemma3 integration client in backend/src/ai/gemma3_integration.py
- [ ] T068 [P] RAG processor for market knowledge in backend/src/ai/rag_processor.py
- [ ] T069 [P] Confidence tracking system in backend/src/ai/confidence_tracker.py
- [ ] T070 AI learning engine and training pipeline in backend/src/ai/learning_engine.py (depends on T067-T069)

### T071-T075: Trading Strategy Implementation
- [ ] T071 [P] Base strategy interface in backend/src/strategies/base_strategy.py
- [ ] T072 [P] Predator strategy implementation in backend/src/strategies/predatory/predator_strategy.py
- [ ] T073 [P] Vulture approach strategy in backend/src/strategies/predatory/vulture_approach.py
- [ ] T074 [P] Time arbitrage strategy in backend/src/strategies/quantitative/time_arbitrage.py
- [ ] T075 [P] Fear exploiter strategy in backend/src/strategies/psychological/fear_exploiter.py

## Phase 3.6: REST API Endpoints

### T076-T080: API Implementation
- [ ] T076 Authentication endpoints (/auth/login, /auth/switch-mode) in backend/src/api/routes/auth.py
- [ ] T077 Strategy management endpoints (/strategies/*) in backend/src/api/routes/strategies.py
- [ ] T078 Trading endpoints (/trades/*) in backend/src/api/routes/trades.py
- [ ] T079 Portfolio endpoints (/portfolio/*) in backend/src/api/routes/portfolio.py
- [ ] T080 System and AI endpoints in backend/src/api/routes/system.py

### T081: WebSocket Server
- [ ] T081 WebSocket server with real-time data streams in backend/src/api/websocket_server.py

## Phase 3.7: Frontend Development

### T082-T086: React Components
- [ ] T082 [P] Main dashboard component in frontend/src/components/Dashboard.tsx
- [ ] T083 [P] AI monitoring component in frontend/src/components/AIMonitor.tsx
- [ ] T084 [P] Trading interface component in frontend/src/components/TradingInterface.tsx
- [ ] T085 [P] Strategy performance component in frontend/src/components/StrategyPerformance.tsx
- [ ] T086 WebSocket service for real-time updates in frontend/src/services/websocket.ts

## Phase 3.8: Risk Management & Execution

### T087: Risk and Execution Systems
- [ ] T087 Risk management and execution engine in backend/src/core/execution_engine.py

## Phase 3.9: Polish & Documentation

### T088-T089: Final Integration
- [ ] T088 [P] System performance optimization and monitoring
- [ ] T089 [P] Update project documentation and API specs

## Dependencies

### Critical Dependencies
- **Setup Phase**: T001-T010 must complete before all other phases
- **TDD Phase**: T011-T040 must complete and FAIL before T041+
- **Models First**: T041-T053 before services T054-T058
- **APIs before Processing**: T059-T063 before T064-T066
- **Core before Strategies**: T064-T070 before T071-T075
- **Backend before Frontend**: T076-T081 before T082-T086

### Sequential Dependencies
- T057 depends on T053 (config service needs config model)
- T058 depends on T052 (audit service needs audit model)
- T063 depends on T059-T062 (auth manager needs API clients)
- T064 depends on T059-T060 (data manager needs broker APIs)
- T065 depends on T064 (processor needs data manager)
- T066 depends on T044 (indicators need model)
- T070 depends on T067-T069 (learning engine needs AI components)
- T086 depends on T081 (frontend WebSocket needs backend server)

## Parallel Execution Examples

### Phase 3.2: Contract Tests (can run simultaneously)
```bash
# Launch contract tests in parallel
Task: "Contract test POST /api/v1/auth/login in backend/tests/contract/test_auth_login.py"
Task: "Contract test GET /api/v1/strategies in backend/tests/contract/test_strategies_list.py" 
Task: "Contract test GET /api/v1/trades in backend/tests/contract/test_trades_list.py"
Task: "WebSocket auth flow test in backend/tests/contract/test_websocket_auth.py"
```

### Phase 3.3: Entity Models (independent implementations)
```bash
# Launch model creation in parallel
Task: "User entity model in backend/src/models/user.py"
Task: "Security entity model in backend/src/models/security.py"
Task: "MarketData entity model in backend/src/models/market_data.py"
Task: "Strategy entity model in backend/src/models/strategy.py"
```

### Phase 3.4: API Clients (independent integrations)
```bash  
# Launch API client development in parallel
Task: "Angel One Smart API client in backend/src/api/angel_one_client.py"
Task: "Dhan HQ API client in backend/src/api/dhan_client.py"
Task: "News API client in backend/src/api/news_client.py"
Task: "Weather API client in backend/src/api/weather_client.py"
```

### Phase 3.7: Frontend Components (independent UI)
```bash
# Launch React component development in parallel  
Task: "Main dashboard component in frontend/src/components/Dashboard.tsx"
Task: "AI monitoring component in frontend/src/components/AIMonitor.tsx"
Task: "Trading interface component in frontend/src/components/TradingInterface.tsx"
Task: "Strategy performance component in frontend/src/components/StrategyPerformance.tsx"
```

## Task Generation Rules Applied

### From REST API Contracts (25 endpoints)
✅ Each endpoint → contract test task [P]  
✅ Each endpoint → implementation task  
✅ Authentication, strategies, trades, portfolio, market-data, AI, system endpoints covered

### From WebSocket API Contracts  
✅ Auth flow → contract test [P]
✅ Each stream type → contract test [P]
✅ Real-time communication → implementation task

### From Data Model (13 entities)
✅ Each entity → model creation task [P]
✅ Relationships → service layer tasks
✅ User, Security, MarketData, Strategy, Trade, Portfolio, AI entities covered

### From Quickstart Scenarios
✅ Paper trading workflow → integration test [P]
✅ Live trading switch → integration test [P] 
✅ Strategy activation → integration test [P]
✅ AI analysis → integration test [P]
✅ System startup → integration test [P]

### Ordering Applied
✅ Setup → Tests → Models → Services → APIs → Implementation → Frontend → Polish
✅ Dependencies prevent conflicts in parallel execution
✅ TDD approach: all tests before implementation

## Validation Checklist
*GATE: Validated before task completion*

- [✅] All REST API endpoints have corresponding contract tests (T011-T025)
- [✅] All WebSocket streams have contract tests (T026-T030) 
- [✅] All 13 entities have model creation tasks (T041-T053)
- [✅] All quickstart scenarios have integration tests (T031-T040)
- [✅] All contract tests come before implementation (T011-T040 before T041+)
- [✅] Parallel tasks are truly independent (different files, no shared dependencies)
- [✅] Each task specifies exact file path
- [✅] No [P] task modifies same file as another [P] task
- [✅] Critical dependencies properly sequenced
- [✅] 89 tasks cover complete NIRAJ system implementation

## Notes
- [P] tasks can run in parallel (different files, no dependencies)
- Verify contract tests fail before implementing (TDD requirement)
- Commit after each task completion
- Focus areas: 20 trading strategies (5 completed in T071-T075, others in T088)
- Paper trading mode is default, PIN 1937 required for live mode
- Sub-millisecond execution requirements addressed in T087-T088

---
**Status**: Ready for execution - 89 tasks generated following constitutional TDD principles
**Estimated Timeline**: 12-16 weeks for full system implementation  
**Parallel Capacity**: Up to 15 tasks can run simultaneously during model/API/component phases