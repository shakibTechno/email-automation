"""
One module per thing that can be generated.

Each exposes `SCHEMA`, `SYSTEM_PROMPT`, `build_user_prompt(...)` and
`create(job, payload) -> object`, so the Celery task can dispatch on the job's
kind without knowing anything about what it is building.
"""
