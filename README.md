# AI Code Review Assistant

Monorepo for an AI-powered code review assistant.

## Structure

```
.
├── client/   # React + TypeScript + Vite frontend
├── server/   # Python FastAPI backend
└── docker-compose.yml
```

## Getting started

Create the env files (they are gitignored):

```bash
cp client/.env.example client/.env
cp server/.env.example server/.env
```

Then run both services:

```bash
docker compose up --build
```

- Client: http://localhost:5173
- Server: http://localhost:8000 (docs at `/docs`)

## Running locally without Docker

### Server

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Client

```bash
cd client
npm install
npm run dev
```
