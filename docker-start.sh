#!/bin/bash

# PostgreSQL Dashboard Docker Helper Script
# Automatically detects whether to use local PostgreSQL or remote database

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}PostgreSQL Dashboard Docker Setup${NC}"
echo "=================================="

# Check if DATABASE_URL environment variable is set
if [ -n "$DATABASE_URL" ]; then
    echo -e "${GREEN}✓ Remote DATABASE_URL detected${NC}"
    echo -e "${YELLOW}Using remote database:${NC} $DATABASE_URL"
    echo ""
    echo -e "${BLUE}Starting application only (no local PostgreSQL)...${NC}"
    docker-compose --profile app up -d
else
    echo -e "${YELLOW}No DATABASE_URL environment variable found${NC}"
    echo -e "${BLUE}Using local PostgreSQL database...${NC}"
    echo ""
    echo -e "${BLUE}Starting application with local PostgreSQL...${NC}"
    docker-compose --profile app --profile postgres up -d
fi

echo ""
echo -e "${GREEN}✓ Services started successfully!${NC}"
echo ""

# Show service status
echo -e "${BLUE}Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${BLUE}Application URL:${NC} http://localhost:8000"

if [ -z "$DATABASE_URL" ]; then
    echo ""
    echo -e "${BLUE}Local Database Connection:${NC}"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: dashboard"
    echo "  User: dashboard_user"
    echo "  Password: dashboard_password"
    echo ""
    echo -e "${BLUE}To connect with psql:${NC}"
    echo "  docker exec -it postgres_db psql -U dashboard_user -d dashboard"
else
    echo ""
    echo -e "${YELLOW}Using remote database${NC}"
    echo "  Set DATABASE_URL environment variable to switch to local development"
fi

echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:       docker-compose logs -f"
echo "  Stop services:   docker-compose down"
echo "  Restart:         docker-compose restart"
echo "  Access app shell: docker exec -it dashboard_app bash"