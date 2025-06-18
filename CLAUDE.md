# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI backend for Excel file analysis using AI agents. It provides authentication and API endpoints for a Next.js frontend. The architecture follows clean architecture principles similar to NestJS but implemented in Python.

## Key Development Commands

```bash
# Environment setup
uv sync                                    # Install dependencies (creates .venv)
uv run uvicorn src.main:app --reload      # Start dev server

# Code quality checks (like npm run build)
uv run check                              # Run linting and type checking
uv run format                             # Auto-format code
uv run build                              # Full check: lint + type check + tests

# Database operations
uv run alembic upgrade head               # Apply migrations
uv run alembic revision --autogenerate -m "description"  # Create migration

# Docker development
docker-compose up                         # Start all services
docker-compose up db redis                # Start only databases
```

## Architecture & Key Patterns

### Module Structure
Each feature module follows this pattern:
- `controller.py` - HTTP endpoints (like NestJS controllers)
- `service.py` - Business logic
- `models.py` - Pydantic schemas for validation (like DTOs)

### Database Schema
All tables use UUID primary keys for consistency and security:
- `users` - User accounts with authentication
- `accounts`, `sessions`, `verification_token` - Auth-related tables (NextAuth.js compatible schema)
- `file_uploads` - Tracks Excel files with company/department metadata
- `analyses` - Processing jobs with agent type and progress tracking
- `results` - Charts, insights, and metrics from analysis

### Authentication Flow
1. Backend provides `/auth/signup` and `/auth/login` endpoints
2. Frontend sends JWT in Authorization header
3. Backend validates JWT with shared secret
4. Users must exist in database (no auto-creation)
5. Uses dependency injection: `CurrentUser` for protected routes
6. First user automatically becomes admin
7. Subsequent users require admin authentication to create

### File Processing Pipeline
1. Upload → Supabase storage (`/api/v1/files/upload`)
2. Create analysis job (`/api/v1/analysis/`)
3. Celery worker processes with LangGraph agents
4. Results stored with chart data and insights
5. Frontend polls or uses WebSocket for progress

## Critical Implementation Notes

### When Working with Authentication
- Backend generates and validates all JWT tokens
- JWT token structure includes: email, sub, name, picture, id (as UUID string), exp, iat
- Users must be created via `/api/v1/auth/signup` endpoint (admin-only after first user)
- First user automatically becomes admin
- Login endpoint at `/api/v1/auth/login` for password-based auth
- Always use `CurrentUser` dependency for auth routes
- No automatic user creation from JWT tokens

### When Adding New Endpoints
- Add router to `src/api.py` register_routes()
- Follow existing pattern: controller → service → repository
- Use appropriate exceptions from `src/exceptions.py`
- Rate limiting is applied globally (100 req/min)

### When Modifying Database Models
- Run `uv run alembic revision --autogenerate -m "description"`
- ALL tables use UUID primary keys (UUID type with default=uuid.uuid4)
- Auth tables (`users`, `accounts`, `sessions`, `verification_token`) maintain NextAuth.js-compatible column names
- Foreign keys must reference UUID types
- Add relationships in entity files

### Environment Variables
Essential for running:
- `DATABASE_URL` - PostgreSQL connection (URL-encode special characters like @ as %40)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` - File storage
- `JWT_SECRET` - Shared secret for JWT token generation/validation
- `REDIS_URL` - For Celery background tasks
- `APP_DEBUG` - Debug mode (not DEBUG to avoid conflicts with VS Code/Cursor)

## Integration Points

### Supabase Integration
- Storage client configured in `src/integrations/supabase.py`
- Files stored in bucket specified in entity (default: "excel-files")
- Path format: `{user_id}/{company_name}/{filename}`

### AI Agent Architecture
- Base agent class in `src/agents/base.py`
- LangGraph for workflow orchestration
- Agent types: excel_analyzer, chart_recommender, data_classifier
- Results include chart_type, chart_data, chart_config for frontend rendering

### Background Task Processing
- Celery worker required for file analysis
- Redis as message broker
- Monitor with Flower at http://localhost:5555
- Task status tracked in `analysis.celery_task_id`

## Common Development Scenarios

### Adding a New Analysis Agent
1. Create agent in `src/agents/`
2. Add to `AgentType` enum in `src/entities/analysis.py`
3. Register in agent registry
4. Update analysis service to handle new type

### Testing with Real Files
- Max file size: 50MB (configurable)
- Allowed extensions: .xlsx, .xls
- Test files should include company_name and data_classification
- Use docker-compose for full stack testing

### Debugging AI Processing
- Set `LANGCHAIN_TRACING_V2=true` for LangSmith traces
- Check Celery logs: `docker-compose logs celery`
- Analysis progress tracked in database (0.0 to 1.0)

## Project Structure Notes

### Scripts Organization
All utility and build scripts are in the `scripts/` folder:
- `check_db_connection.py` - Test database connectivity
- `check_env_vars.py` - Verify environment variables
- `build_scripts.py` - UV build commands (check, format, test, build)

### Important Configuration Details
- The app uses `APP_DEBUG` instead of `DEBUG` to avoid conflicts with IDE environment variables
- Database passwords with special characters (like @) must be URL-encoded in DATABASE_URL
- Supabase pooler connections require the project reference in the username format

### When Creating New Entities
All new entities MUST use UUID primary keys:
```python
import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

class NewEntity(Base):
    __tablename__ = "new_entity"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ... other columns
```

Foreign keys to other tables must also use UUID type:
```python
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
```