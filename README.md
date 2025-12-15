# Multi-Region PostgreSQL Testing Dashboard

An interactive FastAPI dashboard for testing PostgreSQL connectivity and performance across multiple Aiven regions. Built with HTMX for dynamic content updates and LaunchDarkly for feature flag management.

## Features

- **Multi-Region Connectivity Testing**: Test connections to PostgreSQL databases across US East, EU West, and Asia Pacific regions
- **Health Checks**: Verify database availability and connection status
- **Latency Measurement**: Measure query response times for each region
- **Load Testing**: Run concurrent connection tests to evaluate performance under load
- **Feature Flags**: Toggle features dynamically using LaunchDarkly
- **Real-time Updates**: HTMX-powered interface for seamless user experience

## Tech Stack

- **FastAPI**: Modern Python web framework
- **asyncpg**: Fast PostgreSQL async driver
- **HTMX**: Dynamic HTML updates without JavaScript frameworks
- **Jinja2**: Template engine for server-side rendering
- **LaunchDarkly**: Feature flag management
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
│   ├── main.py              # FastAPI application
│   ├── config.py            # Region configurations
│   ├── database.py          # Database connection logic

│   ├── queries.py           # Database queries
│   ├── routers/
│   │   ├── api.py           # API endpoints
│   │   └── pages.py         # HTML page routes
│   ├── static/              # Static files
│   └── templates/           # Jinja2 templates
│       ├── base.html
│       ├── index.html
│       └── partials/        # HTMX partial templates
├── .env                     # Environment variables (not in git)
├── .env.example             # Example environment variables
├── pyproject.toml           # Project configuration and dependencies
├── justfile                 # Command runner recipes
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

## Troubleshooting

### Connection Issues

If you can't connect to a database:
1. Verify connection string in `.env`
2. Check firewall rules allow connections
3. Verify SSL/TLS settings
4. Test connection with `psql` or another client

### LaunchDarkly Issues

If feature flags aren't working:
1. Verify `LAUNCHDARKLY_SDK_KEY` is set correctly
2. Check LaunchDarkly dashboard for flag configuration
3. Review logs for initialization errors

### Port Already in Use

If port 8000 is already in use:
```bash
just run 0.0.0.0 8080  # Run on port 8080 instead
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
