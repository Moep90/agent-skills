---
name: kapitan-debugging-compile
category: core
description: >-
  Use when a Kapitan compile fails or produces the wrong output: class-not-found errors,
  unresolved ${...} interpolation, backend mismatches, missing helm or jsonnet binaries,
  a value that is not what was set, or an unexpected diff in targets you did not touch.
  Reach for this whenever the user is stuck on "kapitan compile" output or a confusing
  compiled/ result. Maps symptoms to causes and fixes.
---

# Debugging a Kapitan compile

Work the closed loop: change inventory or a template, compile, read the diff, fix. If the
`kapitan_*` MCP tools are available, use `kapitan_compile_diff` to see what a change
produces before applying it, and read the `code` on any structured error.

## Symptom to cause

| Error code / symptom | Cause | Fix |
|---|---|---|
| `CLASS_NOT_FOUND` | A name in a `classes:` list has no matching file | Check the dotted name against `inventory/classes/`; fix the typo or remove the include. Do not paper over it by switching backend. |
| `INTERPOLATION_ERROR` (unresolved `${...}`) | The referenced key is missing after the merge | Use `kapitan_search_inventory` to find where the key should be set; add it in the right class. |
| `SECRET_REF_MISSING` | A ref file is absent under `refs/` | Ask the user to create the secret with their keys. Do not fabricate a value. |
| `HELM_BINARY_MISSING` | The helm input type needs helm on PATH | Install helm, or run the MCP server where the real CLI lives. |
| `JSONNET_IMPORT_ERROR` | A jsonnet import path does not resolve | Check the import path and that the library exists in the project. |
| Value is not what you set | You are reading a class, but a later class or the target overrides it | `kapitan_inventory_target` for the resolved value; `kapitan_class_hierarchy` for who wins. |
| Unexpected diff in other targets | A shared class changed and rippled | Treat it as a regression: confirm the change belongs in that shared class, not a single target. |
| A value became the string `"null"` | reclass-rs resolving a nested YAML null without compat mode | Set reclass-rs compatibility mode, or set the value explicitly. |

## The compile-diff discipline

After any inventory or template change, compile and diff against the committed output
before declaring the work done. An unexpected diff in a target you did not mean to touch is
a signal, not noise. Never hand-edit files under `compiled/`: change the inventory or the
template and recompile.

## Backends

Interpolation syntax depends on the backend (colon for reclass, dot for omegaconf). If a
`${...}` looks correct but will not resolve, confirm the backend with
`kapitan_project_info` and check the syntax matches.

## Validated against

Kapitan 0.34 through 0.36.
