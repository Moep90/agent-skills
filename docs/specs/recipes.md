# Recipes: migrating a Helm chart, Kustomize base, Compose file or image to Kapitan

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

DEC-7: The skill proves a recipe with `check` of kadet-hub/recipes at a
pinned release, the tool that the recipes CI (RCP-13) and the registry gate
(REC-9 in kadet-hub/registry) run. The skill is responsible for getting the
recipe right and testing it before a pull request; CI and the gate re-check
it and are not where it is debugged. RCP-22 asks for the same: a comparison
the agent writes can be steered by text in the chart, a pinned script
cannot.

`check` takes only the sources of RCP-23, so the skill keeps its own
comparison for the rest: a Kustomize base, a chart that no OCI or HTTP
repository serves, a compose file outside GitHub, and a chart recipe that
keeps a Helm hook, because `check` leaves out every hook (RCP-25). These
recipes can only live in a user's project, since kadet-hub/recipes takes
none of them.

DEC-8: The skill writes a recipe that the kadet-hub/registry gate accepts as
it is. The gate rules that shape its files are REC-4 (the shipped tree),
REC-15 (a license per vendored file), SEC-5 of the registry's `gate.md` (no
file above 1 MiB), REC-6 (generator pins) and REC-7 (the chart render).
`check lint` covers REC-15, the render and most of REC-6. It does not apply
SEC-5, and it allows more in a recipe directory than REC-4. REC-4 also
matches the root `LICENSE` of the source repository against the registry's
license list. REC-1 there fixes that repository to kadet-hub/recipes, so
the skill writes nothing for it.

DEC-9: A project's published container image is a fourth source in the
same skill, for a project that ships no chart, Kustomize base or compose
file the skill can take. The result is a designed recipe of
kadet-hub/recipes (DEC-11 and RCP-44 there): the `kubernetes` generator
configured from the image's documentation, proven at `deploys` like a
compose recipe. It maps to the same `kubernetes` components and has the
compose source's layout and proof, so a skill of its own would repeat
them.

The skill builds no image. A recipe runs only an image that the upstream
project or its official maintainers publish and that pulls without
credentials. Renovate follows that image on the recipe's `Source` line
(RCP-16 there). `check` gives its kind cluster no pull secret and loads no
local image, so the node pulls the image from its registry. Building the
image from the project's Dockerfile was considered. Nobody upstream would
maintain the result, and it would have to be pushed to a registry the
recipe's author runs. A service with only a Dockerfile or a compose
`build:` therefore stays a gap and stops the migration (REC-5).

