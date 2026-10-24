# Recipes: migrating a Helm chart, Kustomize base or Compose file to Kapitan

```text
Status: Draft
Code: plugins/kapitan-recipes/
Verified against: not yet (no implementation)
```

## Problem

A team that wants to move an application from Helm or Kustomize to Kapitan
has to rebuild what the chart or base renders as inventory for kadet-hub
generators. The examples in kadet-hub/examples (`chart-vs-kapitan`,
`recipes`) show that this works for metrics-server, cert-manager and
kube-prometheus-stack, but the work is manual. The author has to read every
template, find the generator section that renders each object, and prove
afterwards that nothing was lost.

A recipe is kadet-hub's name for the result: inventory that replaces a
chart, the way a chart packages an application. The
term is in use on kadet-hub.org under `/recipes/`.

## Decisions

DEC-1: The skill lives in its own plugin `kapitan-recipes`. A recipe is an
alternative to a chart, not a generator, so it does not belong in
`kapitan-generators`. The plugin can take further recipe skills later
without touching the generator skills.

DEC-2: One skill `to-recipe` covers Helm charts, Kustomize bases and
repositories that contain either. Only the render step differs between
them. Everything after the rendered YAML is the same work: map objects to
generators, write the recipe, compare. Two skills would repeat that part.

DEC-3: "1:1" means the same objects for the values the user actually sets.
The skill renders the source with those values and compiles the recipe,
and both sides must be equal after the API server has defaulted them. It
does not map every key of `values.yaml` to an inventory path. The
generators accept the Kubernetes fields directly, so every other setting
is already reachable through the inventory, and mirroring `values.yaml`
contradicts kadet-hub's authoring guide ("no YAML mirroring").

DEC-4: When no kadet-hub generator renders an object, the skill stops and
reports the gap as a draft generator request. It does not fall back to a
`helm` input or write a generator itself. A silent fallback would produce
a recipe that is only partly migrated while looking complete.

DEC-5: The skill writes the recipe into the user's Kapitan project.
What a recipe is, how it is proven and how it is published is specified
once, in kadet-hub/recipes `docs/specs/recipes.md` (`RCP-`). This spec
covers only how the skill gets there, and the skill defers to `RCP-` where
the two disagree.

DEC-6: A Docker Compose file is a third kind of source in the same skill,
and its recipe is proven at `deploys` only (RCP-37 to RCP-39 in
kadet-hub/recipes). Mapping to generators and writing the recipe are the
same work as for a chart. What differs is the reference: a compose file
has no Kubernetes objects, and kompose output was rejected as one because
it is a heuristic translation itself. The skill therefore maps each
compose key by the table of RCP-37, stops on its gaps, and proves the
recipe by deploying it with a smoke test.

