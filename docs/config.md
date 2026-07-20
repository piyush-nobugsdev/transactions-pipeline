# Environment Validation (Single source of truth)

This document explains the project's environment-validation system: why it exists,
how it works, which files are responsible, and how CI uses it. Treat this page as
the canonical reference for adding, changing, and debugging environment variables.

## Goals

- Fail fast at CI or startup when required configuration is missing or invalid.
- Provide a single `Settings` model for the backend so all code reads one source.
- Make it easy for developers to discover required variables and example values.

## High-level flow

1. Backend defines a `Settings` model using `pydantic-settings`.
2. Application code calls `get_settings()` to obtain validated settings.
3. CI runs the settings CLI (`python -m app.core.config`) immediately after
   installing dependencies. The CLI exits non-zero on validation errors.
4. Docker images are only built / started after env validation passes.

This keeps failures early and makes debugging reproducible.

## Files of interest

- `backend/app/core/config/__init__.py` — the `Settings` model and small CLI. See also [backend/app/core/config/__init__.py](backend/app/core/config/__init__.py#L1-L200).
- `backend/app/core/infrastructure/celery_app.py` — reads `Settings` to configure Celery. See [backend/app/core/infrastructure/celery_app.py](backend/app/core/infrastructure/celery_app.py#L1-L200).
- `backend/app/main.py` — the FastAPI entrypoint that uses the validated settings indirectly. See [backend/app/main.py](backend/app/main.py#L1-L200).
- `.github/workflows/ci.yaml` — CI now runs the env-check step after dependency installation. See [ .github/workflows/ci.yaml ](.github/workflows/ci.yaml#L1-L200).

## How it works (technical)

The core is a single `Settings` class built on `pydantic-settings.BaseSettings`. When
instantiated it reads environment variables (and `.env` file when present) and
validates types and constraints.

Key helpers:

- `get_settings()` — returns a cached `Settings` instance so the app doesn't re-parse env repeatedly.
- `main_check()` — small CLI entrypoint that instantiates `Settings` and prints
  the model on success or exits with non-zero on `ValidationError`.

Example snippet (from `backend/app/core/config/__init__.py`):

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()

if __name__ == "__main__":
    import sys
    try:
        s = Settings()
        print(s.model_dump_json(indent=2))
        sys.exit(0)
    except Exception as exc:
        print("Environment validation failed:\n", exc)
        sys.exit(1)
```

## CI integration

Add the following step in the CI workflow (already implemented in this repo):

```yaml
- name: Env Validation
  run: |
    python -m app.core.config
  working-directory: backend
```

Place this immediately after dependency installation. If the step fails the
pipeline stops and logs contain the validation errors (including which fields
are missing or invalid).

## Adding or changing environment variables

1. Add the new field to `Settings` in `backend/app/core/config/__init__.py`.
   Give a sensible default if the value is optional, otherwise keep it required.
2. Add a placeholder/example value to the repository `.env.example`.
3. Update `docs/config.md` and any module-specific docs describing the variable's purpose.
4. If the variable affects Docker images (credentials, URLs), update `docker-compose.yml` or image build-time args as needed.

Example: adding a new feature flag

```py
class Settings(BaseSettings):
    FEATURE_X_ENABLED: bool = False

    class Config:
        env_file = ".env"
```

And in `.env.example`:

```
FEATURE_X_ENABLED=false
```

## Testing and troubleshooting

- Locally, create `.env` from `.env.example` and run:

```bash
python -m app.core.config
```

If the command exits non-zero, inspect the printed validation errors.

- CI: when the env-check step fails, the logs show the Pydantic `ValidationError`.

Common issues
- Wrong working directory in CI: ensure the CI runs the command from `backend` (the repo root `.env` should be present before Docker commands).
- Missing `.env` in CI: CI must create `.env` from `.env.example` before the Docker step; the env-check step runs before Docker.

## Security and secrets

- `.env.example` must never contain real secrets. Use GitHub Secrets to inject real
  values into CI if needed.
- The env-check CLI will validate presence/format of secrets but will not print
  secret values in logs (avoid placing secrets in printed output).

## Where to look next

- The Celery broker/worker configuration lives in [backend/app/core/infrastructure/celery_app.py](backend/app/core/infrastructure/celery_app.py#L1-L200) and reads `Settings` for broker/back-end URLs.
- The FastAPI app entrypoint is at [backend/app/main.py](backend/app/main.py#L1-L200).

If you want, I can extend this doc with examples for common CI secret patterns (GitHub Actions examples) or add a generated JSON schema from `Settings` for automated docs.
