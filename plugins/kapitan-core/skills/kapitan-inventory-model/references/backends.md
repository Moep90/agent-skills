# Inventory backends

Check which backend a project uses before writing interpolation. Read it from `.kapitan`
(the `inventory-backend` flag under `global` or a command section) or from
`kapitan_project_info`. Do not switch backends to work around an error.

## reclass (default)

- Path delimiter in references is a colon: `${a:b:c}`.
- Meta keys live under `_reclass_`.
- The reference implementation, most feature-complete.

## reclass-rs

- A Rust reimplementation, much faster on large inventories (a 325-class inventory that
  takes 65s on reclass can render in under 2s).
- Same syntax as reclass, but it does not support every feature. It ignores unknown
  `reclass-config.yml` entries with a warning.
- By default it resolves a YAML `null` in a nested reference to the string `"null"` unless
  compatibility mode is set. Watch for that if a value mysteriously becomes `"null"`.
- `kapitan_project_info` surfaces the backend and any warnings.

## omegaconf

- Path delimiter is a dot: `${a.b.c}`, matching OmegaConf's own syntax.
- Meta is renamed from `_reclass_` to `_kapitan_`.
- Escaped `\${...}` becomes resolver syntax; it uses a double-pass resolution to support
  this.
- Its class resolver finds only `.yml` files, not `.yaml`. A class saved as `.yaml` will
  look missing.

## Migration

Moving from reclass to omegaconf is a one-way `--migrate` that rewrites the inventory in
place. Back up first. Never trigger a migration to "fix" a syntax error.
