# Scripts

This folder contains all scripts for development, operations, and build tasks.

## Available Scripts

### check_db_connection.py
Tests the database connection and lists all tables.

```bash
uv run python scripts/check_db_connection.py
```

### check_env_vars.py
Verifies environment variables are loaded correctly.

```bash
uv run python scripts/check_env_vars.py
```

### build_scripts.py
Contains build and development commands used by UV:
- `uv run check` - Run code quality checks
- `uv run format` - Format code with black and ruff
- `uv run test` - Run tests with pytest
- `uv run build` - Run all checks and tests

## Naming Convention

- `check_*` - Diagnostic/verification scripts
- `setup_*` - Initialization/setup scripts  
- `migrate_*` - Data migration scripts
- `build_*` - Build and development scripts

## Adding New Scripts

1. Create script in this folder
2. Add path imports at the top:
   ```python
   import sys
   from pathlib import Path
   sys.path.append(str(Path(__file__).parent.parent))
   ```
3. Document in this README