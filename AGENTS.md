# Repository Guidelines

## Project Structure & Module Organization
Core chatbot logic lives under `SIACASA/bot_siacasa`, arranged by Clean Architecture layers: `domain/` (entities, services), `application/` (use cases and interfaces), `infrastructure/` (OpenAI providers, repositories, NeonDB adapters), and `interfaces/web/` for the Flask + Socket.IO front end. The admin dashboard sits in `SIACASA/admin_panel` with feature-driven subpackages (`analytics/`, `support/`, `training/`) plus `static/` and `templates/`. Datasets and media live in `SIACASA/datasets`, `graphics/`, and runtime uploads in `SIACASA/uploads`. Tests mirror the runtime code in `SIACASA/tests/unit` and `SIACASA/tests/integration`.

## Build, Test, and Development Commands
- `python -m bot_siacasa.main`: boots the public chatbot (defaults to `http://localhost:3200`). Ensure `OPENAI_API_KEY` and NeonDB secrets are loaded.
- `python -m admin_panel.main`: starts the admin panel (defaults to port `4545`) and validates `NEONDB_*` and `ADMIN_*` variables before serving.
- `pm2 start ecosystem.config.js`: production entry point that spawns both services; pair with `pm2 logs virtual-agent` or `pm2 restart siacasa-admin-panel` during operations.
- `pytest`: runs the full suite; add `-q` for faster feedback or `--maxfail=1` when iterating locally.

## Coding Style & Naming Conventions
Target Python 3.11+, keep four-space indentation, and favor type hints in new modules. Maintain descriptive Spanish docstrings and logging messages to align with existing code. Follow module naming already in place (`snake_case` files, `CapWords` classes, `lower_snake_case` functions). When touching templates or static assets, co-locate helper scripts under the matching feature directory.

## Testing Guidelines
Put unit tests in `tests/unit/test_<module>.py`; integration flow tests belong in `tests/integration/`. Use `pytest` fixtures and mocks for external services, and validate happy-path plus failure handling (see `test_sentimiento_analyzer.py`). Before opening a PR, run `pytest --cov=bot_siacasa --cov=admin_panel --cov-report=term-missing` and ensure new logic keeps or improves existing coverage.

## Commit & Pull Request Guidelines
Recent history shows terse lowercase messages (e.g., `updated`, `f2`). Replace them with imperative, informative summaries such as `feat(bot): add caching layer` or `fix(admin): guard missing Neon creds`. Each PR should include: problem statement, bullet summary of changes, environment notes (new env vars, migrations), links to tracking issues, and screenshots or cURL transcripts for UI/API updates. Request review from an owner of the affected package and confirm all checks pass.

## Environment & Secrets
Copy `SIACASA/.env.example` to `.env`, then supply `OPENAI_API_KEY`, NeonDB credentials, and admin panel settings. Keep secrets out of commits; rely on systemd/PM2 environment injection for production. Local development expects the repo root on `PYTHONPATH`; activating the provided virtualenv handles this automatically.
