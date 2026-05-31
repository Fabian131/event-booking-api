# Event Booking API

Backend API for the Event Booking System built with FastAPI and PostgreSQL.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Containerization**: Docker & Docker Compose

## Project Structure

```
event-booking-api/
├── app/
│   ├── api/              # API routes and endpoints
│   │   ├── deps.py       # Dependencies (auth, db session)
│   │   └── v1/           # API version 1 routes
│   ├── core/             # Core configuration and utilities
│   │   ├── config.py     # Settings and environment variables
│   │   ├── database.py   # Database connection and session
│   │   └── security.py   # JWT and password utilities
│   ├── domain/           # Domain models (SQLAlchemy)
│   │   └── models.py     # Database models
│   ├── schemas/          # Pydantic schemas (request/response)
│   └── main.py           # FastAPI application entry point
├── Contracts/            # OpenAPI specifications (YAML)
├── migrations/           # Alembic database migrations
├── tests/                # Test suite
├── docs/                 # Documentation
│   ├── architecture/     # Architecture decisions
│   ├── research/         # Research documents
│   └── screenshots/      # Project screenshots
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # API container definition
└── requirements.txt      # Python dependencies
```

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

## Quick Start

### 1. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (change secrets in production).

### 2. Run with Docker Compose

```bash
docker-compose up -d
```

This will start:
- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Run Migrations

```bash
docker-compose exec api alembic upgrade head
```

## Local Development

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
uvicorn app.main:app --reload
```

### 4. Run tests

```bash
pytest
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Contracts**: `Contracts/` (separate YAML files per endpoint)

### Available Contracts

**Authentication:**
- `register-user.yaml` - Register new user
- `login-user.yaml` - Login and get JWT token

**Users:**
- `get-current-user.yaml` - Get authenticated user profile

**Events:**
- `list-events.yaml` - List all events (paginated)
- `create-event.yaml` - Create new event
- `get-event-by-id.yaml` - Get event details
- `update-event.yaml` - Update event
- `delete-event.yaml` - Delete event

**Event Schedules:**
- `list-event-schedules.yaml` - List schedules for an event
- `create-event-schedule.yaml` - Create schedule
- `get-schedule-by-id.yaml` - Get schedule details
- `update-schedule.yaml` - Update schedule
- `delete-schedule.yaml` - Delete schedule
- `check-schedule-availability.yaml` - Check availability

**Reservations:**
- `list-reservations.yaml` - List user reservations
- `create-reservation.yaml` - Create reservation
- `get-reservation-by-id.yaml` - Get reservation details
- `confirm-reservation.yaml` - Confirm reservation
- `cancel-reservation.yaml` - Cancel reservation

**Notifications:**
- `list-notifications.yaml` - List user notifications
- `mark-notification-as-read.yaml` - Mark as read

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback last migration:

```bash
alembic downgrade -1
```

## Testing

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app --cov-report=html
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `POSTGRES_USER` | Database username | event_booking_user |
| `POSTGRES_PASSWORD` | Database password | Required |
| `POSTGRES_DB` | Database name | event_booking_db |
| `POSTGRES_HOST` | Database host | localhost |
| `POSTGRES_PORT` | Database port | 5432 |
| `SECRET_KEY` | JWT secret key (min 32 chars) | Required |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | 30 |
| `APP_NAME` | Application name | Event Booking API |
| `APP_VERSION` | Application version | 1.0.0 |
| `DEBUG` | Enable debug mode | false |
| `ENVIRONMENT` | Environment name | production |
| `CORS_ORIGINS` | Allowed CORS origins | ["http://localhost:3000"] |

## Architecture

- **Layered Architecture**: Clear separation between API, domain, and infrastructure
- **SOLID Principles**: Applied throughout the codebase
- **DRY**: Reusable components and utilities
- **Clean Code**: Readable, maintainable, and testable code

## Security

- Passwords hashed with bcrypt
- JWT-based authentication
- Environment variables for secrets (never committed)
- CORS configured for allowed origins
- Input validation with Pydantic

## License

This project is part of an academic course.
