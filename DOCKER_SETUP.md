# PostgreSQL Dashboard Docker Setup

This Docker Compose setup provides a complete development environment with:

- **PostgreSQL Database**: Local PostgreSQL 15 instance
- **FastAPI Application**: Dashboard application with hot reload
- **Local Development**: Easy setup with `docker-compose up`

## Quick Start

### Smart Start (Recommended)
```bash
# Auto-detects local vs remote database based on DATABASE_URL env var
./docker-start.sh
```

### Manual Start

#### Local Database (Default)
```bash
# Start with local PostgreSQL
docker-compose --profile app --profile postgres up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

#### Remote Database Only
```bash
# Set environment variable and start app only
export DATABASE_URL="postgresql://user:password@remote-host:5432/dbname"
./docker-start.sh

# Or manually
docker-compose --profile app up -d
```

#### Using Docker Compose Profiles
The setup uses Docker Compose profiles for flexible deployment:

- `--profile app`: Always starts the application
- `--profile postgres`: Starts local PostgreSQL (only when no DATABASE_URL)

The `docker-start.sh` script automatically handles this logic.

## Services

### PostgreSQL (postgres)
- **Port**: 5432
- **Database**: dashboard
- **User**: dashboard_user
- **Password**: dashboard_password
- **Data**: Persisted in Docker volume `postgres_data`

### Application (app)
- **Port**: 8000
- **URL**: http://localhost:8000
- **Auto-reload**: Enabled for development

## Database Connection

### Local Development
```bash
# Connect to local database
docker exec -it postgres_db psql -U dashboard_user -d dashboard
```

### Remote Database Setup
1. **Set environment variable**:
   ```bash
   export DATABASE_URL="postgresql://user:password@remote-host:5432/dbname"
   ./docker-start.sh
   ```

2. **Ensure remote PostgreSQL**:
   - Allows connections from your IP
   - Has proper user permissions
   - Database exists
   
3. **Create database if needed**:
   ```sql
   CREATE DATABASE dashboard;
   CREATE USER dashboard_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE dashboard TO dashboard_user;
   ```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://dashboard_user:dashboard_password@postgres:5432/dashboard` | Database connection string |
| `HOST` | `0.0.0.0` | Application host |
| `PORT` | `8000` | Application port |
| `DEBUG` | `false` | Debug mode |
| `CORS_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Allowed CORS origins |

## Development Workflow

### Running migrations
```bash
# Run migrations on local database
docker exec postgres_db psql -U dashboard_user -d dashboard -f /docker-entrypoint-initdb.d/001_create_health_check_tables.sql
```

### Viewing logs
```bash
# Application logs
docker-compose logs app

# Database logs
docker-compose logs postgres
```

### Rebuilding
```bash
# Rebuild app after changes
docker-compose up --build
```

## Production Considerations

For production deployment:

1. **Security**: Change default passwords
2. **SSL**: Enable SSL for database connections
3. **Volumes**: Use named volumes with proper backup strategy
4. **Networking**: Use overlay networks for multi-host setups
5. **Monitoring**: Add health checks and monitoring

## Troubleshooting

### Database Connection Issues

#### Local Database
```bash
# Check database health
docker exec postgres_db pg_isready -U dashboard_user -d dashboard

# Check database logs
docker-compose logs postgres

# Connect manually
docker exec -it postgres_db psql -U dashboard_user -d dashboard
```

#### Remote Database
```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# Test connection from container
docker exec -it dashboard_app bash
psql $DATABASE_URL -c "SELECT 1;"
```

### Application Issues
```bash
# Check application logs
docker-compose logs app

# Access container shell
docker exec -it dashboard_app bash

# Check environment variables
docker exec dashboard_app env | grep DATABASE
```

### Service Management
```bash
# Check what's running
docker-compose ps

# Restart specific service
docker-compose restart app

# Stop and clean
docker-compose down -v  # -v removes data volume
```

### Port Conflicts
If ports are in use, modify `docker-compose.yml`:
```yaml
services:
  app:
    ports:
      - "8001:8000"   # Different external port for app
  postgres:
    ports:
      - "5433:5432"  # Different external port for PostgreSQL
```