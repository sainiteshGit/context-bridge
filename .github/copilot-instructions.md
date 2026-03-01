# Context Bridge — Copilot Instructions

## Project Overview

Context Bridge is a **personal, user-owned context layer** — SSO for your life context across AI apps.
It is a **personal consumer product only** — no enterprise features, no multi-tenancy, no revenue model.

## Architecture

Clean Architecture with SOLID principles. Every layer depends on abstractions, not implementations.

```
Browser Extension → FastAPI API → Context Broker → Services → Ports (ABCs) → Adapters
```

### Layer Rules

| Layer | Location | Rule |
|-------|----------|------|
| **Models** | `src/context_bridge/core/models/` | Pure Pydantic v2 data classes. No business logic. No I/O. |
| **Ports** | `src/context_bridge/core/ports/` | Abstract base classes (ABCs). Define storage/provider interfaces. |
| **Services** | `src/context_bridge/core/services/` | Business logic. Depend ONLY on ports (injected). No framework imports. |
| **Broker** | `src/context_bridge/broker/` | Orchestration + consent enforcement. Mediator between services. |
| **Adapters** | `src/context_bridge/adapters/` | Implement ports. Currently: `memory/` (dev) and `cosmosdb/` (prod). |
| **Protocol** | `src/context_bridge/protocol/` | JWT auth, token service. |
| **API** | `src/context_bridge/api/` | FastAPI routes, DI, app factory. Thin layer — delegates to broker/services. |
| **Config** | `src/context_bridge/config.py` | pydantic-settings. Single source of truth for all settings. |
| **Extension** | `extension/` | Chrome MV3 browser extension. Shadow DOM for React-hostile sites. |

### Key Design Decisions

- **Storage is swappable**: In-memory for dev/test, Azure Cosmos DB for production. Add new adapters by implementing the port ABCs.
- **Consent enforcement**: The broker enforces consent on every cross-app operation. Services don't know about consent.
- **Shadow DOM**: The content script uses Shadow DOM so React (ChatGPT) and Perplexity can't clobber injected UI.
- **Python 3.9 compatibility**: Use `from __future__ import annotations` in every file. The `eval_type_backport` package handles `X | None` syntax at runtime.

## Code Conventions

### Python

- **Python 3.9+** — always use `from __future__ import annotations` at the top of every `.py` file
- **Pydantic v2** — use `model_config = ConfigDict(...)` not `class Config:`
- **Type hints everywhere** — strict mypy is enabled
- **Ruff** for linting — line length 100, target py39
- **async/await** — services and adapters are async
- **Tests** — pytest + pytest-asyncio with `asyncio_mode = auto`

### Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Enums: class `PascalCase`, members `UPPER_SNAKE_CASE`

### Imports

- Standard library first, then third-party, then local — Ruff enforces this
- Use absolute imports from `context_bridge.*`

## Domain Model

### Context Categories

`PROFILE`, `FITNESS`, `FAMILY`, `FOOD`, `HOME`, `PET`, `FINANCE`, `TRAVEL`, `HOBBY`, `HEALTH`

### Sensitivity Levels

`LOW` → `MEDIUM` → `HIGH` → `CRITICAL` (ordered, supports `<=` comparison)

### Core Entities

- **User** — profile with display name, email, timezone
- **ContextFact** — a single piece of personal context (category, sensitivity, value, tags, source, confidence, expiry)
- **ContextSnapshot** — summary view of facts in a category
- **ConsentGrant** — permission for an app to access specific categories up to a max sensitivity
- **ConnectedApp** — registered third-party AI app
- **AuditEntry** — immutable log of every context access

## Browser Extension

- **Manifest V3** — Chrome only for now
- **content.js** — Injects on chatgpt.com, chat.openai.com, perplexity.ai. Uses Shadow DOM.
- **background.js** — Handles API calls to the Context Bridge server
- **popup.js** — Connection settings, stats, quick-add form
- `findChatInput()` — Handles ProseMirror (ChatGPT), textarea (Perplexity), contenteditable, and fallback textarea
- Context injection uses `document.execCommand('insertText')` for contenteditable or React's native value setter for textareas

## Running the Project

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run API (in-memory storage)
uvicorn context_bridge.main:app --reload

# Seed data
python samples/seed.py

# Run tests
pytest

# Run demo (standalone, no server needed)
python samples/demo.py
```

## Storage Backend Switching

Set `STORAGE_BACKEND=memory` or `STORAGE_BACKEND=cosmosdb` in `.env`.
For Cosmos DB, also set `COSMOS_ENDPOINT`, `COSMOS_KEY`, and `COSMOS_DATABASE`.

## Testing

- Unit tests in `tests/unit/` — use in-memory adapters, no external deps
- Integration tests in `tests/integration/` — for Cosmos DB and API tests
- All tests are async — pytest-asyncio with auto mode
- 27 tests currently, all passing

## What NOT to Add

- No enterprise/multi-tenant features
- No revenue model or pricing
- No roadmap in README
- No unnecessary abstractions — keep it simple and personal
