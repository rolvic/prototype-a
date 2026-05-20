# Prototype A — Person Registry

A simple person registration system with a web form and REST API.

## Architecture

- **Backend**: FastAPI (Python 3.12) — REST API + HTML form
- **Frontend**: nginx — static landing page
- **Database**: PostgreSQL 16 — person records
- **Cache**: Redis 7 — page view counter

## Quick Start

```bash
cp .env.example .env   # edit with real values
docker compose up -d
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API: http://localhost:8000/api/persons
- Health: http://localhost:8000/health

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Web form + person list |
| POST | /persons | Register a new person |
| GET | /api/persons | JSON list of all persons |
| GET | /health | Health check (DB + Redis) |
