# Supply chain: dependency licences, advisories and release artefacts

```text
Status: Draft
Code: plugins/supply-chain/
Verified against: not yet (no implementation)
```

## Problem

A maintainer asks whether every new or updated dependency is checked for a
valid licence, and whether the project meets the EU Cyber Resilience Act
(CRA), NIST SSDF and the CIS Controls. Answering that well takes a full pass
over every package ecosystem in the repository, the CI triggers that run the
checks, the artefacts a release ships, and the primary texts of the
frameworks.

Without guidance an agent tends to stop at the main ecosystem and the
existing licence check. It misses the secondary ecosystems (an editor
extension's npm tree, a Docker image, GitHub Actions), reports a soft-failing
advisory step as a gate, and cites framework clauses from secondary sources.
The licence notices a statically linked binary or a wheel owes its
dependencies go unnoticed because nothing fails without them.

The procedure was worked out on a Rust project with an npm extension and is
written to apply to any repository: kapicorp/kapitan and the kadet-hub
repositories are the first targets.

## Decisions

DEC-1: A new plugin `supply-chain` holds the skill. The procedure is not
specific to Kapitan, and its own version keeps changes to it out of the
Kapitan plugins' changelogs.

DEC-2: One skill, `hardening-supply-chain`, runs the whole loop: inventory,
scans, framework mapping, then the closable gaps as pull requests on the
target repository. An audit-only skill was considered; the user asked for
the loop, and the audit is its first half.

DEC-3: The framework clauses the skill relies on ship as verbatim excerpts in
`references/frameworks.md`, each with its source URL and the date it was
read. EUR-Lex blocks scripted downloads with a JavaScript challenge, and
secondary sources disagree on dates and numbering, so the skill must not
send an agent back to search engines for them.

DEC-4: The skill names tools per ecosystem but no versions. Versions are
resolved from the registry when the skill runs, and tools installed by an
action that bundles its own version manifest (taiki-e/install-action) stay
unpinned so the action's Dependabot bump updates them.

## Inventory

SUP-1: The skill MUST make the agent list every package ecosystem in the
target repository, including subdirectories, container images, vendored
code and CI actions, and say for each whether it ships to users.

  - Test: evals case "inventory"
  - Since: this change

SUP-2: Every number the agent reports MUST state its unit (unique package,
lockfile entry, advisory ID, crate entry) and come from a deduplicated
count.

  - Test: evals case "inventory"
  - Since: this change

## Licences

One allow list governs every ecosystem. Where the main ecosystem's tool
already has one (`deny.toml`, a `pyproject` licence table), the other gates
read it instead of copying it, so adding a licence stays one decision.

SUP-3: The skill MUST make the agent gate the licences of shipped
dependencies in every shipped ecosystem on pull requests that change them,
against the single allow list, failing closed on unknown or compound
licence strings.

  - Test: evals case "licence gate"
  - Since: this change

SUP-4: The skill MUST make the agent check that every distributed artefact
(archive, wheel, image, extension package) carries the third-party licence
notices of what it bundles, and add them where missing.

  - Test: evals case "release artefacts"
  - Since: this change

## Advisories

An advisory step with `continue-on-error`, or one that runs only on a
schedule, does not keep a vulnerable version out of the default branch. The
skill treats such a step as a gap, not as a gate.

SUP-5: The skill MUST make the agent block pull requests that change
dependencies on known advisories and run the same check on a schedule.

  - Test: evals case "advisories"
  - Since: this change

SUP-6: Before a blocking gate lands, the skill MUST make the agent clear the
existing advisories: update where a fixed version exists, otherwise check
whether the project reaches the vulnerable code and ignore the advisory
with that reason and a date.

  - Test: evals case "advisories"
  - Since: this change

## Release artefacts and disclosure

SUP-7: The skill MUST make the agent publish a machine-readable SBOM
(CycloneDX or SPDX) with every release, covered by the release's checksums
and provenance attestation where those exist.

  - Test: evals case "release artefacts"
  - Since: this change

SUP-8: The skill MUST make the agent check that SECURITY.md names the
supported versions and that fixed vulnerabilities are published with
affected versions and severity, and that release notes put security fixes
first.

  - Test: evals case "disclosure"
  - Since: this change

SUP-9: The skill MUST NOT make the agent commit the maintainers to response
times or support periods they have not stated. Such text goes into the pull
request as a question.

  - Test: evals case "disclosure"
  - Since: this change

## Frameworks

The CRA question has three possible answers for a free and open-source
project: out of scope (not monetised, recital 18), open-source software
steward (a legal person that supports the software on a sustained basis for
commercial use, Article 24), or manufacturer. Two of the facts that decide
it, whether the maintaining organisation is a legal person and whether
companies that use the software contribute or pay regularly, are only known
to the maintainers.

SUP-10: The skill MUST make the agent cite framework clauses from
`references/frameworks.md` and mark each gap as closed by a pull request,
partly met, a gap, or a decision for the maintainers.

  - Test: evals case "frameworks"
  - Since: this change

SUP-11: The skill MUST make the agent state the CRA role as an assessment
with the open facts, never as a legal conclusion, and MUST NOT report a
project as compliant with any framework.

  - Test: evals case "frameworks"
  - Since: this change

## Delivery

SUP-12: The skill MUST make the agent follow the target repository's own
contribution rules (spec process, commit convention, fork-only workflow)
over its own defaults.

  - Test: evals case "delivery"
  - Since: this change

SUP-13: When two pull requests touch the same file, the skill MUST make the
agent merge both onto a scratch branch off the default branch and build it
before opening the second.

  - Test: evals case "delivery"
  - Since: this change

SUP-14: The skill MUST cover GitHub and GitLab: the agent detects the forge
from the remotes and uses that forge's CI triggers, update bot, required
check, provenance and private reporting from `references/forges.md`.

GitLab differs where the gate's trust depends on it. Its dependency and
licence scanning are Ultimate-only, `rules:changes` is true for every
pipeline without a push event, and a merge request from a fork runs in the
fork with the fork's CI configuration.

  - Test: evals case "gitlab"
  - Since: this change

## Verification

`evals/evals.json` holds one case per subject above, scored by the
expected strings. A behaviour test ran the task against kapicorp/kapitan
with and without the skill, and against kadet-hub/generators without it; the
pull request lists what the skill changed.

## Implementation inventory

| Path | Content |
|---|---|
| `plugins/supply-chain/skills/hardening-supply-chain/SKILL.md` | The procedure |
| `plugins/supply-chain/skills/hardening-supply-chain/references/frameworks.md` | Verbatim CRA, AI Act, SSDF and CIS excerpts with sources |
| `plugins/supply-chain/skills/hardening-supply-chain/references/ecosystems.md` | Tools and gate snippets per ecosystem |
| `plugins/supply-chain/skills/hardening-supply-chain/references/forges.md` | GitHub and GitLab mechanics |
| `plugins/supply-chain/skills/hardening-supply-chain/evals/evals.json` | Trigger and content cases |
| `scripts/sync_plugins.py` | Registry entry `supply-chain` |
