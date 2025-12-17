# PostgreSQL Connection Dashboard

An interactive FastAPI dashboard for managing and testing PostgreSQL database connections. Features real-time monitoring, performance analytics with Chart.js visualizations, geographic mapping, and an AI-powered chat assistant for database insights.

## Features

### Core Functionality
- **Database Connection Management**: Full CRUD operations for PostgreSQL connections with secure credential storage
- **Real-time Testing & Monitoring**: Connection validation, latency measurement, and load testing
- **Health Checks**: Comprehensive metrics including cache hit ratio, active connections, database size, and query performance
- **Time-Series Analytics**: Historical performance data stored in TimescaleDB hypertables with 90-day retention

### Visualization & UI
- **Interactive Charts**: Chart.js-powered visualizations for latency trends, health metrics, and query performance
- **Geographic Map**: Leaflet.js map showing database locations with visual connections to user location
- **HTMX-Powered UI**: Dynamic updates without page reloads for seamless user experience
- **Responsive Design**: Bootstrap-based interface that works on desktop and mobile

### Performance & Security
- **AI Chat Assistant**: Ollama-powered natural language interface for performance insights and query analysis
- **Query Analytics**: Expensive query tracking via pg_stat_statements with execution time statistics
- **Encrypted Credentials**: bcrypt password hashing (12 rounds) with additional encryption layer
- **SSL Auto-Detection**: Automatic SSL enforcement for remote databases, disabled for localhost

### Developer Experience
- **Fast Setup**: One-command initialization with just and uv package manager
- **Docker Integration**: Local PostgreSQL with TimescaleDB via Docker Compose
- **Code Quality**: Black formatting, Ruff linting, mypy type checking
- **Task Management**: Beads issue tracker for project management

## Tech Stack

### Backend
- **FastAPI 0.104+**: Modern async Python web framework with automatic OpenAPI documentation
- **PostgreSQL 15+**: Relational database for application storage
- **TimescaleDB**: Time-series extension for connection test history hypertables
- **asyncpg 0.29+**: High-performance async PostgreSQL driver
- **bcrypt 5.0+**: Password hashing with 12 rounds for security
- **cryptography 46+**: Additional encryption layer for stored credentials

### Frontend
- **HTMX**: Server-driven HTML updates without heavy JavaScript frameworks
- **Alpine.js**: Lightweight reactive framework for client-side state management
- **Bootstrap**: Responsive CSS framework for mobile-friendly design
- **Chart.js 4.4+**: Modern charting library for performance visualizations
- **Leaflet.js**: Interactive mapping for geographic database locations
- **Jinja2 3.1.2+**: Server-side template engine

### Development Tools
- **uv**: Lightning-fast Python package installer and resolver
- **just**: Command runner for task automation
- **Black**: Code formatter with 100-character line length
- **Ruff**: Fast Python linter and import sorter
- **mypy**: Static type checker for Python
- **Beads (bd)**: Issue tracking and task management

### AI & Analytics
- **Ollama**: Local AI model integration for chat assistant
- **httpx 0.27+**: Async HTTP client for AI service communication
- **pg_stat_statements**: PostgreSQL extension for query performance monitoring

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
  - Any PostgreSQL instances you want to monitor and test

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>
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

Edit `.env` with your configuration:

