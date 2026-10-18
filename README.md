# CloudCapsule

**A containerized cloud module lifecycle management platform.**

CloudCapsule provides an API for registering application modules, managing their lifecycle states, and recording lifecycle events. The project is being developed locally first, with AWS infrastructure planned as a subsequent phase.

> **Current status:** The FastAPI backend and PostgreSQL database run locally using Docker Compose. Lifecycle operations are simulations; they do not deploy or modify AWS resources.

## Features

- **Module management:** Create, list, retrieve, and update registered modules.
- **Lifecycle simulation:** Deploy, stop, and restart modules using validated state transitions.
- **Audit history:** Record successful and rejected lifecycle actions.
- **Database reliability:** Use PostgreSQL transactions and row-level locking for lifecycle operations.
- **Configuration validation:** Reject malformed database URLs before attempting a connection.
- **Database migrations:** Manage schema changes with Alembic.
- **API documentation:** Explore endpoints through FastAPI's interactive Swagger UI.
- **Automated tests:** Test API behavior, lifecycle transitions, concurrency, rollback, and database configuration.

## Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database | PostgreSQL |
| Database migrations | Alembic |
| Database access | Psycopg, SQLAlchemy metadata |
| Containerization | Docker, Docker Compose |
| Testing | Pytest, FastAPI TestClient |
| Cloud infrastructure | AWS and Terraform — planned |

## Prerequisites

- Docker Desktop with Docker Compose
- Git
- PowerShell on Windows, or an equivalent terminal

## Getting Started

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd CloudCapsule
```

Replace `<YOUR_REPOSITORY_URL>` with your Git repository URL.

### 2. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a reference.

Set `DATABASE_URL` to the PostgreSQL connection URL appropriate for your Docker Compose environment. For the local Compose database, the hostname is `db`, the port is `5432`, and the database name is `cloudcapsule`.

Use the credentials configured for your local database service. Do not commit `.env` or production credentials.

### 3. Start the services

```bash
docker compose up -d --build
```

Check the service status:

```bash
docker compose ps
```

### 4. Open the API documentation

- Swagger UI: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
- Database health: http://localhost:8000/health/database

The backend is bound to `127.0.0.1:8000` by default in the provided Compose configuration.

### 5. Run the test suite

```bash
docker compose exec backend python -m pytest -q
```

### 6. Check database migration consistency

```bash
docker compose exec backend alembic current
docker compose exec backend alembic check
```

### 7. View application logs

```bash
docker compose logs --tail 100 backend
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API root |
| GET | `/health` | Application health |
| GET | `/health/database` | Database health |
| POST | `/modules` | Register a module |
| GET | `/modules` | List modules |
| GET | `/modules/{module_id}` | Retrieve a module |
| PATCH | `/modules/{module_id}` | Update module details |
| POST | `/modules/{module_id}/actions` | Execute a simulated lifecycle action |
| GET | `/modules/{module_id}/events` | Retrieve lifecycle event history |

Use Swagger UI to inspect request schemas, try endpoints, and view responses.

## Lifecycle Model

The API validates actions against the module's current state. Supported actions include `deploy`, `stop`, and `restart`.

Deploy operations simulate transitions through deployment to a running state. Stop and restart operations are also simulated locally. Invalid transitions are rejected and recorded in the event history.

These operations do not provision cloud infrastructure or execute real AWS deployments.

## Architecture and Development Status

**Implemented locally**
- FastAPI backend
- PostgreSQL persistence
- Alembic migration management
- Module lifecycle simulation and event history
- Docker Compose development environment
- Automated API and configuration tests

**Planned**
- AWS architecture and infrastructure provisioning
- Infrastructure as Code workflows using Terraform
- Cloud deployment, monitoring, security controls, and recovery workflows

AWS resources will only be deployed after the architecture, permissions, and expected costs have been reviewed and approved.

## Security Notes

- Keep `.env`, credentials, tokens, and private keys out of Git.
- Never commit production secrets or Terraform state files.
- Use dedicated, least-privilege credentials for any future cloud deployment.
- Review network exposure and access controls before deploying beyond localhost.

## License

No license has been selected yet. All rights reserved unless a license is added to this repository.
