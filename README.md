# Visa & Debit Card Scraper Platform

A production-ready, full-stack web platform for ethically scraping publicly available information about visa requirements and debit/credit card product details. The system includes a modular backend API, background scraping jobs, a responsive frontend, database integration, authentication, security features, automated tests, and deployment via Docker and CI.

## Key Features
- Backend: FastAPI, SQLAlchemy, JWT auth, Pydantic validation, structured logging
- Scrapers: Modular design using Requests + BeautifulSoup
- Jobs: Celery worker + Beat scheduler with Redis broker
- Database: PostgreSQL (production) with SQLite fallback for local dev
- Frontend: React + Vite + TypeScript + React Query
- Security: Password hashing (bcrypt), JWT, input validation, field-level encryption (Fernet), CORS, error handling
- Testing: Pytest for backend, Vitest + React Testing Library for frontend
- Deployment: Dockerfiles, docker-compose, CI workflow

## Ethical Use Notice
This project targets public information only (e.g., card features, fees, rewards; visa requirements by country). It is NOT intended for scraping personal data or sensitive information. Respect robots.txt, sites' ToS, and all applicable laws.

## Monorepo Structure
```
backend/         # FastAPI app + Celery + SQLAlchemy models + tests
frontend/        # React + Vite app + tests
nginx/           # Nginx for serving built frontend
.github/workflows/ci.yml  # CI pipeline
.docker/         # Helper scripts
.env.example     # Example environment configuration
docker-compose.yml
```

## Quick Start (Docker)
1. Copy environment file:
   ```bash
   cp .env.example .env
   ```
2. Build and start services:
   ```bash
   docker compose up --build
   ```
3. Access services:
   - Backend API docs: http://localhost:8000/docs
   - Frontend UI: http://localhost:3000

## Local Development (without Docker)
- Backend
  ```bash
  cd backend
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
- Frontend
  ```bash
  cd frontend
  corepack enable || npm i -g corepack
  pnpm i || npm i
  pnpm dev || npm run dev
  ```

## Environment Variables
See `.env.example` for full list. Key variables:
- `DATABASE_URL` (e.g., postgres://user:pass@db:5432/app_db)
- `JWT_SECRET`
- `FERNET_KEY` (generate via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `REDIS_URL`
- `SCRAPER_USER_AGENT`

## Running Tests
- Backend:
  ```bash
  cd backend
  pytest -q
  ```
- Frontend:
  ```bash
  cd frontend
  pnpm test || npm test
  ```

## CI/CD
- GitHub Actions workflow builds and tests both backend and frontend.

## Notes
- The example scrapers parse local fixtures to ensure deterministic tests. In production, register site-specific scrapers in `backend/app/services/scraping/registry.py`.
- For production database migrations, prefer Alembic. This project auto-creates tables on startup for simplicity.