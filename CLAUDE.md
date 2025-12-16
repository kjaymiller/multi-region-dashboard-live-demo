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

## Architecture Overview

### Dual Backend System

The application supports two database storage backends for connection management:

1. **File-based backend** (`app/db_manager.py` + `app/routers/db_management.py`):
   - Stores connections in `.db_connections/connections.json`
   - Uses Fernet encryption for passwords
   - No external database required
   - Suitable for development/testing

2. **PostgreSQL backend** (`app/db_manager_postgres.py` + `app/routers/db_management_postgres.py`):
   - Stores connections in PostgreSQL database
   - Uses bcrypt for password hashing
   - Requires DATABASE_URL environment variable
   - Supports concurrent users and scaling
   - Managed via Alembic migrations

**Switching backends**: Edit `app/main.py` line 33 to include the desired router:
- File-based: `app.include_router(db_management.router, prefix="/api/db")`
- PostgreSQL: `app.include_router(db_management_postgres.router, prefix="/api/db")`

### Key Architectural Patterns

**HTMX-driven Frontend**:
- Server-side rendered HTML partials in `app/templates/partials/`
- HTMX triggers for UI updates: `connection-created`, `connection-test-failed`, `connection-error`
- All API endpoints return HTML templates, not JSON (except where noted)
- Auto-refresh achieved via HX-Trigger headers

**Database Connection Testing**:
- The app manages and tests connections to *external* PostgreSQL databases
- Backend database (for storing connection metadata) is separate from tested connections
- Both backends implement `test_connection()` which validates external DB connectivity

**Security Model**:
- File backend: Fernet symmetric encryption with PBKDF2 key derivation
- PostgreSQL backend: bcrypt password hashing (rounds=12)
- SSL handling: Automatic detection - require SSL for remote hosts, disable for localhost
- Never expose plaintext passwords in API responses

**Async Design**:
- All database operations use async/await
- Connection pool management via asyncpg
- FastAPI lifespan context manager in `app/main.py`

## Critical Implementation Details

### Database Column Names
The PostgreSQL backend uses `database_name` column, not `database`. When writing queries for the PostgreSQL backend, always use:
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
- **File backend**: Store encrypted password in `password` field
- **PostgreSQL backend**: Store `password_hash` and `salt`, never store plaintext
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
├── db_manager.py                # File-based connection manager
├── db_manager_postgres.py       # PostgreSQL-based connection manager
├── location_service.py          # Geographic distance calculations
├── routers/
│   ├── api.py                   # Health checks, connection tests
│   ├── db_management.py         # File backend CRUD endpoints
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
DATABASE_URL=postgresql://user:password@host:port/dbname  # For PostgreSQL backend only
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

2. **Column name mismatches**: PostgreSQL backend uses `database_name` in SQL but `database` in Python dataclass. Always map correctly when reading from DB.

3. **JavaScript quote escaping**: HTMX triggers with JavaScript in header values need proper escaping.

4. **SSL certificate verification**: Currently disabled (`ssl_context.verify_mode = ssl.CERT_NONE`) for testing - should be enabled in production.

## Testing Connections

The `test_connection()` methods establish a real connection to external PostgreSQL databases and run:
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
