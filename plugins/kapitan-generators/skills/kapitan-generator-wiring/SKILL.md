---
name: kapitan-generator-wiring
category: generators
description: >-
  Use when a generator block produces no output, or when wiring a component or generator
  into a target. Covers the data-block-to-compile-entry-to-target chain, the silent no-op
  where a block emits nothing with no error, and which top-level inventory key each generator
  family reads. Reach for this whenever an edit compiles to zero manifests, or the user adds
  a components/generators block and expects output.
---

# Wiring a generator so it actually emits

The most common generator failure is silent: you add a block, compile succeeds, and nothing
is written. There is no inventory schema validation, so a block that no generator consumes
just disappears. Four things must all line up.

## The four-part chain

1. **The data block** lives in a class: `parameters.components.<name>` or
   `parameters.generators.<x>.<...>`.
2. **A kadet compile entry** must exist in the resolved `parameters.kapitan.compile[]` with
   `input_type: kadet` and an `input_paths` pointing at the generator that reads that key.
3. **The class is included** by the right aggregator (often an `init.yml`) so the block
   actually merges into the inventory.
4. **A target inherits the chain** — the target's `classes:` must transitively pull in both
   the data class and the compile entry.

Miss any one and you get zero manifests and no error. Break down which link is missing with
`kapitan_class_hierarchy` (is the class in the target?) and `kapitan_generator_trace` (is a
compile entry consuming the block?).

## Which key does which generator read

Each generator scans exactly one top-level key. Put data under the wrong key and it is
silently dropped:

| Inventory key | Consumed by |
|---|---|
| `parameters.components.<name>` | the kubernetes / manifest generator |
| `parameters.generators.<x>.<collection>` | the domain generator named `<x>` (e.g. a CRD generator) |
| `parameters.ingresses.<name>` | the ingress generator |
| `parameters.argocd_applications` / `argocd_projects` | the argocd generator (a sibling of `generators.argocd`, not under it) |

The keys inside a block are the generator's schema (often snake_case mapped to camelCase). A
misspelled inner key is dropped the same silent way; confirm fields against
`kapitan-kubernetes-generator` / `kapitan-terraform-generator` or the fetched generator
source.

## Verification loop

After editing a component or generator block:

1. `kapitan_generator_trace` — flags any block that no compile entry consumes (the orphan).
2. `kapitan_compile_diff` — review the manifests the block actually produced.

An unexpected empty result for a block you just added means a broken link in the chain, not
"nothing to do."

## Validated against

kapicorp/generators as fetched by Kapitan 0.34 through 0.36, on both the reclass and
omegaconf inventory backends.
