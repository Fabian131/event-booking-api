# Docker Commands - Event Booking API

Essential commands for managing the Event Booking API containers.

## Quick Start

```bash
# Start all services (API + Database)
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (deletes all database data)
docker-compose down -v
```

## Build

```bash
# Build API image
docker-compose build

# Build without cache (force rebuild)
docker-compose build --no-cache

# Build specific service
docker-compose build api
```

## Database Migrations

```bash
# Apply all pending migrations
docker-compose exec api alembic upgrade head

# Create new migration (after model changes)
docker-compose exec api alembic revision --autogenerate -m "description"

# Rollback last migration
docker-compose exec api alembic downgrade -1

# View migration history
docker-compose exec api alembic history
```

## Database Operations

```bash
# Reset database completely (deletes all data)
docker-compose down -v
docker-compose up -d db
docker-compose exec api alembic upgrade head

# Access database shell
docker-compose exec db psql -U event_booking_user -d event_booking_db

# Remove database volume only
docker volume rm event-booking-api_postgres_data
```

## Logs

```bash
# View all logs
docker-compose logs

# View API logs only
docker-compose logs api

# Follow logs in real-time
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100 api
```

## Container Management

```bash
# List running containers
docker-compose ps

# Restart services
docker-compose restart api

# Stop specific service
docker-compose stop api
docker-compose stop db

# Remove stopped containers
docker-compose rm -f
```

## Testing

```bash
# Run all tests
docker-compose exec api pytest

# Run tests with coverage
docker-compose exec api pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec api pytest tests/test_auth.py
```

## Common Workflows

### Fresh setup (clean start)
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Update code and rebuild
```bash
docker-compose down
docker-compose build
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Reset database only
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec api alembic upgrade head
```

## Access Points

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Troubleshooting

```bash
# Check container health
docker-compose ps

# View container logs
docker-compose logs api

# Restart Docker Desktop if containers won't start

# Kill process using port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```
