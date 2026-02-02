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

### Deployment (GCP Compute Engine)

| | DEV | PROD |
|---|-----|------|
| **Instance** | `malatesta-dev-server` | `malatesta-prod-server` |
| **Branch** | `develop` | `master` |
| **Zone** | `us-central1-a` | `us-central1-a` |

**User**: `proyecto_ai_ilv`
**App Path**: `/home/proyecto_ai_ilv/reporting-app-back`
**Services**: `reporting-backend`, `cloudflared` (systemd)
**Port**: `8000`

**CI/CD**: GitHub Actions auto-deploys on push
- `develop` → DEV server (`.github/workflows/deploy-develop.yml`)
- `master` → PROD server (`.github/workflows/deploy-production.yml`)

**HTTPS**: Cloudflare Tunnel (free tier - URL changes on service restart)
- Get URL: `sudo journalctl -u cloudflared | grep "trycloudflare.com" | tail -1`
- After restart: Update Vercel env vars with new URL

**Service Management**:
- Status: `sudo systemctl status reporting-backend`
- Logs: `sudo journalctl -u reporting-backend -f`
- Restart: `sudo systemctl restart reporting-backend`

**Quick Commands**: See `docs/GCP_COMMANDS.md`

**Chosen Over Render/Cloud Run**: Need SSH access and file system for 'Claude Agent SDK' integration which use 'Claude Code' file system tools under the hood

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
5. **Swagger**: Enabled in all environments (`/docs` and `/redoc`)

## Portfolio ETL

### Important Excel Sheets
Only these sheets are used for portfolio data import:
- `Various/StructuredNotes` - All non-Real Estate assets
- `RealEstate` - Real Estate assets with extension data

### Real Estate Field Normalization
Real Estate uses different column names for equivalent financial concepts. During ETL, these are normalized to Asset table fields:

| Excel Column (Real Estate) | Asset Field | Description |
|---------------------------|-------------|-------------|
| `equity_investment_to_date_usd/eur` | `paid_in_capital_usd/eur` | Cost basis |
| `estimated_capital_gain_usd/eur` | `realized_gain_usd/eur` | Realized gain |
| `unrealized_gain_usd/eur` | `unrealized_gain_usd/eur` | Direct import |

The original values are also stored in the `RealEstateAsset` extension table for Real Estate-specific views.

### ETL Scripts
- **Production**: `scripts/migrate_portfolio_data.py`
- **Development**: `scripts/migrate_portfolio_data_dev.py` (supports multiple report dates)