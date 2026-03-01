# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrackAI is a lightweight experiment tracker for deep learning, built as an alternative to tools like Neptune.ai and Weights & Biases. It consists of a FastAPI backend with a React/TypeScript frontend for visualizing experiments.

## Development Commands

### Quick Start (Production Mode)

TrackAI serves both backend and frontend from a single port in production:

```bash
# Start everything (automatically finds available port starting from 8000)
./start.sh
```

This script:
- Finds the first available port starting from 8000
- Builds the frontend
- Serves everything from the backend on the selected port

### Development Mode (with Hot Reload)

For active frontend development with hot reload:

```bash
# Run backend and frontend separately
./dev.sh
```

This script:
- Finds available ports for both backend (starting from 8000) and frontend (starting from 5173)
- Starts backend and frontend on the selected ports
- Frontend automatically proxies `/api` requests to the backend
- Displays URLs for both servers

### Backend (Python/FastAPI)

The backend uses **uv** for Python dependency management. Always use uv commands:

```bash
# Install dependencies
cd backend && uv sync

# Run the server
cd backend && uv run uvicorn trackai.api.main:app --reload

# Run example scripts
cd backend && uv run python examples/simple_experiment.py

# Import Neptune export data
cd backend && uv run python scripts/import_exports.py
```

**Important**: Before running custom Python scripts, access the uv skill for better understanding how to run and manage them.

### Frontend (React/TypeScript/Vite)

```bash
# Install dependencies
cd frontend && npm install

# Run development server (default: http://localhost:5173)
cd frontend && npm run dev

# Build for production (outputs to ../static)
cd frontend && npm run build

# Build with type checking
cd frontend && npm run build:check

# Lint code
cd frontend && npm run lint
```

## Architecture Overview

### Backend Architecture

**Framework**: FastAPI with SQLAlchemy ORM

**Database**:
- SQLite database stored at `~/.trackai/trackai.db` (centralized location)
- Can be overridden via `TRACKAI_DB_PATH` environment variable
- Tables: `projects`, `runs`, `metrics`, `configs`, `files`, `custom_views`, `dashboards`
- Metrics use EAV (Entity-Attribute-Value) model for flexibility

**Key Components**:
- `src/trackai/__init__.py` - Public API (`init()`, `log()`, `log_system()`, `finish()`)
- `src/trackai/run.py` - Run class that manages experiment lifecycle
- `src/trackai/services/logger.py` - LoggingService for database operations
- `src/trackai/api/main.py` - FastAPI app entry point
- `src/trackai/api/routes/` - API route handlers (projects, runs, metrics, mcp)
- `src/trackai/db/schema.py` - SQLAlchemy table definitions
- `src/trackai/db/connection.py` - Database connection and initialization

**Python Logging API**:
TrackAI provides a trackio-compatible API for logging experiments:
- `trackai.init()` - Initialize a run (supports resume modes: "never", "allow", "must")
- `trackai.log()` - Log training metrics with step numbers
- `trackai.log_system()` - Log system metrics without steps (uses timestamps)
- `trackai.finish()` - Mark run as completed
- Supports context manager pattern (`with trackai.init() as run:`)

### Frontend Architecture

**Framework**: React 19 with TypeScript, Vite build tool

**Key Libraries**:
- React Router v7 - Client-side routing
- TanStack Query (React Query) v5 - Data fetching and caching
- TanStack Virtual - Virtualized tables for performance
- Plotly.js - Interactive charts
- Tailwind CSS v4 - Styling
- React Grid Layout - Dashboard widget layout

**Directory Structure**:
- `src/api/client.ts` - Axios API client and React Query hooks
- `src/pages/` - Page components (ProjectsPage, RunsPage, RunDetailPage, CompareRunsPage, DashboardPage)
- `src/components/` - Reusable components
  - `Layout.tsx` - Main app layout with navigation
  - `RunsTable/` - Virtualized table for runs list
  - `Charts/` - Metric visualization components
  - `Dashboard/` - Dashboard widgets

**Routing**:
- `/projects` - List all projects
- `/projects/:projectId/runs` - List runs for a project
- `/projects/:projectId/dashboard` - Project dashboard
- `/runs/:runId` - Run detail page with metrics
- `/compare` - Compare runs side-by-side

**Data Flow**:
- React Query hooks (defined in `client.ts`) handle all API calls
- 30-second stale time, no refetch on window focus
- Virtualized tables for efficient rendering of large datasets

### API Endpoints

**Projects**:
- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project with summary stats
- `POST /api/projects` - Create new project
- `DELETE /api/projects/{project_id}` - Delete project

**Runs**:
- `GET /api/runs` - List runs (supports filters, pagination, sorting)
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/{run_id}/summary` - Get run summary with metrics
- `GET /api/runs/{run_id}/config` - Get run configuration
- `POST /api/runs` - Create new run
- `PATCH /api/runs/{run_id}/state` - Update run state
- `DELETE /api/runs/{run_id}` - Delete run

**Metrics**:
- `GET /api/metrics/runs/{run_id}` - List all metric names for a run
- `GET /api/metrics/runs/{run_id}/metric/{metric_path}` - Get metric values
- `POST /api/metrics/compare` - Compare metrics across multiple runs

## Database Management

**Check statistics**:
```bash
sqlite3 ~/.trackai/trackai.db "SELECT
  (SELECT COUNT(*) FROM projects) as projects,
  (SELECT COUNT(*) FROM runs) as runs,
  (SELECT COUNT(*) FROM metrics) as metrics;"
```

**Backup**:
```bash
cp ~/.trackai/trackai.db ~/backups/trackai-backup.db
```

**Reset (deletes all data)**:
```bash
rm ~/.trackai/trackai.db
```

## Development Workflow

### Production Mode (Single Port)

Run everything from a single command:

```bash
./start.sh
```

The backend serves the built frontend from the `/static` directory. The script automatically finds an available port starting from 8000 and displays the URL.

### Development Mode (Hot Reload)

For active development with frontend hot reload:

```bash
./dev.sh
```

The script automatically finds available ports for both servers:
- Backend: starts from port 8000
- Frontend: starts from port 5173
- Frontend automatically proxies `/api` requests to the backend's port

### Adding New Features

**Backend**:
1. Update `db/schema.py` if database changes are needed
2. Add route handlers in `api/routes/`
3. Register router in `api/main.py`
4. Add/update service methods in `services/`

**Frontend**:
1. Add API functions and hooks to `api/client.ts`
2. Create page components in `pages/`
3. Add reusable components in `components/`
4. Update routing in `App.tsx`

## Key Design Decisions

- **Metrics Storage**: Uses EAV model to support arbitrary metric structures without schema changes
- **Database Location**: Centralized at `~/.trackai/trackai.db` to access experiments from any project
- **API Compatibility**: Python API designed to be trackio-compatible for easy migration
- **Frontend Performance**: Virtualized tables and React Query caching for handling large datasets
- **Resume Support**: Runs can be resumed using `resume="allow"` or `resume="must"` modes
