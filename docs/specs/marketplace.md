# Marketplace: distribution, versioning and repository health

```
Status: Draft
Code: .claude-plugin/, .agents/plugins/, plugins/*/.claude-plugin/, plugins/*/.codex-plugin/, plugins/*/CHANGELOG.md, scripts/check-plugins.sh, .pre-commit-config.yaml, .github/, renovate.json, LICENSE, README.md
Verified against: not yet (no implementation)
```

## Problem

Arena has to reach three hosts (Claude Code, Codex CLI, OpenCode), and more
general-purpose skills are likely to follow. Each skill needs its own version
so a user can tell what changed and a fix to one skill does not force a
release of the others. The existing public repository
`Moep90/agent-toolkit-for-kapitan` already ships a multi-host marketplace,
but it is a Kapitan domain toolkit and has no versioning.

## Decisions

DEC-1: This repository becomes a general marketplace, published as the public
GitHub repository `Moep90/agent-skills` under the MIT licence. Arena is its
first plugin. The Kapitan toolkit stays separate because its plugins only make
sense for Kapitan projects.

DEC-2: The layout follows the Kapitan toolkit: one marketplace file per host
at the repository root and one manifest per host inside each plugin. Cursor
manifests are left out because no Cursor use is planned.

DEC-3: Every plugin is versioned on its own with SemVer in its manifests and
released as a git tag `{name}--v{version}` created by `claude plugin tag`.
There is no release tool. `claude plugin tag` already checks that
`plugin.json` and the marketplace entry agree; a release tool such as
release-please would add a CI workflow and a bot for what is a manual,
occasional step.

DEC-4: Hermes Agent gets no install route (arena.md DEC-6).

