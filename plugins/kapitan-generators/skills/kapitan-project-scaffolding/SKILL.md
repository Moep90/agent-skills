---
name: kapitan-project-scaffolding
category: scaffolding
description: >-
  Use when creating a new Kapitan project or understanding an existing one's layout:
  inventory/targets and inventory/classes structure, the kapitan-reference layout,
  cookiecutter or cruft bootstrap, the system/ libraries, and the ./kapitan docker wrapper
  pattern. Reach for this whenever the user starts a Kapitan repo from scratch, asks where a
  file should go, or wonders why "kapitan" on their PATH is a shell script.
---

# Kapitan project layout

A Kapitan project has a predictable shape. Follow it so tools and generators find things.

```
.
├── .kapitan                 # pins inventory-backend and other defaults
├── inventory/
│   ├── targets/             # one file per target; these compile
│   └── classes/             # reusable config, dotted names map to paths
├── components/              # kadet/jinja2/jsonnet inputs
├── system/                  # fetched generators and libraries
├── refs/                    # secret ref files (encrypted), never plaintext
└── compiled/                # generated output, committed, never hand-edited
```

## Bootstrapping

- `kapitan init` lays down a starter structure.
- Many teams start from the **kapitan-reference** repo, which shows a realistic layout with
  generators wired up, and copy or template from it.
- cookiecutter or cruft templates keep multiple projects consistent and let you pull
  template updates later.

## system/ libraries

Generators and shared libraries are fetched into `system/` as dependencies. They are not
your source; treat them as vendored and pin their versions. Versions drift between projects,
so a component field that works in one repo may not in another.

## The ./kapitan wrapper

kapitan-reference ships a `./kapitan` shell script that runs Kapitan inside Docker, so the
whole team uses one pinned version without local installs. When `kapitan` on PATH is that
wrapper, commands run in a container. `kapitan_project_info` detects the wrapper. Run the
MCP server where the real CLI (or the wrapper) is available.

## Where things go

- New reusable config: a class under `inventory/classes/`.
- Something that compiles: a target under `inventory/targets/`.
- Generated output: leave it to `compiled/`; do not create files there by hand.
- Secrets: refs under `refs/`, referenced from the inventory as `?{backend:path}`.

## Validated against

Kapitan 0.34 through 0.36.