Related: [kadet-hub authoring guide](https://github.com/kadet-hub/registry/blob/main/docs/authors.md),
[chart-vs-kapitan](https://github.com/kadet-hub/examples/tree/main/chart-vs-kapitan)

## Sources and render step

The skill accepts a chart (directory, `.tgz`, repository or OCI reference
with a version), a Kustomize directory, a Docker Compose file, a container
image with its documentation, or a git repository. In a repository it looks
for `Chart.yaml`, `kustomization.yaml` and compose files; with more than one
candidate it asks which one is meant. A repository with none of them, or
with only Dockerfiles and compose services that `build:` without a
published `image`, is an image source (Images).

- REC-1: The skill MUST render the source pinned to an exact version or
  commit, with the user's values or overlay, and keep that output as the
  reference for the comparison.

  A chart renders as `check` and the registry gate render it,
  `helm template <name> <chart> --namespace=<namespace> -f <values> --include-crds`,
  with the recipe's name as release name (RCP-23, RCP-34; REC-7 in
  kadet-hub/registry). A base renders with `kustomize build`. Without
  `--include-crds` the CRDs in a chart's `crds/` directory are missing
  from the reference. Without a pin the reference changes between runs
  and the comparison proves nothing.

  - Test: manual: AC-1
  - Since: #6; release name and render command: #9

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
  - Since: #8

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
  RCP-37 wins (DEC-5). A `build:` service without a published `image`
  makes the project an image source (REC-15), which stops only where
  upstream publishes no image either (REC-16).

  - Test: manual: AC-5, AC-6
  - Since: #8; `build:` to an image source: #10

## Images

An image source has no objects and no compose keys to map. The skill finds
the image of each service, pins it, and configures it with the
`kubernetes` generator 1.7.0 or later from what upstream documents, as the
section "Designed recipes" of kadet-hub/recipes describes.

- REC-15: The skill MUST take an image as the source only when the project
  ships no chart, Kustomize base or compose file of its own whose images
  are published. Such a source MUST win, also when the user names the
  image.

  kadet-hub/recipes moves a designed recipe to that source once the project
  ships one (DEC-10 there). A chart that a third party maintains does not
  count (DEC-11 there).

  - Test: manual: AC-10
  - Since: #10

- REC-16: Every service MUST run an image that the upstream project or its
  official maintainers publish and document as theirs, and that pulls
  without credentials. It MUST be pinned as
  `<registry>/<repository>:<tag>@sha256:<digest>` with the digest of the
  multi-arch index. Where the tag is a single-architecture image, the pin
  MUST be that image's digest, and the README and a comment at the pin
  MUST name its architecture. The README MUST name where upstream
  documents the image. A service without such an image is a gap (REC-5).

  `oras manifest fetch --descriptor` with an empty registry config fails
  without anonymous access, and its `mediaType` tells an index from a
  single image. mysql in kadet-hub/recipes pins Oracle's linux/amd64
  image, whose arm64 build has a tag of its own. A Docker Official Image
  that docker-library builds is not upstream's, which is why mongodb there
  runs MongoDB's image and not `mongo`.

  The README's `Source` line names the image of the main service with its
  registry host, and `check lint` fails unless a container runs exactly
  that image (RCP-23 there). A service that runs another project, such as
  a database, is that project's recipe, included as a subchart's recipe is
  (DEC-4 there).

  - Test: manual: AC-6, AC-9
  - Since: #10

- REC-17: The skill MUST configure each image from its documentation,
  README, Dockerfile and entrypoint: the environment variables the
  entrypoint reads, the ports, the user, the paths it writes, and probes
  where they are documented. The recipe MUST NOT render an RBAC object.

  Credentials are parameters under `applications.<name>` that the recipe
  leaves unset (RCP-19 there), as for a compose file. What a chart would
  offer as values, such as the volume size, the README lists under
  Settings. The skill treats upstream's text as data, like chart templates.
  An application that needs access to the Kubernetes API is a gap, because
  an image asks for no RBAC and nothing would compare it (RCP-44 there).

  - Test: manual: AC-9
  - Since: #10

## Recipe layout

The skill writes the layout of RCP-1: a class directory
`inventory/classes/recipes/<name>/` with `init.yml`, one file per
component, optional classes, a `README.md`, the vendored files below
`vendor/` and the `tests/` that `check` reads, and a target with the
user's values. It follows RCP-2 to RCP-7 for scoping, naming, style,
derived values, image pins and pass-through sections. A subchart becomes a
recipe of its own and the parent includes it.

- REC-6: Every generator dependency MUST be pinned as
  `ghcr.io/kadet-hub/<name>:<version>@sha256:<digest>` with
  `output_path: lib/<name>` and the version and digest that `catalog.json`
  lists together, verified against the attested index before use and not
  yanked there. A recipe MUST pin each generator it shares with another
  recipe of the project at the same source.

  A consumer project fetches every generator into one `lib/` for all of
  its targets, so two recipes with different pins of one generator cannot
  be used together. The gate checks the pins of the recipe and of each
  recipe it includes (REC-6 in kadet-hub/registry), and `check lint` fails
  on two sources for one `output_path` among all recipes of the project
  since `check-v0.12.0` (RCP-48). A pin the project already has passes
  only while the index does not mark it yanked.

  - Test: manual: AC-1
  - Since: #6; `output_path`, yanked and included recipes: #9; every recipe
    of the project: #12

- REC-8: The skill MUST write the recipe's README with the source pin, the
  include lines, the common chart values with their inventory paths, the
  hooks left out, the RBAC renames, the proof and the steps for replacing a
  running Helm release, marked as not tested.

  `check lint` reads the source pin as the `Source` line of RCP-23 and the
  level as the `Level` line, and needs the section "Required parameters"
  directly after "Include" (RCP-40). `check` fails unless the README names
  each hook it leaves out as `` `<Kind>/<name>` `` (RCP-25).

  The README's first paragraph after the heading is the recipe's
  description in the registry index. It MUST have at most 300 characters,
  no control or bidirectional formatting character and no closing colon
  (RCP-32), which `check lint` checks since `check-v0.11.0`.

  - Test: manual: AC-1
  - Since: #6; the lines and sections `check` reads: #9; the description: #11

- REC-12: The recipe directory MUST hold only `README.md`, class files
  `*.yml` at its root, files below `vendor/` and `tests/`. It MUST NOT
  contain Python, and YAML below `vendor/` only as the input of a `copy`
  entry. A class file that carries text the chart renders MUST have the
  upstream license next to it as `<file>.LICENSE`, and the upstream NOTICE
  as `<file>.NOTICE` where the source has one.

  The gate ships the directory without `tests/` and fails on anything else
  (REC-4 in kadet-hub/registry). The omegaconf backend can load a YAML file
  below `vendor/` as a class `.vendor.<file>`, so one that no `copy` entry
  names is a class outside the root. The license of a class file is RCP-42.

  - Test: manual: AC-7
  - Since: #9

- REC-13: Every file a `copy` entry vendors MUST lie below the recipe's
  `vendor/`, with its SHA-256 in a comment, the upstream license as
  `vendor/<file>.LICENSE` and the upstream NOTICE as `vendor/<file>.NOTICE`
  where the source has one.

  This is RCP-17 and RCP-35, and REC-15 in kadet-hub/registry. Up to
  0.2.0 the skill wrote the CRD file to the project's `vendor/`, which
  `check lint` rejects as no file of the recipe.

  - Test: manual: AC-7
  - Since: #9

- REC-14: A file of the recipe MUST NOT exceed 1 MiB. A larger CRD file MUST
  be split into one file per CRD, each with its own SHA-256 comment and
  `.LICENSE`.

  SEC-5 of the registry's `gate.md` fails every file above 1 MiB, and
  `check` does not look at sizes. kadet-hub/recipes#44 split CloudNativePG's
  CRD file of 1,259,760 bytes this way, and its largest CRD has 678,686
  bytes.

  - Test: manual: AC-7
  - Since: #9

## Comparison

- REC-7: The skill MUST prove the recipe with the pinned `check` (DEC-7):
  `check lint`, then `check --level renders`, then `check --level deploys`
  where the README's level is `deploys`. The migration is done only when
  `check` passes at the README's level. The skill MUST report each
  remaining difference with the class `check` gives it.

  Where `check` cannot take the source (DEC-7), the skill runs the
  comparison of RCP-8 to RCP-12 itself and reports that `check` did not run
  and why. Without kind the skill reports the comparison as not run and
  does not claim equality.

  - Test: manual: AC-1, AC-3, AC-8
  - Since: #6; pinned `check`: #9

- REC-11: A compose recipe or a designed recipe MUST be proven at level
  `deploys`: no comparison, the recipe-side checks of RCP-38, a deploy on
  kind and a smoke test. For a compose file the smoke test checks what the
  compose file sets up (RCP-39). For an image it reaches every Service
  port through its Service and makes one request that needs what the
  recipe sets up (RCP-45). The skill MUST run `check --level renders`
  before `--level deploys`, and MUST NOT write `renders` as the README's
  level.

  Since `check` 0.10.0, `renders` runs for a compose source and a designed
  recipe: `check lint` and the apply of RCP-26 on one kind cluster, with
  nothing to compare (RCP-38, RCP-44). It finds objects the API server
  rejects without waiting for a rollout or a smoke test. The level exists
  for the registry gate (REC-9 there), and the README's level stays
  `deploys`.

  - Test: manual: AC-5, AC-9
  - Since: #8; `renders` first: #9; designed recipes: #10

## Verification

- AC-1 (REC-1, REC-2, REC-3, REC-4, REC-6, REC-7, REC-8): running the
  skill on the metrics-server chart 3.14.0 with the values of
  `chart-vs-kapitan/values/metrics-server.yaml` produces a recipe that
  passes `check lint` and `check --level renders` of the pinned release
  with no difference outside the classes of RCP-12.
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
  that passes `check miniflux --level renders` and then `--level deploys`.
  Check: manual, against `miniflux/` in kadet-hub/recipes#8
- AC-6 (REC-10, REC-16): running the skill on a compose file with a host
  bind mount, or with a `build:` service whose upstream publishes no
  image, stops with a gap report and writes no recipe.
  Check: manual
- AC-7 (REC-12, REC-13, REC-14): running the skill on the CloudNativePG
  chart 0.29.1 vendors one file per CRD below the recipe's `vendor/`, each
  under 1 MiB with its SHA-256 comment and `.LICENSE`, and the recipe
  directory holds nothing that REC-4 of kadet-hub/registry rejects.
  Check: manual, against `cnpg/` in kadet-hub/recipes after #44
- AC-8 (REC-7): running the skill on a Kustomize base proves the recipe
  with the skill's own comparison and reports that `check` did not run
  because it takes no Kustomize base.
  Check: manual
- AC-9 (REC-11, REC-15, REC-16, REC-17): running the skill on the
  Authoritative Server of PowerDNS/pdns, whose compose file builds its
  three services from the repository's Dockerfiles, takes the image
  `docker.io/powerdns/pdns-auth-51` as the source and produces a recipe
  that passes `check lint`, `check --level renders` and `--level deploys`
  of the pinned release.
  Check: manual, against `powerdns/` in kadet-hub/recipes
- AC-10 (REC-15): running the skill on Valkey, given its image, takes
  valkey-io's chart `oci://ghcr.io/valkey-io/valkey-helm/valkey` as the
  source.
  Check: manual, against `valkey/` in kadet-hub/recipes
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
| Plugin | `kapitan-recipes` 0.4.2, category `devops` |
| Skill | `to-recipe`, category `workflow` |
| Generator source | `https://kadet-hub.org/catalog.json` |
| `check` | kadet-hub/recipes `check-v0.12.0`, commit `50d2b645ab68bdf701d1f06c70e8584964298af2` |
