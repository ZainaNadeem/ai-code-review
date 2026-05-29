# AI Code Review Assistant

Monorepo for an AI-powered code review assistant.

## Structure

```
.
├── client/   # React + TypeScript + Vite frontend
├── server/   # Python FastAPI backend (SQLAlchemy + Alembic)
└── docker-compose.yml
```

The stack includes a PostgreSQL database, accessed via SQLAlchemy with schema
migrations managed by Alembic.

## Getting started

Create the env files (they are gitignored):

```bash
cp client/.env.example client/.env
cp server/.env.example server/.env
```

Then run all services (Postgres, server, client):

```bash
docker compose up --build
```

- Client: http://localhost:5173
- Server: http://localhost:8000 (docs at `/docs`)
- Database: PostgreSQL on localhost:5432 (db `ai_code_review`)

Apply the database migrations once the stack is up:

```bash
docker compose exec server alembic upgrade head
```

## Running locally without Docker

### Server

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Point DATABASE_URL at a running Postgres instance (see .env.example),
# then apply migrations and start the server:
alembic upgrade head
uvicorn app.main:app --reload
```

### Database & migrations

The server uses SQLAlchemy models defined in [server/app/models/](server/app/models/):

- `User` — `id`, `email`, `hashed_password`, `created_at`
- `Repo` — `id`, `user_id` → `User`, `github_repo_url`, `name`
- `Review` — `id`, `repo_id` → `Repo`, `pr_number`, `status`, `created_at`, `summary`

Schema changes are managed with Alembic (config in [server/alembic.ini](server/alembic.ini)).
Run these commands from the `server/` directory:

```bash
# Apply all migrations
alembic upgrade head

# Autogenerate a new migration after editing models
alembic revision --autogenerate -m "describe your change"

# Roll back the most recent migration
alembic downgrade -1
```

### Client

```bash
cd client
npm install
npm run dev
```