Related: [Claude Code plugin manifest reference](https://code.claude.com/docs/en/plugins-reference),
[Codex skills](https://learn.chatgpt.com/docs/build-skills.md),
[OpenCode skills](https://opencode.ai/docs/skills)

## Layout and manifests

```
.claude-plugin/marketplace.json      # Claude Code marketplace, name "agent-skills"
.agents/plugins/marketplace.json     # Codex marketplace
plugins/<name>/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  skills/<skill>/SKILL.md
  CHANGELOG.md
  tests/
```

A plugin bundles one or more skills that are released together. Arena is one
plugin with one skill.

- MKT-1: Every directory under `plugins/` MUST be listed in both marketplace
  files, and every marketplace entry MUST point to an existing plugin
  directory.

  - Test: scripts/check-plugins.sh (AC-1)
  - Since: not implemented

- MKT-2: Every plugin MUST have `.claude-plugin/plugin.json` and
  `.codex-plugin/plugin.json` with identical `name`, `version`, `description`
  and `license`.

  The Claude manifest wins over the marketplace entry for `version`, so the
  marketplace entries carry no version of their own.

  - Test: scripts/check-plugins.sh (AC-1)
  - Since: not implemented

- MKT-3: Every manifest MUST pass `claude plugin validate --strict`.

  The command needs no login, so CI can install Claude Code and run it.

  - Test: scripts/check-plugins.sh (AC-1)
  - Since: not implemented

## Versioning

Claude Code keeps users on a plugin's `version` until it changes. A change
that is merged without a version bump therefore never reaches users who
installed the plugin, which makes the bump check below a correctness check,
not a formality.

- MKT-4: `version` MUST be a SemVer string `MAJOR.MINOR.PATCH`.

  - Test: scripts/check-plugins.sh (AC-1)
  - Since: not implemented

- MKT-5: A merge request that changes files under `plugins/<name>/` MUST set
  that plugin's version higher than the version on the current tip of the
  target branch.

  Comparing with the tip rather than the merge base catches a branch that
  was bumped to 0.2.0 while the target moved on to 0.3.0. A plugin that does
  not exist on the target tip is new; any SemVer version passes MKT-5 for it
  and MKT-4 still applies. A plugin removed by the merge request is not
  checked by MKT-5; MKT-1 requires its marketplace entries to be removed with
  it.

  Changes that only touch `plugins/<name>/tests/` are exempt, because tests
  are not installed behaviour.

  - Test: scripts/check-plugins.sh (AC-2)
  - Since: not implemented

- MKT-6: Every version in a manifest MUST have a section in the plugin's
  `CHANGELOG.md`.

  - Test: scripts/check-plugins.sh (AC-1)
  - Since: not implemented

- MKT-7: A release MUST be the tag `{name}--v{version}` created and pushed
  with `claude plugin tag --push plugins/<name>` on the default branch after
  the bump is merged.

  The Codex pin `--ref arena--v0.1.0` needs the tag on the remote; a local tag
  is not a release.

  - Test: manual: `claude plugin tag --dry-run plugins/<name>` before tagging,
    `git ls-remote --tags origin '{name}--v{version}'` after
  - Since: not implemented

## Installation per host

The root `README.md` documents installation; the commands below are what it
states.

| Host | Install |
|---|---|
| Claude Code | `/plugin marketplace add Moep90/agent-skills`, then `/plugin install arena@agent-skills` |
| Codex CLI | `codex plugin marketplace add Moep90/agent-skills`, then `codex plugin add arena@agent-skills`; `codex plugin marketplace upgrade` fetches new versions |
| OpenCode | Symlink `plugins/arena/skills/arena` to `$HOME/.agents/skills/arena`. OpenCode also reads `$HOME/.claude/skills`, but a marketplace install in Claude Code lands in the plugin cache, not there. |

Codex installs from a git snapshot of the marketplace, refreshed by
`codex plugin marketplace upgrade`. A user who wants to stay on one Arena
release can add the marketplace with `--ref arena--v0.1.0`, which is what the
per-plugin tags of MKT-7 make possible. These commands were read from the
help of codex-cli 0.160.1.

- MKT-8: `README.md` MUST document installation for Claude Code, Codex CLI and
  OpenCode, and repeat the data note of arena.md ARENA-25.

  - Test: manual: AC-3
  - Since: not implemented

## Repository health

Arena's Layer 1 tests need a logged-in `claude` on the user's subscription,
so they run locally and are not part of CI; running them in CI would need a
paid API key. CI covers everything that runs without credentials.

- MKT-9: pre-commit MUST run gitleaks, shellcheck, JSON and YAML syntax
  checks, end-of-file and trailing-whitespace fixers, and a check that
  rejects absolute home paths in committed files.

  The home-path check matches the regular expression
  `(/home|/Users)/[A-Za-z0-9._-]+` and has no exceptions. A bare prefix
  followed by a backtick, or a placeholder such as `/home/<user>`, does not
  match, so specs and docs write user paths with a placeholder. The failing
  fixtures for AC-4 are generated at test time instead of being committed.

  The home-path check exists because skills are written on a personal
  machine and a stray path in an example leaks the account name.

  - Test: CI job `pre-commit` (AC-4)
  - Since: not implemented

- MKT-10: CI on every pull request MUST run pre-commit on all files and
  `scripts/check-plugins.sh`.

  - Test: CI workflow `.github/workflows/ci.yml` (AC-4)
  - Since: not implemented

- MKT-11: Renovate MUST manage the versions of GitHub Actions and pre-commit
  hooks, with automerge disabled.

  - Test: manual: Renovate onboarding pull request lists both managers
  - Since: not implemented

- MKT-12: Commits MUST follow Conventional Commits with the plugin name as
  scope where a plugin is affected, such as `feat(arena): ...`.

  - Test: none
  - Since: not implemented

## Verification

- AC-1 (MKT-1, MKT-2, MKT-3, MKT-4, MKT-6): `scripts/check-plugins.sh` passes
  on the repository and fails on each of these fixtures: a plugin missing
  from one marketplace file, manifests with different versions, a version
  that is not SemVer, a version without changelog section.
  Check: `scripts/check-plugins.sh`, run by CI
- AC-2 (MKT-5): a branch that edits `plugins/arena/skills/arena/SKILL.md`
  without a version bump fails the check; the same branch with the bump
  passes; a branch that edits only `plugins/arena/tests/` passes without a
  bump; a branch bumped to 0.2.0 fails after the target tip moved to 0.3.0;
  a branch adding a new plugin at 0.1.0 passes; a branch deleting a plugin
  together with its marketplace entries passes.
  Changed files are taken from the merge base, versions from the target tip.
  Check: `scripts/check-plugins.sh`, run by CI
- AC-3 (MKT-8): following the README installs Arena and the documented
  invocation works. In Claude Code and Codex CLI the install comes from the
  marketplace, not a symlink, and the invocation is `/arena:arena` and
  `$arena`. In OpenCode the install is the documented symlink and the
  invocation is `/arena`.
  Check: manual
- AC-4 (MKT-9, MKT-10): the hook fails on a temporary file whose content is
  generated at test time as a home prefix joined with a literal user name,
  for both `/home` and `/Users`; it passes on this spec, which uses only bare
  prefixes and placeholders.
  Check: CI

## Open questions

None. OQ-1 was settled by a probe: `claude plugin validate --strict` passed
on a sample plugin with an empty `CLAUDE_CONFIG_DIR` and no API key, so it
needs no login and runs in CI (Claude Code 2.1.292). OQ-2 was settled from the
Codex CLI help and is recorded under Installation per host.

## Implementation inventory

| Path | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | Claude Code marketplace `agent-skills` |
| `.agents/plugins/marketplace.json` | Codex marketplace |
| `plugins/arena/.claude-plugin/plugin.json` | Arena manifest for Claude Code, version `0.1.0` |
| `plugins/arena/.codex-plugin/plugin.json` | Arena manifest for Codex, same version |
| `plugins/arena/CHANGELOG.md` | Arena changelog |
| `scripts/check-plugins.sh` | Manifest consistency, SemVer, changelog and version-bump checks |
| `.pre-commit-config.yaml` | Hooks of MKT-9 |
| `.github/workflows/ci.yml` | MKT-10 |
| `renovate.json` | MKT-11 |
| `LICENSE` | MIT |
| `README.md` | Install per host, data note |

| Value | Setting |
|---|---|
| GitHub repository | `Moep90/agent-skills`, public |
| Marketplace name | `agent-skills` |
| Tag format | `{name}--v{version}` |
| First Arena version | `0.1.0` |
