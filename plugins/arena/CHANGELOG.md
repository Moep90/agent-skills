# Changelog

## 0.2.0

Optional local reviewer: `--reviewer local` sends the review to an OpenAI-compatible
endpoint set by `ARENA_LOCAL_BASE_URL`, `ARENA_LOCAL_MODEL` and `ARENA_LOCAL_API_KEY`, and
falls back to the default reviewer when the endpoint does not answer (ARENA-28 to ARENA-31).

## 0.1.0

First release: cross-model author and review loop on Claude Code, Codex CLI and OpenCode,
per docs/specs/arena.md.
