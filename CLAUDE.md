# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI backend for Excel file analysis using AI agents, designed to work with a Next.js frontend using NextAuth v5. The architecture follows clean architecture principles similar to NestJS but implemented in Python.

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

### Database Schema (NextAuth Compatible)
The database includes NextAuth v5 required tables:
- `users` (id as Integer, not UUID)
- `accounts`, `sessions`, `verification_token`

Application tables use UUID primary keys:
- `file_uploads` - Tracks Excel files with company/department metadata
- `analyses` - Processing jobs with agent type and progress tracking
- `results` - Charts, insights, and metrics from analysis

### Authentication Flow
1. Frontend sends NextAuth JWT in Authorization header
2. Backend validates JWT with shared secret
3. Auto-creates users from valid tokens
4. Uses dependency injection: `CurrentUser` for protected routes

### File Processing Pipeline
1. Upload → Supabase storage (`/api/v1/files/upload`)
2. Create analysis job (`/api/v1/analysis/`)
3. Celery worker processes with LangGraph agents
4. Results stored with chart data and insights
5. Frontend polls or uses WebSocket for progress

## Critical Implementation Notes

### When Working with Authentication
- JWT validation expects NextAuth token structure (email, sub, name, picture)
- User ID in NextAuth tables is Integer, not UUID
- Always use `CurrentUser` dependency for auth routes
- Development login endpoint available at `/api/v1/auth/dev/login`

### When Adding New Endpoints
- Add router to `src/api.py` register_routes()
- Follow existing pattern: controller → service → repository
- Use appropriate exceptions from `src/exceptions.py`
- Rate limiting is applied globally (100 req/min)

### When Modifying Database Models
- Run `uv run alembic revision --autogenerate -m "description"`
- NextAuth tables should maintain compatibility
- Use UUID for new application tables
- Add relationships in entity files

### Environment Variables
Essential for running:
- `DATABASE_URL` - PostgreSQL connection
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` - File storage
- `JWT_SECRET` - Must match NextAuth configuration
- `REDIS_URL` - For Celery background tasks

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