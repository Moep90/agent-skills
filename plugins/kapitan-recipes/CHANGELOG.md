# Changelog

## 0.2.0

`to-recipe` takes a Docker Compose file as a source. It maps each compose key to the
`kubernetes` generator by the table of kadet-hub/recipes RCP-37, stops on the gaps listed there,
and proves the recipe at level `deploys` with a smoke test, since there is nothing to compare.

## 0.1.1

`args` is written as a mapping with the `kubernetes` generator 1.7.0 or later, so a target can
change or drop one argument.

## 0.1.0

First release: the `to-recipe` skill migrates a Helm chart or Kustomize base to a Kapitan
recipe on kadet-hub generators, per docs/specs/recipes.md.