```env
# Backend Database (for storing connection metadata and test history)
# Must have TimescaleDB and pg_stat_statements extensions enabled
DATABASE_URL=postgresql://dashboard_user:dashboard_password@localhost:5432/dashboard

# Password Encryption Key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
DB_PASSWORD_ENCRYPTION_KEY=your-generated-encryption-key-here

# AI Chat Configuration (optional)
OLLAMA_BASE_URL=http://localhost:11434  # Default Ollama endpoint
OLLAMA_MODEL=gpt-oss                    # AI model to use
CHAT_ENABLED=true                       # Enable/disable chat feature

# TimescaleDB Configuration
TIMESCALE_RETENTION_DAYS=90            # Days to keep test history
TIMESCALE_CHUNK_TIME_INTERVAL=7 days   # Chunk interval for hypertables

# Example Target Database Connections (add via UI)
# You can add database connections through the web interface after starting the application
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
postgres-dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application and lifespan
│   ├── config.py                    # Database configuration
│   ├── database.py                  # Database connection utilities
│   ├── queries.py                   # PostgreSQL query definitions
│   ├── chat.py                      # AI chat assistant logic
│   ├── location_service.py          # Geographic distance calculations
│   ├── region_mapping.py            # Geographic coordinate mapping
│   ├── db_manager_postgres.py       # PostgreSQL backend manager
│   ├── routers/
│   │   ├── api.py                   # Health checks, testing, analytics endpoints
│   │   ├── db_management_postgres.py # PostgreSQL CRUD endpoints
│   │   └── pages.py                 # HTML page routes
│   ├── static/                      # Static assets (CSS, JS)
│   └── templates/                   # Jinja2 templates
│       ├── base.html                # Base template with HTMX, Chart.js, Leaflet
│       ├── index.html               # Main dashboard page
│       └── partials/                # HTMX-swappable UI components
│           ├── database_connections.html
│           ├── connection_form.html
│           ├── health_result.html   # Health check with Chart.js visualizations
│           ├── metrics_charts.html  # Performance charts
│           ├── map_view.html        # Geographic visualization
│           └── ...
├── .beads/                          # Beads task management
├── migrations/                      # SQL initialization scripts
├── setup_database.py                # Database schema setup (no Alembic)
├── .env                             # Environment variables (not in git)
├── .env.example                     # Example environment variables
├── docker-compose.yml               # Docker development environment
├── justfile                         # Command runner recipes
├── pyproject.toml                   # Project configuration and dependencies
├── CLAUDE.md                        # Development guidelines
├── DOCKER_SETUP.md                  # Docker deployment documentation
└── README.md
```

## Adding Database Connections

Database connections are managed through the web UI:

1. Navigate to the dashboard at `http://localhost:8000`
2. Use the connection form to add PostgreSQL databases
3. Configure: host, port, database name, username, password, SSL mode
4. Optionally set region (e.g., "US East", "EU West") and cloud provider
5. Test connection automatically upon creation

The dashboard supports any PostgreSQL database - local, cloud-hosted, or managed services.

## API Endpoints

### Health & Monitoring
- `GET /api/health/{connection_id}` - Get comprehensive health metrics for a database
- `GET /api/health/all` - Health check all configured databases
- `GET /api/database/info` - Get database configuration information
- `GET /api/database-summary` - Overall summary statistics across all databases

### Connection Testing
- `POST /api/test/connection/{connection_id}` - Test connectivity and measure latency
- `POST /api/test/all-regions` - Test all configured database connections
- `POST /api/test/latency/{connection_id}` - Run multiple iterations of latency tests (5 rounds)
- `POST /api/test/load/{connection_id}` - Execute load test with concurrent connections

### Analytics & Visualization
- `GET /api/latency-chart-data` - Time-series latency data for Chart.js visualization
- `GET /api/health-metrics-chart-data` - Historical health metrics for charts
- `GET /api/recent-checks` - Recent connection test history
- `GET /api/expensive-queries` - Query performance statistics from pg_stat_statements
- `GET /api/map-data` - Geographic data for interactive map

### AI & Chat
- `POST /api/chat` - Send natural language queries to AI assistant
- Chat context includes database performance metrics and query statistics

### Database Management (CRUD)
- `GET /api/db/connections` - List all database connections
- `POST /api/db/connections` - Create new database connection
- `PUT /api/db/connections/{connection_id}` - Update existing connection
- `DELETE /api/db/connections/{connection_id}` - Delete database connection

### Utility
- `GET /api/location` - Detect user's geographic location for distance calculations

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

## Development Workflow

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
