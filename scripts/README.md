# Scripts

Stdlib-only helper scripts used by the Makefile and CI.

- `validate_skills.py`: checks each skill's frontmatter (name matches directory, description
  present and under 1024 chars) and that reference links resolve. Run via `make validate-skills`.
- `sync_plugins.py`: copies the mapped skills into each plugin bundle. `--check` fails on
  drift. Run via `make sync-plugins` / `make check-plugins`.
