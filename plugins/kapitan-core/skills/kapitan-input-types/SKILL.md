---
name: kapitan-input-types
category: core
description: >-
  Use when choosing which input_type a compile entry should use, or what input types Kapitan
  supports: jinja2, kadet, helm, jsonnet, external, kustomize, copy, remove, cuelang, and the
  shared compile-entry shape. Reach for this whenever the user is unsure which input fits a
  job, or asks what a kapitan.compile entry needs; follow the links here for the inputs that
  have their own deep skill.
---

# Choosing a Kapitan input type

Kapitan compiles a target by running its `kapitan.compile` list. Each entry has an
`input_type` that decides how `input_paths` become output under `compiled/<target>/`. This
skill is the selector: which input for which job, and where the depth lives. It does not
re-document the inputs that have their own skill.

## The compile-entry shape

Every entry shares the same envelope; the `input_type` decides the rest.

```yaml
parameters:
  kapitan:
    compile:
      - input_type: jinja2
        input_paths: [components/mycomponent]
        output_path: manifests
        output_type: yaml   # yaml | json | plain, per input
```

## Which input for which job

| input_type | Use it for | Depth |
|---|---|---|
| `jinja2` | Templating text/config files with inventory values | Standard Jinja2; no dedicated skill |
| `kadet` | Building manifests programmatically in Python | `kapitan-writing-kadet`, `kapitan-authoring-generator` |
| `helm` | Rendering a third-party Helm chart | `kapitan-helm-input` |
| `jsonnet` | Config generated from Jsonnet | Standard Jsonnet; set the entry's `output_type` |
| `external` | Running an external command/binary to emit output | Give `command`/args and `env_vars`; output goes to `output_path` |
| `kustomize` | Rendering a Kustomize overlay | Point `input_paths` at the overlay dir |
| `copy` | Copying files verbatim into compiled output | No templating; straight copy |
| `remove` | Deleting a path from the compiled output | Prune generated files you do not want shipped |
| `cuelang` | Config generated from CUE | Niche; pass tool args on the entry |

## Reuse across inputs

Repeating the same compile/dependency wiring per component is the sign to reach for a custom
resolver: see `kapitan-omegaconf-resolvers`. It expands one compact block into the full
`kapitan.compile` and `kapitan.dependencies` entries for helm, kustomize, or any input.

## After editing

Whichever input you choose, review the result with `kapitan_compile_diff`, and never hand-edit
`compiled/` output; change the input or the inventory and recompile.

## Validated against

Kapitan 0.34 through 0.36. Input types available depend on the kapitan version and, for
`helm`/`kustomize`/`cuelang`/`external`, the corresponding tool being installed.
