# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
just dev              # Start development server with auto-reload
just serve            # Run production server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality
```bash
just format           # Format code with black (100 char line length)
just lint             # Lint with ruff
just typecheck        # Type check with mypy
just check            # Run all checks (lint + typecheck)
```

### Database Setup
```bash
just db-setup         # Create tables and populate initial data
uv run python setup_database.py
```

**Note**: This project does not use Alembic. Database schema changes are made directly via `setup_database.py`.

### Dependency Management
```bash
just add <package>      # Add production dependency
just add-dev <package>  # Add dev dependency
just install            # Install dependencies
just install-dev        # Install with dev dependencies
uv sync                 # Sync all dependencies from pyproject.toml
```

### Setup
```bash
just setup            # Full setup: install deps and create .env
just setup-env        # Copy .env.example to .env
```

## Database Requirements

### Backend Database (Application Storage)

The PostgreSQL backend requires a database with the following extensions enabled:

- **TimescaleDB**: Time-series database extension for storing connection test history in hypertables
- **pg_stat_statements**: Query performance statistics for monitoring

#### Local Development Database

Use the included Docker Compose setup:
```bash
docker compose --profile postgres up -d
```

This starts PostgreSQL 15 with TimescaleDB and pg_stat_statements pre-installed.

#### Production/Remote Database

Ensure your PostgreSQL database has these extensions enabled:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

Then run the database setup script to create tables:
```bash
just db-setup
```

### Target Databases (External Databases Being Monitored)

The external PostgreSQL databases that you add to the dashboard for monitoring should have:

- **pg_stat_statements**: Required for comprehensive health checks and query performance metrics

**Without pg_stat_statements**: Health checks will still work but will return limited data:
- Basic metrics (cache hit ratio, connections, database size) will still be available
- Query performance statistics will be unavailable
- Health check responses will show `pg_stat_statements_available: false`

To enable on target databases:
```sql
-- Add to postgresql.conf
shared_preload_libraries = 'pg_stat_statements'

-- After restart, create extension in each database
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

## Architecture Overview

### PostgreSQL Backend

The application uses PostgreSQL for storing connection metadata and test history:

- Stores connections in PostgreSQL database
- **Required PostgreSQL extensions**: TimescaleDB (for connection test history), pg_stat_statements (for query monitoring)
- Uses bcrypt for password hashing
- Requires DATABASE_URL environment variable
- Supports concurrent users and scaling
- Schema managed via `setup_database.py` (no Alembic/migrations)
- Connection test results stored in TimescaleDB hypertable for time-series analysis

### Key Architectural Patterns

**HTMX-driven Frontend**:
- Server-side rendered HTML partials in `app/templates/partials/`
- HTMX triggers for UI updates: `connection-created`, `connection-test-failed`, `connection-error`
- All API endpoints return HTML templates, not JSON (except where noted)
- Auto-refresh achieved via HX-Trigger headers

**Database Connection Testing**:
- The app manages and tests connections to *external* PostgreSQL databases
- Backend database (for storing connection metadata) is separate from tested connections
- The `test_connection()` method validates external DB connectivity
- Health checks query pg_stat_statements on target databases for comprehensive metrics
- Target databases without pg_stat_statements will return basic metrics only

**Security Model**:
- Password hashing: bcrypt (rounds=12)
- SSL handling: Automatic detection - require SSL for remote hosts, disable for localhost
- Never expose plaintext passwords in API responses

**Async Design**:
- All database operations use async/await
- Connection pool management via asyncpg
- FastAPI lifespan context manager in `app/main.py`

## Critical Implementation Details

### Database Column Names
The database uses `database_name` column, not `database`. When writing queries, always use:
```python
# Correct
await conn.execute("SELECT database_name FROM database_connections WHERE id = $1", conn_id)