Related: [kadet-hub authoring guide](https://github.com/kadet-hub/registry/blob/main/docs/authors.md),
[chart-vs-kapitan](https://github.com/kadet-hub/examples/tree/main/chart-vs-kapitan)

## Sources and render step

The skill accepts a chart (directory, `.tgz`, repository or OCI reference
with a version), a Kustomize directory, a Docker Compose file, or a git
repository. In a repository it looks for `Chart.yaml`, `kustomization.yaml`
and compose files; with more than one candidate it asks which one is
meant.

- REC-1: The skill MUST render the source pinned to an exact version or
  commit, with the user's values or overlay, and keep that output as the
  reference for the comparison.

  A chart renders with `helm template --include-crds`, a base with
  `kustomize build`. Without `--include-crds` the CRDs in a chart's
  `crds/` directory are missing from the reference. Without a pin the
  reference changes between runs and the comparison proves nothing.

  - Test: manual: AC-1
  - Since: not implemented

- REC-2: Helm hooks and test pods MUST be listed separately and not
  migrated silently.

  `helm template` emits hook objects (annotation `helm.sh/hook`) that only
  make sense inside `helm install`, such as cert-manager's
  `startupapicheck`. The skill asks whether each one is needed outside
  Helm. Test pods and the hooks the user drops move out of the reference
  into a separate list, so the comparison does not count them as missing.

  - Test: manual: AC-1
  - Since: not implemented

- REC-9: A compose file MUST be pinned by repository, full commit SHA and
  the file's SHA-256, and its variables resolved to their defaults, as
  `docker compose config` resolves them without an `.env` file. The
  resolved file is the reference for the mapping.

  kadet-hub/recipes writes the pin as the README's compose `Source` line
  (RCP-23) and checks the SHA-256.

  - Test: manual: AC-5
  - Since: this change

## Mapping to generators

The generators come from kadet-hub's `catalog.json`. Each generator lists
the kinds it renders, so a rendered object is matched by kind first and
then checked against the generator's README for the fields it needs.

- REC-3: Every rendered object MUST map to a section of a kadet-hub
  generator, to a CRD file pinned by checksum, or to a gap (REC-5). A
  section that copies a whole object through unchanged is not a mapping.

  Without that rule every core kind would be covered by the `kubernetes`
  generator's `manifests`, and the recipe would mirror the chart's YAML.
  The first test run on cert-manager did this for its ServiceAccounts and
  webhook configurations.

  CRDs come from the upstream release file, checked against a SHA-256 and
  included with a `copy` input, as `chart-vs-kapitan` does for
  cert-manager.

  - Test: manual: AC-1
  - Since: not implemented

- REC-4: The recipe MUST follow the authoring guide. Every value is
  written once and derived where the generator derives it. Generator
  defaults are not repeated. Values the chart generates at render time,
  such as random passwords, become Kapitan refs.

  - Test: manual: AC-1
  - Since: not implemented

- REC-5: An object no generator renders MUST stop the migration with a
  report. For each gap, the report names the kind, the fields the chart
  uses, and the generator that would be closest. The report includes a
  draft for the generator request form of kadet-hub/registry. The skill
  does not open the issue.

  - Test: manual: AC-2
  - Since: not implemented

- REC-10: Every key of a compose file MUST map as the table of RCP-37
  says, and a gap listed there, or a key the table does not map, MUST stop
  the migration as REC-5 does.

  The skill carries the table in step 3. Where it and RCP-37 disagree,
  RCP-37 wins (DEC-5).

  - Test: manual: AC-5, AC-6
  - Since: this change

## Recipe layout

The skill writes the layout of RCP-1: a class directory
`inventory/classes/recipes/<name>/` with `init.yml`, one file per
component, optional classes and a `README.md`, and a target with the
user's values. It follows RCP-2 to RCP-7 for scoping, naming, style,
derived values, image pins and pass-through sections. A subchart becomes a
recipe of its own and the parent includes it.

- REC-6: Every generator dependency MUST be pinned as
  `ghcr.io/kadet-hub/<name>:<version>@sha256:<digest>` with the version and
  digest that `catalog.json` lists together, verified against the attested
  index before use.

  - Test: manual: AC-1
  - Since: not implemented

- REC-8: The skill MUST write the recipe's README with the source pin, the
  include lines, the common chart values with their inventory paths, the
  hooks left out, the RBAC renames, the proof and the steps for replacing a
  running Helm release, marked as not tested.

  - Test: manual: AC-1
  - Since: not implemented

## Comparison

- REC-7: The migration is done only when the comparison of RCP-8 to
  RCP-11 passes and the remaining differences all fall into the classes of
  RCP-12. The skill MUST report each remaining difference with its class.
  Until kadet-hub/recipes publishes `check`, the skill runs the comparison
  itself, following those requirements. Afterwards it runs a pinned
  version of `check`.

  Without kind the skill reports the comparison as not run and does not
  claim equality.

  - Test: manual: AC-1, AC-3
  - Since: not implemented

- REC-11: A compose recipe MUST be proven at level `deploys` only: no
  comparison, the recipe-side checks of RCP-38, a deploy on kind and a
  smoke test that checks what the compose file sets up (RCP-39). The
  skill MUST NOT report it as `renders`.

  - Test: manual: AC-5
  - Since: this change

## Verification

- AC-1 (REC-1, REC-2, REC-3, REC-4, REC-6, REC-7): running the skill on the
  metrics-server chart 3.14.0 with the values of
  `chart-vs-kapitan/values/metrics-server.yaml` produces a recipe that
  compiles and whose comparison shows no diff.
  Check: manual, against the target of `chart-vs-kapitan`
- AC-2 (REC-5): running the skill on a chart with a kind no generator
  renders, such as a chart with a custom resource of an unlisted operator,
  stops with a gap report and writes no recipe.
  Check: manual
- AC-3 (REC-7): without a reachable cluster the report states that the
  comparison did not run.
  Check: manual
- AC-5 (REC-9, REC-10, REC-11): running the skill on
  `contrib/docker-compose/basic.yml` of Miniflux 2.3.4 produces a recipe
  that passes `check miniflux --level deploys`.
  Check: manual, against `miniflux/` in kadet-hub/recipes#8
- AC-6 (REC-10): running the skill on a compose file with a `build:`
  service or a host bind mount stops with a gap report and writes no
  recipe.
  Check: manual
- AC-4: `scripts/validate_skills.py` passes on the skill and its
  `evals/evals.json` (marketplace.md MKT-13).
  Check: CI job `quality`

## Open questions

None. Publishing (former OQ-1) moved to kadet-hub/recipes.

## Implementation inventory

| Path | Purpose |
|---|---|
| `plugins/kapitan-recipes/skills/to-recipe/SKILL.md` | The skill |
| `plugins/kapitan-recipes/skills/to-recipe/evals/evals.json` | Trigger cases (MKT-13) |
| `plugins/kapitan-recipes/CHANGELOG.md` | Versions (MKT-6) |
| `scripts/sync_plugins.py` | Registry entry for `kapitan-recipes` |

| Value | Setting |
|---|---|
| Plugin | `kapitan-recipes` 0.2.0, category `devops` |
| Skill | `to-recipe`, category `workflow` |
| Generator source | `https://kadet-hub.org/catalog.json` |
