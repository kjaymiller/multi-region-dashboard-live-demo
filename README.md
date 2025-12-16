# Multi-Region PostgreSQL Testing Dashboard

An interactive FastAPI dashboard for managing and testing PostgreSQL database connections. Features dual database backend architecture (file-based and PostgreSQL), HTMX for dynamic frontend updates, and comprehensive CRUD operations.

## Features

- **Database Connection Management**: Create, read, update, delete PostgreSQL connections
- **Dual Backend Architecture**: File-based storage and PostgreSQL backend with encrypted credentials
- **Real-time Frontend Updates**: HTMX-powered interface for seamless CRUD operations
- **Connection Testing**: Validate database connectivity with latency measurement
- **Geographic Visualization**: Interactive map showing connection locations
- **AI Chat Assistant**: Performance insights powered by Ollama
- **Secure Storage**: Encrypted password storage with bcrypt hashing (PostgreSQL) or Fernet encryption (file-based)
- **Auto-refresh Interface**: HTMX triggers for immediate UI updates after changes

## Tech Stack

- **FastAPI**: Modern Python web framework with async support
- **Database Backends**: 
  - File-based storage with Fernet encryption
  - PostgreSQL backend with bcrypt password hashing
- **HTMX**: Dynamic HTML updates without JavaScript frameworks
- **Jinja2**: Template engine for server-side rendering
- **Alpine.js**: Client-side interactivity and state management
- **Bootstrap**: Responsive CSS framework
- **Cryptography**: Password encryption and hashing
- **asyncpg**: Fast PostgreSQL async driver
- **Alembic**: Database migrations (PostgreSQL backend)
- **uv**: Fast Python package installer and resolver

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- [just](https://github.com/casey/just) command runner (optional but recommended)
- Aiven PostgreSQL databases (or any PostgreSQL instances)
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

### 3. Configure environment variables

Edit `.env` and add your database connection strings and LaunchDarkly SDK key:

```env
# Aiven PostgreSQL Connection Strings (use PgBouncer connection strings on port 6543)
AIVEN_PG_US_EAST=postgresql://user:password@host:6543/defaultdb?sslmode=require
AIVEN_PG_EU_WEST=postgresql://user:password@host:6543/defaultdb?sslmode=require
AIVEN_PG_ASIA_PACIFIC=postgresql://user:password@host:6543/defaultdb?sslmode=require

# LaunchDarkly SDK Key
LAUNCHDARKLY_SDK_KEY=sdk-your-key-here
```

### 4. Run the application

With `just`:
```bash
just dev
```

Or manually:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open your browser

Navigate to [http://localhost:8000](http://localhost:8000)

## Available Commands

If you have `just` installed, you can use these commands:

```bash
just                  # List all available commands
just dev              # Run development server with auto-reload
just serve            # Run production server
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
│   ├── db_manager.py       # File-based database manager
│   ├── db_manager_postgres.py # PostgreSQL backend manager
│   ├── routers/
│   │   ├── api.py           # General API endpoints
│   │   ├── db_management.py # File-based CRUD endpoints
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
├── .db_connections/         # File-based storage
├── alembic/               # Database migrations
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

### Database Backend Selection

The application supports two database backends:

1. **File-based** (`db_manager.py`):
   - Uses Fernet encryption for password storage
   - Stores connections in `.db_connections/connections.json`
   - No external database required
   - Suitable for development/testing

2. **PostgreSQL** (`db_manager_postgres.py`):
   - Uses bcrypt for password hashing
   - Requires PostgreSQL database and migrations
   - Supports concurrent users and scaling
   - Configured in `app/main.py` by router selection

### Frontend Refresh System

The application uses HTMX triggers for automatic UI updates:
- `connection-created` → Refreshes connections list on successful creation
- `connection-test-failed` → Should also refresh list (fix needed)
- `connection-error` → Shows error messages

### Known Issues

1. **Frontend Refresh on Test Failures**: Connections save successfully but list doesn't refresh when connection test fails
2. **JavaScript Quote Issues**: HTMX-Trigger-After-Swap headers need proper escaping
3. **Database Column Mismatches**: PostgreSQL backend uses `database_name` column

## Troubleshooting

### Connection Management Issues

**New connections not appearing:**
1. Check browser console for HTMX errors
2. Verify file permissions on `.db_connections/` directory
3. Check if connection test is failing but saving successfully
4. Look for JavaScript syntax errors in HTMX triggers

**Delete operations not working:**
1. Verify correct backend is configured in `app/main.py`
2. Check database connectivity (PostgreSQL backend)
3. Look for column name mismatches in SQL queries

**Backend switching:**
- File-based: Edit `app/main.py` line 33 to use `db_management.router`
- PostgreSQL: Edit `app/main.py` line 33 to use `db_management_postgres.router`

### Development Issues

If dependencies are missing:
```bash
just add cryptography bcrypt asyncpg
```

If migrations fail:
```bash
# Check DATABASE_URL in .env
uv run alembic current
```

### Connection Testing

If connections save but don't test:
1. Verify target database is running
2. Check network connectivity to host:port
3. Validate SSL/TLS settings
4. Test with external client like `psql`

## License

[Add your license here]

## Recent Updates & Fixes

### Bug Fixes Applied

1. **Delete Functionality** (Dec 2025):
   - Fixed SQL column name mismatches in PostgreSQL backend
   - Corrected `database` vs `database_name` column references
   - Delete endpoints now work correctly for both backends

2. **Frontend Refresh Issues** (Dec 2025):
   - Identified: HTMX triggers only fire on successful connection creation
   - Connection test failures don't refresh list despite successful saves
   - Partial fix implemented in `db_management.py`
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
