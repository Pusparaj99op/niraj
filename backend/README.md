# NIRAJ Backend

Advanced Self-Learning Algorithmic AI Personal Trading System - Backend

## Features

- FastAPI web framework
- SQLAlchemy ORM with SQLite
- Redis for caching and real-time data
- JWT authentication
- WebSocket support for real-time updates
- AI integration with Ollama Gemma3
- Multiple trading strategies
- Paper and live trading modes

## Setup

1. Install dependencies: `poetry install`
2. Run the development server: `poetry run uvicorn src.main:app --reload`

## Project Structure

- `src/` - Main application code
- `tests/` - Test files (contract and integration tests)
- `config/` - Configuration files
- `scripts/` - Development automation scripts