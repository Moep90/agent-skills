# Changelog

## 0.3.0

`to-recipe` proves a recipe with `check` of kadet-hub/recipes, pinned to `check-v0.10.0`, the tool
that the recipes CI and the registry gate run: `check lint`, then `--level renders`, then
`--level deploys`. A compose recipe runs `renders` first as the fast check and stays at `deploys`.
The skill's own comparison remains for sources `check` cannot take, such as a Kustomize base.
Vendored files move below the recipe's `vendor/` with a `.LICENSE` each, files above 1 MiB are
split, and the recipe directory, generator pins, README lines and `tests/` follow what `check`
and the registry gate read.

## 0.2.0

`to-recipe` takes a Docker Compose file as a source. It maps each compose key to the
`kubernetes` generator by the table of kadet-hub/recipes RCP-37, stops on the gaps listed there,
and proves the recipe at level `deploys` with a smoke test, since there is nothing to compare.
The note on `service: {}` now matches the `kubernetes` generator 1.7.0, which renders a Service for it.

## 0.1.1

`args` is written as a mapping with the `kubernetes` generator 1.7.0 or later, so a target can
change or drop one argument.

## 0.1.0

First release: the `to-recipe` skill migrates a Helm chart or Kustomize base to a Kapitan
recipe on kadet-hub generators, per docs/specs/recipes.md.
