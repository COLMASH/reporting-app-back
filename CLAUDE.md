# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI backend for Excel file analysis using AI agents. Provides authentication and API endpoints for a Next.js frontend.

## Key Development Commands

```bash
# Environment setup
uv sync                                    # Install dependencies
uv run uvicorn src.main:app --reload      # Start dev server

# Code quality
uv run check                              # Lint + type check
uv run format                             # Auto-format
uv run build                              # Full check: lint + type + tests

# Database
uv run alembic upgrade head               # Apply migrations
uv run alembic revision --autogenerate -m "description"  # Create migration
```

## Architecture & Key Patterns

### CRITICAL: Avoid OOP for Major Logic
**This project MUST avoid Object-Oriented Programming patterns for major business logic.** Use functional programming approaches instead:
- Prefer pure functions over classes with state
- Use data classes/TypedDicts for data structures only
- Keep logic in simple functions that transform data
- Avoid inheritance hierarchies and complex class structures

**EXCEPTION: The following files are ALLOWED to use Python classes:**
- Core infrastructure files:
  - `src/core/middleware/logging.py` - Middleware classes
  - `src/core/config.py` - Settings configuration class
  - `src/core/exceptions.py` - Exception class hierarchy
  - `src/core/storage.py` - Storage client class (for encapsulation)
- In modules folder ONLY:
  - `**/models.py` - SQLAlchemy database models
  - `**/schemas.py` - Pydantic validation schemas

All other files, especially `service.py` files, MUST use functional programming.

### Module Structure
- `controller.py` - HTTP endpoints (like NestJS controllers)
- `service.py` - Business logic (use simple functions, NOT classes)
- `schemas.py` - Pydantic schemas for validation
- `models.py` - SQLAlchemy database models
- `dependencies.py` - FastAPI dependency injection (optional)

### Database Rules
- **ALL tables MUST use UUID primary keys**
- Auth tables maintain NextAuth.js-compatible column names
- Foreign keys must reference UUID types

### Authentication
- No automatic user creation - must use `/auth/signup` endpoint  
- First user becomes admin automatically
- JWT structure: `{email, sub, name, picture, id, exp, iat}`
- Always use `CurrentUser` dependency for protected routes

## Critical Implementation Notes

### When Adding New Endpoints
- Add router to `src/core/api.py` register_routes()
- Follow pattern: controller → service (with direct DB access)
- Use exceptions from `src/core/exceptions.py`
- Rate limiting: 100 req/min (works without Redis)

### When Creating New Database Models

**IMPORTANT: Models must be imported in 2 places for SQLAlchemy to work properly**

1. Create the model in the appropriate module's `models.py`:
```python
import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from src.core.database.core import Base

class NewModel(Base):
    __tablename__ = "new_model"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ... other columns
```

2. Import the model in **BOTH** of these files:
   - `src/main.py` - Add to the "Import all entities" section with `# noqa: F401`
   - `migrations/env.py` - Add import for Alembic to detect the model

3. Generate migration:
```bash
uv run alembic revision --autogenerate -m "Add NewModel"
```

Example: If adding a `Comment` model to `src/modules/reporting_results/models.py`:
- In `src/main.py`: `from src.modules.reporting_results.models import ChartType, Comment, Result  # noqa: F401`
- In `migrations/env.py`: `from src.modules.reporting_results.models import Comment`

### Environment Configuration
- Uses single `.env` file for simplicity
- `APP_DEBUG` instead of `DEBUG` (avoids IDE conflicts)
- URL-encode special chars in DATABASE_URL (@ → %40)
- Production values set in Render dashboard

### Deployment
- Manual Render setup (no render.yaml)
- Different env vars per branch
- `build.sh` runs migrations during deployment
- Swagger disabled in production

## Not Yet Implemented

These exist in config/models but have no implementation:
- Supabase file storage
- AI agents (LangGraph)
- Celery background tasks
- File upload size/extension validation

## Common Pitfalls

1. **Database URLs**: Always URL-encode special characters
2. **UUID Keys**: Never use auto-increment IDs
3. **Auth**: Don't create users from JWT tokens
4. **Redis**: Optional - rate limiting works without it
5. **Swagger**: Disabled in production by default