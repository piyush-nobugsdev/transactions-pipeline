# Transaction Pipeline API

AI-powered transaction processing pipeline: CSV upload → async Celery
processing → data cleaning → anomaly detection → LLM batch classification →
LLM narrative summary → polling API for results.

> **Status:** Skeleton stage. Health check + dummy Celery task only.
> Real pipeline logic comes next.

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

## 1. Setup

```bash
cp .env.example .env
docker compose up --build
```

That's it — one command. It will:
1. Build the `api` image (installs Python deps from `api/requirements.txt`).
2. Start Postgres and Redis.
3. Start the FastAPI server (`api`) and the Celery worker (`worker`), both
   waiting for Postgres/Redis to report healthy first.

You should see logs from `txn_api`, `txn_worker`, `txn_postgres`, `txn_redis`
interleaved in your terminal. Leave it running.

To stop: `Ctrl+C`, then `docker compose down` (add `-v` to also wipe the
Postgres volume if you want a totally clean slate).

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
curl -X POST http://localhost:8000/debug/ping
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
├── docker-compose.yml      # orchestrates all 4 containers
├── .env.example             # template for required env vars
├── api/
│   ├── Dockerfile           # same image used by both api and worker services
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app + routes
│       ├── celery_app.py    # Celery instance config
│       └── tasks.py         # Celery task definitions
```

`api` and `worker` in `docker-compose.yml` build from the *same* Dockerfile
and image — they're just the same codebase started with two different
commands (`uvicorn ...` vs `celery ... worker`). This is a common pattern
and keeps things simple: one requirements.txt, one Dockerfile, no code
duplication.

---

## 4. Notes for the video (design decisions)

- *(none yet at this stage — will accumulate here as we build)*
