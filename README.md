# TumorXpert

TumorXpert is a local-first research sandbox for brain-tumor MRI workflows. The current release integrates a local multi-modality inference stack: DICOM or BraTS-style NIfTI intake, preprocessing, single-missing-modality synthesis, dual-model segmentation with nnU-Net and Swin UNETR, ensemble fusion, longitudinal comparison, and artifact export.

> WARNING: Research demo only. Do not use outputs for clinical decision making.

## Set up a fresh clone

Trained model checkpoints are included through Git LFS. Install
[Git LFS](https://git-lfs.com/) before cloning (the official installer also works
on older macOS versions), then download the model files:

```bash
git lfs install
git clone https://github.com/hafeezullahjamro/tumorxpert.git
cd tumorxpert
git lfs pull
```

Install the backend and frontend dependencies:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt -c backend/constraints.txt
cp .env.example .env
cd frontend
npm ci
npm run build
cd ..
```

For a new installation with Docker, start PostgreSQL:

```bash
docker compose up -d postgres
./scripts/start.sh --production
```

If you already have PostgreSQL, edit the `POSTGRES_*` values in `.env` to match
your existing database before starting. The startup script applies the schema
migrations. Register an account through the UI when using a fresh database.

This repository contains the application source, migrations, tests, dependency
lockfile, startup scripts, and all model checkpoints. Database files, local
credentials, uploaded scans, generated results, installed dependencies, and
runtime logs remain on the local machine. Copying a repository does not copy
the existing database or user accounts. `backend/.env`, when present, overrides
the shared `.env` file.

## Run on this Mac

The existing project database is `tumorxpert` in `.local-postgres/data`, on port
`55432`. The backend reads its credentials from `backend/.env`. The separate
system PostgreSQL service on port `5432` contains another project's database.

Start both servers, including the existing project database if stopped:

```bash
./scripts/start.sh --production
```

Open http://localhost:3000. API documentation is at http://127.0.0.1:8000/docs.
Both servers stay running after the terminal command finishes. Logs and process
IDs are in `.run/`. To stop the app servers:

```bash
./scripts/stop.sh
```

PostgreSQL stays running when the app servers stop. For development, use
`./scripts/start.sh` without `--production`. After frontend changes, run
`cd frontend && npm run build` before starting production mode again.

The working Python environment is `backend/.venv`; the copied `.venv-mac`
environment is retained but is not used. Intel macOS uses PyTorch 2.2.2 and CPU
inference. Large MRI studies can take several minutes to process. Redis and
Docker are optional for the current synchronous inference workflow.

Automatic artifact deletion is disabled in `backend/.env` to preserve existing
studies. A database backup is saved at
`.local-postgres/backups/tumorxpert-before-repair.dump`. Exact matching copies
restored eight missing original scan files; the recovery inventory is in
`.run/artifact-recovery.json`.

## Project layout

```
tumorxpert/
- backend/            FastAPI app, SQLAlchemy models, Alembic migrations
- frontend/           Next.js + Tailwind UI (App Router, Zustand, shadcn-inspired components)
- infra/              Future infra hooks (initdb, nginx proxy)
- storage/            Local-first artifact tree (uploads/processed/exports/temp)
- docker-compose.yml  Postgres 17 + pgAdmin + Redis scaffolding
- .env.example        Shared environment variables
- README.md           You are here
```

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker Desktop (optional, for containerized Postgres/pgAdmin/Redis services)
- PostgreSQL server process running (local service or Docker)

## 1. Start data services

```bash
docker compose up -d
```

Services exposed:

- Postgres 17 -> `5432`
- pgAdmin 4 -> `http://localhost:5050` (email `admin@tumorxpert.local`, password `tumorxpert`)
- Redis 7 -> `6379` (optional for future Celery workers)

## 2. Configure environment

```bash
cp .env.example .env
```

Adjust paths or credentials as needed. The backend reads `DATABASE_URL` or the Postgres components defined in `.env`.

Useful inference settings:

- `SEGMENTATION_BACKEND=auto` prefers Swin UNETR 3D when its checkpoint is present, otherwise falls back to nnU-Net 2D
- `SEGMENTATION_BACKEND=nnunet2d` forces the 2D checkpoint
- `SEGMENTATION_BACKEND=swinunetr3d` forces the 3D checkpoint
- `SWINUNETR_OVERLAP=0.25` controls MONAI sliding-window overlap for 3D inference

## 3. Backend setup

### Quick start (recommended)

```bash
./scripts/start-backend.sh
```

This single command:

- checks that PostgreSQL is reachable
- starts project-local Postgres (`.local-postgres`, port `55432`) when configured and currently down
- runs `alembic upgrade head`
- starts Uvicorn on `127.0.0.1:8000`

### Manual setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate             # macOS / Linux
# .\.venv\Scripts\activate           # PowerShell on Windows
pip install -r requirements.txt -c constraints.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Why Postgres must be started separately:

- Installing PostgreSQL installs binaries and service definitions.
- Your app connects to a running database server process (`postgres`), not just installed files.
- If the service/container is stopped, API routes that hit the DB (login/register/upload/etc.) will return connection errors.

Key endpoints:

- `GET /health` -> service check
- `POST /studies/upload` -> upload DICOM ZIP, or 3/4 BraTS-style NIfTI modality files
- `POST /studies/{id}/run` -> preprocessing, synthesis (if one modality is missing), dual-model segmentation, ensemble export
- `POST /compare` -> longitudinal summary

Artifacts are written under `storage/` (uploads, processed results, exports).

### Tests

```bash
cd backend
.venv/bin/python -m pytest app/tests -q
```

The suite covers authentication, health, upload, run, comparisons, and export
flows against temporary SQLite and storage, without touching the project database.

## 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000 to access the UI. Major screens include:

- Upload  - drag/drop DICOM ZIP or BraTS-style modality upload with QC heuristics
- Studies - grid/table with status badges and quick actions
- Viewer  - study detail with per-model overlays, confidence maps, and final ensemble output
- Compare - longitudinal change summary based on final stored segmentations
- Report  - embedded PDF preview plus export links (PDF, DICOM-SEG, JSON, STL)
- Jobs/Admin/Settings/Help/Auth - supporting workflows, policy controls, documentation

The frontend consumes the FastAPI endpoints through a same-origin `/api` proxy
using Axios and React Query. `API_BACKEND_URL` changes the proxy destination;
`NEXT_PUBLIC_API_BASE` optionally overrides the browser API URL. Zustand stores
persist viewer preferences locally, and Jobs displays study status from the backend.

## 5. Storage hygiene

The backend launches a background auto-delete task on startup. By default, artifacts older than seven days are removed when `AUTO_DELETE_ENABLED=true`. Adjust the policy through the Admin screen or `.env`.

## Next steps and TODOs

- Implement a genuine DICOM-SEG writer (swap in pydicom + highdicom).
- Add DICOMweb adapter for OHIF viewer integration.
- Flesh out Celery workers and Redis-backed job orchestration.
- Expand frontend brush editing to sync mask revisions back to the backend.

Happy prototyping!
