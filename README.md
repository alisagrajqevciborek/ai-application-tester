# TestFlow AI — AI-Powered Application Tester

TestFlow AI is a full-stack platform that uses AI and browser automation to run comprehensive tests against web applications. It supports **functional**, **regression**, **performance**, **accessibility**, **broken-link**, and **authentication** testing — all executed in parallel and summarised into rich, AI-enhanced reports.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Option A — Docker Compose (Recommended)](#option-a--docker-compose-recommended)
  - [Option B — Run Locally (Without Docker)](#option-b--run-locally-without-docker)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Creating an Admin User](#creating-an-admin-user)
- [Running Tests](#running-tests)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌──────────────┐      ┌──────────────┐      ┌───────────┐
│   Frontend   │◄────►│   Backend    │◄────►│  Database  │
│  (Next.js)   │ REST │  (Django)    │      │ PostgreSQL │
│  Port 3000   │      │  Port 8000   │      │  / SQLite  │
└──────────────┘      └──────┬───────┘      └───────────┘
                             │
                      ┌──────▼───────┐      ┌───────────┐
                      │ Celery Worker│◄────►│   Redis    │
                      │ (Async Tasks)│      │ Port 6379  │
                      └──────────────┘      └───────────┘
```

- **Frontend** — Next.js 16 React app with Tailwind CSS and shadcn/ui components.
- **Backend** — Django 5 REST API with JWT authentication.
- **Celery Worker** — Executes test suites in parallel using Playwright for browser automation.
- **Redis** — Message broker and result backend for Celery.
- **Database** — PostgreSQL in production; SQLite fallback for local development.

---

## Tech Stack

| Layer     | Technology                                                         |
| --------- | ------------------------------------------------------------------ |
| Frontend  | Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Framer Motion |
| Backend   | Django 5, Django REST Framework, SimpleJWT                         |
| Task Queue| Celery 5 with Redis broker                                        |
| Browser   | Playwright (Chromium)                                              |
| AI        | OpenAI GPT-4o (test generation & issue analysis)                   |
| Database  | PostgreSQL (prod) / SQLite (dev fallback)                          |
| Infra     | Docker & Docker Compose                                            |

---

## Prerequisites

- **Docker** and **Docker Compose** (v2+) — *recommended approach*
- **OR** for local development:
  - Python 3.10+
  - Node.js 20+
  - npm 9+
  - Redis server
  - (Optional) PostgreSQL 14+

---

## Project Structure

```
ai-application-tester/
├── backend/
│   ├── apps/
│   │   ├── applications/    # Core app: models, views, tasks, serializers
│   │   ├── reports/         # Report generation & storage
│   │   └── users/           # Authentication & user management
│   ├── common/
│   │   ├── browser_automation/  # Playwright test runners
│   │   ├── ai_helpers.py        # OpenAI integration
│   │   ├── issue_grouper.py     # Issue deduplication & grouping
│   │   └── test_case_generator.py
│   ├── core/                # Django settings, URLs, Celery config
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # React components (UI, dashboard, reports)
│   ├── contexts/            # React Contexts (Auth, ActiveTests)
│   ├── lib/                 # API client, types, utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Getting Started

### Option A — Docker Compose (Recommended)

This spins up all four services (frontend, backend, celery worker, redis) in one command.

**1. Clone the repository**

```bash
git clone <repository-url>
cd ai-application-tester
```

**2. Configure environment variables**

Create a `.env` file in the project root (or set the variables in your shell). At minimum:

```env
# Required for AI features
OPENAI_API_KEY=sk-...

# Optional — leave blank to use SQLite in dev mode
DB_PASSWORD=

# Optional — Jira integration
JIRA_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
JIRA_PROJECT_KEY=
```

> **Tip:** If `DB_PASSWORD` is empty and `DEBUG=True`, the backend automatically falls back to SQLite — no PostgreSQL needed for local development.

**3. Start all services**

```bash
docker compose up --build
```

**4. Run database migrations**

In a separate terminal:

```bash
docker compose exec backend python manage.py migrate
```

**5. Create a superuser (admin account)**

```bash
docker compose exec backend python manage.py createsuperuser
```

Follow the prompts to set email and password.

**6. Access the application**

| Service           | URL                            |
| ----------------- | ------------------------------ |
| Frontend          | http://localhost:3000           |
| Backend API       | http://localhost:8000/api/      |
| Django Admin      | http://localhost:8000/admin/    |

---

### Option B — Run Locally (Without Docker)

#### Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set environment variables (or create backend/.env)
# At minimum set OPENAI_API_KEY for AI features

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver 0.0.0.0:8000
```

#### Redis (required for Celery)

```bash
# macOS (Homebrew)
brew install redis && redis-server

# Windows — use WSL or Docker
docker run -d -p 6379:6379 redis:7-alpine

# Linux
sudo apt install redis-server && sudo systemctl start redis
```

#### Celery Worker

In a separate terminal (with the virtual environment activated):

```bash
cd backend
celery -A core worker --loglevel=info
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at **http://localhost:3000**.

---

## Environment Variables

All environment variables can be set in a `.env` file in the `backend/` directory, or passed via `docker-compose.yml`.

| Variable                | Default                          | Description                                      |
| ----------------------- | -------------------------------- | ------------------------------------------------ |
| `DEBUG`                 | `True`                           | Enable Django debug mode                         |
| `SECRET_KEY`            | *(insecure default)*             | Django secret key — **change in production**      |
| `ALLOWED_HOSTS`         | `localhost,127.0.0.1`            | Comma-separated allowed hostnames                |
| `DB_NAME`               | `ai_app_tester`                  | PostgreSQL database name                         |
| `DB_USER`               | `postgres`                       | PostgreSQL user                                  |
| `DB_PASSWORD`           | *(empty — triggers SQLite)*      | PostgreSQL password                              |
| `DB_HOST`               | `localhost`                      | PostgreSQL host                                  |
| `DB_PORT`               | `5432`                           | PostgreSQL port                                  |
| `CELERY_BROKER_URL`     | `redis://localhost:6379/0`       | Redis URL for Celery broker                      |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0`       | Redis URL for Celery results                     |
| `OPENAI_API_KEY`        | *(empty)*                        | OpenAI API key for AI features                   |
| `OPENAI_MODEL`          | `gpt-4o`                         | OpenAI model to use                              |
| `JIRA_URL`              | *(empty)*                        | Jira instance URL                                |
| `JIRA_EMAIL`            | *(empty)*                        | Jira account email                               |
| `JIRA_API_TOKEN`        | *(empty)*                        | Jira API token                                   |
| `JIRA_PROJECT_KEY`      | *(empty)*                        | Jira project key for issue creation              |
| `EMAIL_HOST_USER`       | *(empty)*                        | SMTP email username                              |
| `EMAIL_HOST_PASSWORD`   | *(empty)*                        | SMTP email password                              |
| `CLOUDINARY_CLOUD_NAME` | *(empty)*                        | Cloudinary cloud name for image storage          |
| `CLOUDINARY_API_KEY`    | *(empty)*                        | Cloudinary API key                               |
| `CLOUDINARY_API_SECRET` | *(empty)*                        | Cloudinary API secret                            |

---

## Database Setup

### SQLite (Default for Development)

No configuration needed. When `DEBUG=True` and `DB_PASSWORD` is empty, Django automatically uses SQLite at `backend/db.sqlite3`.

### PostgreSQL (Production / Supabase)

Set the `DB_*` environment variables to point to your PostgreSQL instance:

```env
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432
```

Then run migrations:

```bash
# Docker
docker compose exec backend python manage.py migrate

# Local
cd backend && python manage.py migrate
```

---

## Creating an Admin User

```bash
# Docker
docker compose exec backend python manage.py createsuperuser

# Local
cd backend && python manage.py createsuperuser
```

Access the Django admin panel at **http://localhost:8000/admin/**.

---

## Running Tests

### From the Web UI

1. Log in at http://localhost:3000/login
2. Register an application (provide URL, name, and optional login credentials)
3. Choose a test type:
   - **General** — runs all test suites in parallel (functional, regression, performance, accessibility, broken links, authentication)
   - **Functional** — UI interaction and form testing
   - **Regression** — visual and behavioral regression checks
   - **Performance** — page load times and resource analysis
   - **Accessibility** — WCAG compliance checks
4. Monitor real-time progress via the floating **Active Tests Widget**
5. View detailed AI-enhanced reports with collapsible step-by-step results

### Parallel Testing Architecture

When a **General** test is started:

1. The backend creates a `TestRun` with status `pending`
2. A Celery task dispatches individual test steps in parallel using `chord` + `group`
3. Each step (functional, regression, performance, etc.) runs independently and reports its `TestRunStepResult`
4. An aggregation task collects all results, calculates overall pass/fail rates, and generates an AI-enhanced detailed report
5. The frontend polls for `step_results` and displays real-time progress

---

## API Endpoints

### Authentication

| Method | Endpoint              | Description              |
| ------ | --------------------- | ------------------------ |
| POST   | `/api/auth/login/`    | Obtain JWT tokens        |
| POST   | `/api/auth/register/` | Create a new account     |
| POST   | `/api/auth/refresh/`  | Refresh an access token  |
| GET    | `/api/auth/profile/`  | Get current user profile |

### Applications & Test Runs

| Method | Endpoint                                    | Description                        |
| ------ | ------------------------------------------- | ---------------------------------- |
| GET    | `/api/applications/`                        | List user's applications           |
| POST   | `/api/applications/`                        | Register a new application         |
| GET    | `/api/applications/<id>/`                   | Get application details            |
| GET    | `/api/applications/<id>/test-runs/`         | List test runs for an application  |
| POST   | `/api/applications/<id>/test-runs/`         | Start a new test run               |
| GET    | `/api/applications/test-runs/<id>/`         | Get test run details & step results|
| POST   | `/api/applications/test-runs/<id>/cancel/`  | Cancel a running test              |

### AI Test Cases

| Method | Endpoint                                       | Description                  |
| ------ | ---------------------------------------------- | ---------------------------- |
| POST   | `/api/applications/test-cases/generate/`       | Generate AI test cases       |
| GET    | `/api/applications/test-cases/`                | List generated test cases    |
| POST   | `/api/applications/test-cases/<id>/run/`       | Run a generated test case    |

### Reports

| Method | Endpoint              | Description          |
| ------ | --------------------- | -------------------- |
| GET    | `/api/reports/`       | List all reports     |
| GET    | `/api/reports/<id>/`  | Get report details   |

---

## Troubleshooting

### `Module not found: Can't resolve 'react-markdown'`

Ensure dependencies are installed inside the `frontend/` directory:

```bash
cd frontend
rm -rf node_modules package-lock.json .next
npm install
npm run dev
```

### `EADDRINUSE: address already in use :::3000`

Another process is using port 3000. Find and kill it:

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:3000 | xargs kill -9
```

### `psycopg2.OperationalError: no password supplied`

Either set `DB_PASSWORD` in your environment, or leave it empty to use SQLite (only works when `DEBUG=True`).

### Django `APPEND_SLASH` POST redirect error

All API endpoints in this project include trailing slashes. Ensure your API calls use trailing slashes (e.g., `/api/auth/login/` not `/api/auth/login`).

### Celery tasks not running

Make sure Redis is running and the Celery worker is started:

```bash
# Docker
docker compose logs celery_worker

# Local — start Redis, then in a separate terminal:
cd backend
celery -A core worker --loglevel=info
```

### Docker containers not starting

```bash
# Rebuild from scratch
docker compose down -v
docker compose up --build

# Check logs
docker compose logs -f
```

---

## License

This project is proprietary. All rights reserved.