# Incorrect - will fail
await conn.execute("SELECT database FROM database_connections WHERE id = $1", conn_id)
```

### HTMX Response Pattern
When creating/updating connections, return HTML partials with HX-Trigger headers:
```python
return templates.TemplateResponse(
    "partials/connection_result.html",
    {"request": request, "result": test_result},
    headers={"HX-Trigger": "connection-created"}  # Triggers frontend refresh
)
```

### Password Handling
- Store `password_hash` and `salt`, never store plaintext
- Testing connections requires plaintext password, but it's never persisted

### SSL Context Creation
When testing connections, SSL is auto-detected:
```python
use_ssl = not any(
    local_host in connection.host.lower()
    for local_host in ["localhost", "127.0.0.1", "postgres"]
)
```

## Project Structure

```
app/
├── main.py                      # FastAPI app, router configuration
├── config.py                    # Database configuration (DATABASE_URL)
├── db_manager_postgres.py       # PostgreSQL-based connection manager
├── location_service.py          # Geographic distance calculations
├── routers/
│   ├── api.py                   # Health checks, connection tests
│   ├── db_management_postgres.py # PostgreSQL backend CRUD endpoints
│   └── pages.py                 # HTML page routes
├── templates/
│   ├── base.html                # Base template with HTMX
│   ├── index.html               # Main dashboard
│   └── partials/                # HTMX-swappable components
│       ├── connection_form.html
│       ├── database_connections.html
│       └── connection_result.html
└── static/                      # CSS, JS assets
```

## Environment Configuration

Required environment variables (in `.env`):
```env
DATABASE_URL=postgresql://user:password@host:port/dbname
```

The app uses `python-dotenv` to load `.env` automatically.

## Database Schema Management

This project does NOT use Alembic or SQLAlchemy migrations. Schema changes are made directly:

1. Edit `setup_database.py` to add/modify tables
2. Run `just db-setup` to apply changes
3. The script uses `CREATE TABLE IF NOT EXISTS` for safe re-runs

Current schema includes:
- `database_connections` table: stores managed database connection metadata
- `locations` table: geographic coordinates for cloud provider regions

## Code Style

- **Line length**: 100 characters (black + ruff)
- **Type hints**: Use modern union syntax (`str | None`, not `Optional[str]`)
- **Async**: Prefer async/await for all I/O operations
- **Error handling**: FastAPI HTTPException with proper status codes
- **Imports**: Sorted with isort (ruff handles this)

## Frontend Patterns

### HTMX Event Flow
1. User submits form → POST `/api/db/connections`
2. Backend saves connection, tests it, returns HTML partial
3. HTMX receives response with `HX-Trigger: connection-created`
4. Frontend listens for trigger, refreshes connections list
5. New connection appears without page reload

### Alpine.js Usage
Used for client-side interactivity:
- Map rendering with Leaflet
- Form state management
- Modal dialogs

## Known Issues and Gotchas

1. **HTMX refresh on test failure**: Connections save successfully but list doesn't auto-refresh when connection test fails (only triggers on success). The `connection-test-failed` trigger exists but may need frontend listener.

2. **Column name mismatches**: Database uses `database_name` in SQL but `database` in Python dataclass. Always map correctly when reading from DB.

3. **JavaScript quote escaping**: HTMX triggers with JavaScript in header values need proper escaping.

4. **SSL certificate verification**: Currently disabled (`ssl_context.verify_mode = ssl.CERT_NONE`) for testing - should be enabled in production.

## Testing Connections

The `test_connection()` method establishes a real connection to external PostgreSQL databases and runs:
```sql
SELECT
    inet_server_addr()::text AS server_ip,
    pg_backend_pid() AS backend_pid,
    version() AS pg_version
```

This validates:
- Credentials are correct
- Network connectivity works
- Database is reachable
- Measures latency (round-trip time)

## Health Checks

The `get_connection_health_metrics()` function performs comprehensive health checks on target databases:

**Always Available Metrics** (no extensions required):
- Cache hit ratio (from pg_stat_database)
- Active/idle/total connections (from pg_stat_activity)
- Database size (from pg_database_size)

**Extended Metrics** (requires pg_stat_statements):
- Top 10 queries by call count
- Query execution time statistics (total, mean, max)
- Per-query cache hit percentages
- Shared buffer hits and reads

If pg_stat_statements is not available on the target database:
- Health check still succeeds
- Returns `pg_stat_statements_available: false`
- Includes warning in response
- Basic metrics are still collected

## Task Management with Beads

This project uses **Beads** (`bd`) for issue tracking. Issues are stored in `.beads/issues.jsonl`.

### Common Commands
```bash
bd list                    # List all issues
bd list --status=open      # List open issues
bd ready                   # Show ready-to-work issues (no blockers)
bd create "Title" --type=bug|feature|task|chore
bd show <issue-id>         # Show detailed info
bd update <issue-id> --status=in_progress
bd close <issue-id>        # Mark as completed
bd dep <issue-id> <depends-on-id>  # Add dependency
```

### Workflow
1. **Create issues** for any non-trivial work (bugs, features, tasks, chores)
2. **Set priorities**: 0 (highest), 1 (high), 2 (normal), 3 (low)
3. **Add dependencies** when work depends on other issues
4. **Check ready issues**: `bd ready` shows work with no blockers
5. **Update status**: open → in_progress → closed
6. **Close with reason**: Document why the issue was closed

### Beads Conventions for This Project
- **Bug**: Something broken that needs fixing
- **Feature**: New functionality
- **Task**: Development work (refactoring, updates, etc.)
- **Chore**: Maintenance, cleanup, documentation

### Priority Levels
- **0**: Critical (blocks other work, security issues)
- **1**: High (important for current milestone)
- **2**: Normal (regular development work) - default
- **3**: Low (nice-to-have, future enhancements)

### Compaction
Issues closed for 30+ days can be compacted to save space:
```bash
bd compact --stats         # Check compaction candidates
bd compact --analyze --json  # Export for review
```

For more details: `/beads:quickstart` or check `.claude/commands/beads*.md`
