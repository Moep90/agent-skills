# MCP server tools

`kapitan-mcp-server` exposes read-first tools over stdio. Every response is
JSON with a `schema_version`. Errors return
`{"error": {"code", "message", "remediation"}}`. The project root comes from
`--project-root` or CWD auto-detect, never from the model, so tools cannot be
pointed at another project. Without a project the server still starts; tools
return `PROJECT_NOT_FOUND` and retry discovery on each call.

## Read-only inventory

### kapitan_project_info

No arguments. Returns the project root, kapitan version, inventory backend,
whether a `./kapitan` wrapper was detected, target count, and warnings. Call
it first: the backend determines interpolation syntax for the other tools.

### kapitan_list_targets

`pattern?` (glob). Returns `{targets: [{name, path, labels}]}`.

### kapitan_list_classes

`pattern?` (glob). Returns `{classes: [{dotted_name, path}]}`.

### kapitan_inventory_target

`target`, `parameter_path?` (dotted). Returns the fully resolved (merged and
interpolated) inventory for the target. With `parameter_path` it returns just
that subtree. Large responses set `truncated: true` with a `hint` to use
`parameter_path`.

### kapitan_class_hierarchy

`target`. Returns the ordered class include tree:
`{includes: [{dotted_name, path, depth}]}`. Use it to see which class sets or
overrides a value.

### kapitan_search_inventory

`query`, `kind` (key|value|regex), `scope` (classes|targets|all). Returns
matches across the raw inventory YAML: `{matches: [{path, line, snippet}]}`.

### kapitan_refs_list

No arguments. Returns `{refs: [{token, backend, path, exists}]}`. Metadata
only. This never reveals a value, and there is no reveal tool.

## Compile loop

### kapitan_compile

`targets`, `fetch=false`, `apply=true`. Compiles the targets. Writes into the
project's `compiled/` only when `apply` is true; otherwise compiles to a temp
dir. Remote fetch is off unless `fetch=true`. Returns
`{results: [{target, ok, duration_s, error?}]}`.

### kapitan_compile_diff

`targets`. Compiles into a temp dir and returns a unified diff against the
committed `compiled/`, scoped to the compiled targets. Never writes into
`compiled/`. Returns `{changed_files: [{path, diff}], unchanged_count,
truncated}`. Run this before finishing an inventory or template change.

### kapitan_lint

No arguments. Runs `kapitan lint` and returns `{ok, output}`.

## Generators

Both read the resolved inventory, so they work on any backend and need no
compile.

### kapitan_generator_trace

`targets?` (all targets if omitted). Flags every `components.*` /
`generators.*` block that no `input_type: kadet` compile entry consumes: the
silent no-op where a block emits nothing with no error. Returns
`{targets: [{target, backend, blocks: [{path, kind, wired,
matched_input_path, hint}]}], orphans}`. Run it after editing a generator
block, before `kapitan_compile_diff`. It catches unwired blocks, not mistyped
keys inside a block.

### kapitan_generator_schema

`key="components"` (dotted top-level block), `targets?`. Learns a block's
schema by example: the keys other blocks of the same family already use, with
the count of distinct blocks and example names. Keys used by exactly one
block come back in `rare_keys` as likely typos. Returns
`{key, blocks_examined, keys: [{key, count, examples}], rare_keys}`. Use it
to confirm a field name before adding it.

## Error codes

Failures from the kapitan CLI are translated to actionable codes:
`CLASS_NOT_FOUND`, `INTERPOLATION_ERROR`, `HELM_BINARY_MISSING`,
`JSONNET_IMPORT_ERROR`, plus `INVALID_INVENTORY` for unparseable YAML and
`PATH_OUTSIDE_PROJECT` for sandbox violations. Each carries a `remediation`
hint.

## Not provided

There is no `validate` tool: `kapitan validate` is not a subcommand in the
supported Kapitan line, and inventory validation happens during compile.
There is deliberately no ref-reveal tool.
