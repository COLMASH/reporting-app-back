# Reporting Backend

FastAPI backend for Excel file analysis and reporting with AI agents, designed to work with a Next.js frontend using NextAuth v5.

## 🏗️ Architecture

This project follows clean architecture principles with a clear separation of concerns:

- **Controllers**: Handle HTTP requests and responses (similar to NestJS controllers)
- **Services**: Business logic and orchestration
- **Models/Schemas**: Data validation with Pydantic (like DTOs in NestJS)
- **Entities**: Database models with SQLAlchemy (compatible with NextAuth.js schema)
- **Integrations**: External services (Supabase, Celery, AI)

## 🚀 Tech Stack

- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens (NextAuth.js v5 compatible)
- **File Storage**: Supabase Storage
- **Background Tasks**: Celery with Redis
- **AI/LLM**: LangChain and LangGraph
- **Package Manager**: UV (modern Python package manager)

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL (or Supabase account)
- Redis (for background tasks)
- UV package manager

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone <repo-url>
cd reporting-back
```

### 2. Install UV (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Create virtual environment and install dependencies
```bash
# UV will create a .venv directory
uv sync
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration (Supabase keys, JWT secret, etc.)
```

### 5. Run database migrations
```bash
# Make sure PostgreSQL is running
uv run alembic upgrade head
```

### 6. Start the development server
```bash
uv run uvicorn src.main:app --reload
# API will be available at http://localhost:8000
```

## 🐳 Using Docker

```bash
# Start all services (PostgreSQL, Redis, FastAPI, Celery)
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📁 Project Structure

```
reporting-back/
├── src/
│   ├── api.py                 # Route registration
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Environment configuration
│   ├── exceptions.py         # Custom exceptions
│   ├── logging.py           # Logging setup
│   ├── auth/                # Authentication module
│   │   ├── controller.py    # Auth endpoints
│   │   ├── service.py      # JWT validation logic
│   │   └── models.py       # Auth schemas
│   ├── files/              # File management module
│   ├── analysis/           # Analysis processing
│   ├── results/            # Analysis results
│   ├── entities/           # SQLAlchemy models
│   ├── integrations/       # External services
│   └── agents/             # AI/LangGraph agents
├── migrations/             # Alembic database migrations
├── tests/                  # Test suite
├── .env.example           # Environment variables template
├── pyproject.toml         # Project dependencies and scripts
├── alembic.ini           # Migration configuration
├── Dockerfile            # Container configuration
└── docker-compose.yml    # Local development setup
```

## 👨‍💻 Development

### Available Commands

```bash
# Check code quality (like npm run build)
uv run check

# Auto-format code
uv run format

# Run tests
uv run test

# Full build check (lint + type check + tests)
uv run build
```

### Code Quality Tools

```bash
# Linting
uv run ruff check src tests

# Type checking
uv run mypy src

# Code formatting
uv run black src tests
uv run ruff format src tests
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "Add new table"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_auth_service.py

# Run tests in watch mode
uv run pytest-watch
```

## 🚀 Deployment

The application is configured for deployment on Render using Docker.

1. Push to GitHub
2. Connect repository to Render
3. Deploy using the Dockerfile
4. Set environment variables in Render dashboard

### Required Environment Variables

See `.env.example` for all required environment variables.

**Essential variables**:
- `DATABASE_URL`: PostgreSQL connection string
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `JWT_SECRET`: Secret for JWT tokens (must match NextAuth)
- `REDIS_URL`: Redis connection string

**AI Configuration**:
- `OPENAI_API_KEY`: OpenAI API key for LangChain
- `LANGCHAIN_API_KEY`: LangSmith API key (optional)

## 🔧 Troubleshooting

### Common Issues

1. **Import errors when running the app**
   ```bash
   # Make sure you're in the virtual environment
   source .venv/bin/activate  # Linux/Mac
   # or
   uv run uvicorn src.main:app --reload
   ```

2. **Database connection errors**
   ```bash
   # Check PostgreSQL is running
   docker-compose up db
   # Or use local PostgreSQL
   ```

3. **UV sync fails**
   ```bash
   # Clear UV cache and retry
   uv cache clean
   uv sync
   ```

## 📝 License

This project is proprietary and confidential.