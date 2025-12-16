# Multi-Region PostgreSQL Testing Dashboard

An interactive FastAPI dashboard for managing and testing PostgreSQL database connections. Features HTMX for dynamic frontend updates, comprehensive CRUD operations, and TimescaleDB integration for connection test history.

## Features

- **Database Connection Management**: Create, read, update, delete PostgreSQL connections
- **PostgreSQL Backend**: Secure storage with bcrypt password hashing and TimescaleDB for time-series data
- **Real-time Frontend Updates**: HTMX-powered interface for seamless CRUD operations
- **Connection Testing**: Validate database connectivity with latency measurement
- **Geographic Visualization**: Interactive map showing connection locations
- **AI Chat Assistant**: Performance insights powered by Ollama
- **Secure Storage**: bcrypt password hashing for maximum security
- **Auto-refresh Interface**: HTMX triggers for immediate UI updates after changes

## Tech Stack

- **FastAPI**: Modern Python web framework with async support
- **PostgreSQL**: Backend database with bcrypt password hashing and TimescaleDB for time-series data
- **HTMX**: Dynamic HTML updates without JavaScript frameworks
- **Jinja2**: Template engine for server-side rendering
- **Alpine.js**: Client-side interactivity and state management
- **Bootstrap**: Responsive CSS framework
- **Cryptography**: Password encryption and hashing
- **asyncpg**: Fast PostgreSQL async driver
- **TimescaleDB**: Time-series database extension for connection test history
- **uv**: Fast Python package installer and resolver

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- [just](https://github.com/casey/just) command runner (optional but recommended)
- **Backend PostgreSQL database** (for application storage):
  - **TimescaleDB extension** (for connection test history)
  - **pg_stat_statements extension** (for query performance monitoring)
  - Docker Compose setup provided, or use managed PostgreSQL with extensions
- **Target PostgreSQL databases** (to monitor):
  - **pg_stat_statements extension** (recommended for comprehensive health checks)
  - Without this extension, health checks will work but provide limited query statistics
  - Aiven PostgreSQL or any PostgreSQL instances to test
- LaunchDarkly account (for feature flags)

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd multi-region-dashboard-live-demo
```

### 2. Install dependencies

With `just`:
```bash
just setup
```

Or manually:
```bash
uv sync --extra dev
cp .env.example .env
```

### 3. Start the backend PostgreSQL database (with Docker Compose)

For local development, use the included Docker Compose setup with TimescaleDB:

```bash
docker compose --profile postgres up -d
```

This starts a PostgreSQL 15 database with TimescaleDB and pg_stat_statements extensions pre-installed for storing application data.

Alternatively, provide your own PostgreSQL database with the required extensions enabled.

**Note**: This is the backend database where the app stores connection metadata, not the databases you'll be monitoring.

### 4. Set up the database schema

```bash
just db-setup
```

This creates all required tables, including the TimescaleDB hypertable for connection test history.

### 5. Configure environment variables

Edit `.env` and add your database connection strings and LaunchDarkly SDK key:

```env
# Backend Database (for storing connection metadata and test history)
# Must have TimescaleDB and pg_stat_statements extensions enabled
DATABASE_URL=postgresql://dashboard_user:dashboard_password@localhost:5432/dashboard

# Aiven PostgreSQL Connection Strings (use PgBouncer connection strings on port 6543)
AIVEN_PG_US_EAST=postgresql://user:password@host:6543/defaultdb?sslmode=require
AIVEN_PG_EU_WEST=postgresql://user:password@host:6543/defaultdb?sslmode=require
AIVEN_PG_ASIA_PACIFIC=postgresql://user:password@host:6543/defaultdb?sslmode=require

# LaunchDarkly SDK Key
LAUNCHDARKLY_SDK_KEY=sdk-your-key-here
```

### 6. Run the application

With `just`:
```bash
just dev
```

Or manually:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Open your browser

Navigate to [http://localhost:8000](http://localhost:8000)

## Available Commands

If you have `just` installed, you can use these commands:

```bash
just                  # List all available commands
just dev              # Run development server with auto-reload
just serve            # Run production server
just db-setup         # Create database tables and populate initial data
just install          # Install dependencies
just install-dev      # Install with dev dependencies
just add <package>    # Add a new dependency
just add-dev <package> # Add a dev dependency
just format           # Format code with black
just lint             # Lint code with ruff
just typecheck        # Type check with mypy
just check            # Run all checks (lint + typecheck)
just clean            # Remove Python cache files
just info             # Show application and dependency info
just setup-env        # Copy .env.example to .env
just check-env        # Verify .env file exists
just setup            # Full project setup
```

## Project Structure

```
multi-region-dashboard-live-demo/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and lifespan
│   ├── config.py            # Database configuration
│   ├── database.py          # Database connection utilities
│   ├── queries.py           # PostgreSQL query definitions
│   ├── chat.py            # AI chat assistant logic
│   ├── region_mapping.py    # Geographic coordinate mapping
│   ├── db_manager_postgres.py # PostgreSQL backend manager
│   ├── routers/
│   │   ├── api.py           # General API endpoints
│   │   ├── db_management_postgres.py # PostgreSQL CRUD endpoints
│   │   └── pages.py         # HTML page routes
│   ├── static/              # Static assets (CSS, JS)
│   └── templates/           # Jinja2 templates
│       ├── base.html         # Base template with HTMX setup
│       ├── index.html         # Main dashboard page
│       └── partials/        # Reusable UI components
│           ├── database_connections.html
│           ├── connection_form.html
│           ├── connection_result.html
│           ├── connection_details.html
│           ├── map_view.html
│           └── ...
├── .beads/                  # Beads task management
├── migrations/              # SQL migration scripts (run via docker-entrypoint-initdb.d)
├── setup_database.py        # Database schema setup (no Alembic/migrations)
├── .env                    # Environment variables (not in git)
├── .env.example            # Example environment variables
├── justfile                # Command runner recipes
├── pyproject.toml          # Project configuration and dependencies
└── README.md
```

## Configured Regions

The dashboard is pre-configured with three regions:

1. **US East (Virginia)** - Primary testing region
2. **EU West (Ireland)** - European testing region
3. **Asia Pacific (Singapore)** - APAC testing region

To add or modify regions, edit `app/config.py` and update the `REGIONS` dictionary.

## API Endpoints

### Health Checks
- `GET /api/health/{region_id}` - Check health of a specific region
- `GET /api/health/all` - Check health of all regions

### Connectivity Tests
- `POST /api/test/connection/{region_id}` - Test connection to a region
- `POST /api/test/all-regions` - Test all regions

### Performance Tests
- `POST /api/test/latency/{region_id}` - Measure query latency
- `POST /api/test/load/{region_id}` - Run load test with concurrent connections

## Development

### Code Quality

Format code:
```bash
just format
```

Lint code:
```bash
just lint
```

Type check:
```bash
just typecheck
```

Run all checks:
```bash
just check
```

### Adding Dependencies

Production dependency:
```bash
just add <package-name>
```

Development dependency:
```bash
just add-dev <package-name>
```

## Deployment

For production deployment:

1. Set environment variables on your hosting platform
2. Install production dependencies: `uv sync`
3. Run with: `just serve` or `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`

Consider using a process manager like systemd, supervisor, or containerizing with Docker.

## Security Notes

- Never commit `.env` file to version control
- Use secure connection strings (SSL/TLS enabled)
- Use PgBouncer connection pooling (port 6543) for better performance
- Rotate credentials regularly
- Limit database user permissions to minimum required

## Architecture Notes

### PostgreSQL Backend

The application uses PostgreSQL for storing connection metadata and test history:

- Uses bcrypt for password hashing
- Requires PostgreSQL database with TimescaleDB and pg_stat_statements extensions
- Schema managed via `setup_database.py` (no Alembic/migrations)
- Supports concurrent users and scaling
- Stores connection test history in TimescaleDB hypertable

### Frontend Refresh System

The application uses HTMX triggers for automatic UI updates:
- `connection-created` → Refreshes connections list on successful creation
- `connection-test-failed` → Should also refresh list (fix needed)
- `connection-error` → Shows error messages

### Known Issues

1. **Frontend Refresh on Test Failures**: Connections save successfully but list doesn't refresh when connection test fails
2. **JavaScript Quote Issues**: HTMX-Trigger-After-Swap headers need proper escaping
3. **Database Column Mismatches**: Database uses `database_name` column

## Troubleshooting

### Connection Management Issues

**New connections not appearing:**
1. Check browser console for HTMX errors
2. Check if connection test is failing but saving successfully
3. Look for JavaScript syntax errors in HTMX triggers
4. Verify database connectivity

**Delete operations not working:**
1. Check database connectivity
2. Look for column name mismatches in SQL queries
3. Check browser console for errors

### Development Issues

If dependencies are missing:
```bash
just add cryptography bcrypt asyncpg
```

If database setup fails:
```bash
# Check DATABASE_URL in .env
# Verify TimescaleDB and pg_stat_statements extensions are available
just db-setup
```

### Connection Testing

If connections save but don't test:
1. Verify target database is running
2. Check network connectivity to host:port
3. Validate SSL/TLS settings
4. Test with external client like `psql`

### Health Checks Missing Query Statistics

If health checks succeed but don't show query performance data:
1. Check if target database has `pg_stat_statements` extension installed
2. Enable the extension on target databases:
   ```sql
   -- Add to postgresql.conf
   shared_preload_libraries = 'pg_stat_statements'

   -- After database restart
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
   ```
3. Health checks will still work without this extension, but query statistics will be unavailable

## License

[Add your license here]

## Recent Updates & Fixes

### Bug Fixes Applied

1. **Delete Functionality** (Dec 2025):
   - Fixed SQL column name mismatches
   - Corrected `database` vs `database_name` column references
   - Delete endpoints now work correctly

2. **Frontend Refresh Issues** (Dec 2025):
   - Identified: HTMX triggers only fire on successful connection creation
   - Connection test failures don't refresh list despite successful saves
   - JavaScript quote escaping issue identified

### Development Workflow

The project uses **Beads** for issue tracking:
```bash
bd create "Issue title" --type=bug|feature|task
bd list --status=open
bd ready                    # Show workable issues
bd close <issue-id>
```

### Code Quality Standards

- **Formatting**: Black with 100 character line length
- **Type Hints**: Modern union syntax (`str | None`)
- **Error Handling**: FastAPI HTTP exceptions with proper status codes
- **Async**: All database operations use async/await
- **Security**: Encrypted credentials, never commit secrets

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow code style guidelines (see AGENTS.md)
4. Test thoroughly: `just check`
5. Submit Pull Request with clear description

### Development Commands

```bash
just dev              # Start development server
just format           # Format code
just check            # Run all checks
just add <package>    # Add dependencies
```
