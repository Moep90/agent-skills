---
name: kapitan-inventory-model
category: core
description: >-
  Use whenever the user works with a Kapitan inventory: targets, classes, reclass,
  reclass-rs, omegaconf, parameter merging, ${...} interpolation, target labels, or edits
  files under inventory/ or a .kapitan file. Reach for this even when the user does not say
  "Kapitan" but is clearly editing a targets/ or classes/ YAML tree and wondering why a
  value is not what they set. Explains how classes load, how parameters merge, and when
  interpolation resolves.
---

# The Kapitan inventory model

Kapitan resolves an inventory in two phases. Get this order wrong and you will guess wrong
about every value.

1. **Merge.** For a target, Kapitan loads its classes depth-first. Each class contributes
   a `parameters` block. These deep-merge in include order: later entries override earlier
   ones, and the target's own `parameters` win last.
2. **Interpolate.** Only after the full merge does Kapitan resolve `${...}` references,
   against the merged result. A `${foo}` that looks unresolved in one class may resolve
   fine once another class higher in the include order supplies `foo`.

So `namespace: ${target_name}` in a base class resolves to whatever `target_name` ends up
being after merging, not what it is in that one file.

## Use the tools, do not merge YAML in your head

If the `kapitan_*` MCP tools are available:

- Call `kapitan_inventory_target` to get the fully resolved (merged and interpolated)
  inventory for a target. Pass a dotted `parameter_path` like `mysql.image` to fetch one
  subtree instead of the whole thing.
- Call `kapitan_class_hierarchy` to see the ordered include tree, so you can tell which
  class set or overrode a value.
- Call `kapitan_search_inventory` to find where a key is defined across the raw YAML.

Manually merging classes is the single most common way agents get Kapitan wrong.

## Targets and classes

- A **target** (`inventory/targets/<name>.yml`) is what compiles. It lists `classes:` and
  may set its own `parameters:`.
- A **class** (`inventory/classes/<dotted.name>.yml`) is reusable configuration. The dotted
  name maps to a path: `component.mysql` is `inventory/classes/component/mysql.yml`.
- A class can include other classes via its own `classes:` list. Includes load depth-first.

## Target labels

Targets carry labels (under `parameters.labels` or the target metadata) used to select
groups of targets. When asked "which targets are production", look at labels rather than
guessing from names.

## Backends change the syntax

Three inventory backends exist and they are not interchangeable in syntax. Read
[references/backends.md](references/backends.md) before writing interpolation, and check the
project's `.kapitan` (or `kapitan_project_info`) to learn which backend is active.

For the exact merge and interpolation rules with worked examples, read
[references/merge-and-interpolation.md](references/merge-and-interpolation.md). For class
wildcards and the `.yml` vs `.yaml` trap, read
[references/class-wildcards.md](references/class-wildcards.md).

## Validated against

Kapitan 0.34 through 0.36, backends reclass, reclass-rs, omegaconf.
