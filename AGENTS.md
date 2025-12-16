# Multi-Region PostgreSQL Testing Dashboard - Agent Guidelines

## Build Commands
- **Setup**: `just setup` - Install dev dependencies and create .env file
- **Dev Server**: `just dev` - Run development server with reload
- **Database Setup**: `just db-setup` - Create tables and populate initial data via `setup_database.py`
- **Format**: `just format` - Format code with black (line-length: 100)
- **Lint**: `just lint` - Run ruff checks
- **Type Check**: `just typecheck` - Run mypy type checking
- **All Checks**: `just check` - Run lint + typecheck
- **Clean**: `just clean` - Remove Python cache files

## Database Schema Management
- **NO Migrations**: This project does NOT use migrations or SQL migration files
- **Schema Changes**: Edit `setup_database.py` directly to add/modify tables
- **Apply Changes**: Run `just db-setup` to apply schema changes
- **Safe Re-runs**: Uses `CREATE TABLE IF NOT EXISTS` for idempotent execution
- **Backend Database Extensions** (application storage):
  - **TimescaleDB**: For time-series data (connection test history stored in hypertables)
  - **pg_stat_statements**: For query performance monitoring
  - **Docker Database**: Start with `docker compose --profile postgres up -d` (PostgreSQL 15 with extensions pre-installed)
- **Target Database Extensions** (databases being monitored):
  - **pg_stat_statements**: Recommended for comprehensive health checks with query performance metrics
  - **Without extension**: Health checks still work but return limited metrics (basic stats only)

## Code Style Guidelines
- **Formatting**: Black with 100 character line length
- **Imports**: Use ruff/isort, first-party imports: `app`
- **Type Hints**: Use modern union syntax (`str | None`), mypy in strict mode with some relaxations
- **Error Handling**: Use FastAPI's built-in error responses, graceful degradation for feature flags
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Async**: Use async/await throughout, all database operations are async
- **Environment**: Use .env file, never commit secrets, use dataclasses for config
- **Dependencies**: Add with `just add <package>` or `just add-dev <package>` for dev dependencies