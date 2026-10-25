# Transaction Pipeline API

AI-powered transaction processing pipeline: CSV upload → async Celery
processing → data cleaning → anomaly detection → LLM batch classification →
LLM narrative summary → polling API for results.

> **Status:** Backend foundation, job metadata APIs, and the first CSV processing
> slice are in place. Upload, storage, processing dispatch, and job state
> transitions work end-to-end in the current backend implementation; anomaly
> detection, AI classification, summary generation, export, metrics, and retention
> are still pending.

---

## 0. Installing Docker (first time only)

Docker lets us package the app + its exact dependencies into "images", then
run them as isolated "containers" — so the whole team (or grader) gets an
identical environment without installing Python, Postgres, Redis, etc. by
hand. `docker compose` is the tool that starts multiple containers together
and wires up the networking between them.

- **Windows:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
  It requires WSL2 — the installer will prompt you to enable it if it isn't
  already. Restart when asked.
- **Mac:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  (choose Apple Silicon or Intel chip build correctly).
- **Linux:** Install [Docker Engine](https://docs.docker.com/engine/install/)
  for your distro, then [Docker Compose plugin](https://docs.docker.com/compose/install/linux/)
  if not bundled.

Verify the install:
```bash
docker --version
docker compose version
```
Both should print version numbers without error.

---

## 1. Start the full application

From the repository root, run:

```bash
docker compose up --build
```

This single command builds and starts the frontend, FastAPI API, Celery worker,
PostgreSQL, and Redis. Local database defaults are provided, so a `.env` file is
not required for the default setup. Docker Compose also loads a root `.env` file
if you create one to override those defaults; use `.env.example` as a reference.

When the services are ready, open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- API health: [http://localhost:8000/health](http://localhost:8000/health)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Leave the command running to keep the application available. Stop it with
`Ctrl+C`; then run `docker compose down` to remove the containers. Add `-v` to
also delete the PostgreSQL data volume.

---

## 2. Verify it works

**Health check:**
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**Exercise the Celery flow** (API enqueues a job → worker picks it up from
Redis → result goes back through Redis → API reads it):
```bash
# Enqueue
curl.exe -X POST http://localhost:8000/debug/ping #use curl.exe in powershell
# {"task_id":"<some-uuid>"}

# Poll the result (status will be PENDING for ~1s, then SUCCESS)
curl http://localhost:8000/debug/ping/<task_id-from-above>
# {"task_id":"...","status":"SUCCESS","result":"pong"}
```

If both work, the full chain — API container → Redis → worker container →
Redis → API container — is proven end to end.

---

## 3. Project structure

```
txn-pipeline/
├── docker-compose.yml      # orchestrates the API, worker, frontend, Postgres, and Redis
├── .env.example             # template for required env vars
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          # FastAPI app + routes
│   │   ├── core/             # shared infrastructure
│   │   └── modules/          # business modules
│   └── tests/
```

`api` and `worker` in `docker-compose.yml` build from the backend Dockerfile
and image — they're just the same codebase started with two different
commands (`uvicorn ...` vs `celery ... worker`). This is a common pattern
and keeps things simple: one requirements.txt, one Dockerfile, no code
duplication.

---

## 4. Notes for the video (design decisions)

- *(none yet at this stage — will accumulate here as we build)*
- The audits/jobs module owns job lifecycle use cases and keeps controllers,
  application orchestration, domain contracts, infrastructure, docs, and tests
  separated according to `AGENTS.md`.

## 5. Audits / Jobs API

The audits/jobs module exposes upload and job lifecycle operations:

```text
POST   /v1/audits/upload
POST   /v1/audits/upload/preview
POST   /v1/audits
GET    /v1/audits
GET    /v1/audits/{job_id}/status
DELETE /v1/audits/{job_id}
```

See [backend/app/modules/audits/docs/README.md](backend/app/modules/audits/docs/README.md)
for request and response details. The preview endpoint returns sample rows and
suggested column mappings. The upload UI supports automatic aliases and manual
mapping for required transaction fields before the canonical CSV is stored and
processed. Anomaly detection is not implemented yet.
