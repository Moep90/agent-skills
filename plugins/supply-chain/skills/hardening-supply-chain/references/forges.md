# GitHub and GitLab

Detect the forge from `git remote -v` and use its CLI: `gh` for GitHub, `glab` for GitLab.
Settings the agent cannot change through a pull or merge request (branch protection,
private reporting, alerts) go into the report as a step for an admin.

| Concern | GitHub | GitLab |
|---|---|---|
| Update bot | Dependabot (`.github/dependabot.yml`), cooldown per ecosystem | No Dependabot. Renovate (`renovate.json`, `minimumReleaseAge`) |
| Gate on dependency changes | A workflow on every `pull_request`; a `changes` job sets which scan jobs run; one final job with `if: always()` fails unless every result is `success` or `skipped`, and only that job is required. A workflow-level `paths:` filter leaves the required check pending on other PRs | `rules: - if: $CI_PIPELINE_SOURCE == "merge_request_event"` with `changes: paths:` |
| Scheduled scan | `on: schedule` plus `workflow_dispatch` | A pipeline schedule (Build > Pipeline schedules) and a job with `rules: - if: $CI_PIPELINE_SOURCE == "schedule"` |
| Built-in licence and dependency scanning | dependency-review-action reads the dependency graph | Dependency scanning and licence scanning are Ultimate-only. On Free and Premium, run the scanners from ecosystems.md as jobs |
| Gate is required | Branch ruleset or protection with the required check | Settings > Merge requests > Merge checks > "Pipelines must succeed" (all tiers) |
| Release provenance | `actions/attest-build-provenance` (Sigstore) | `RUNNER_GENERATE_ARTIFACTS_METADATA: "true"` writes `{ARTIFACT_NAME}-metadata.json`, an in-toto statement with SLSA 1.0 provenance, unsigned. The SLSA CI/CD component in the CI/CD Catalog signs it |
| Release assets | `gh release create/upload` | `glab release create` with links, or the generic package registry |
| Private vulnerability reports | Private vulnerability reporting, repository security advisories (GHSA) | A confidential issue. For a public project on GitLab.com, a maintainer can request a CVE ID from the confidential issue |
| Publish a fixed vulnerability | Publish the GHSA | Make the issue public after the release, CVE ID in the release notes |

## GitLab gate pitfalls

`rules:changes` is true for every pipeline without a push event, schedules included, so a
scheduled job never skips on paths. In merge request pipelines it compares against the
target branch. `compare_to` names another ref, but the docs warn it can give unexpected
results in forked projects and merged-results pipelines.

"Pipelines must succeed" treats a skipped pipeline as failed unless "Skipped pipelines are
considered successful" is set. If the gate job only runs on dependency changes, check that
setting, or give the pipeline an always-running job.

A merge request from a fork runs its pipeline in the fork by default, with the fork's
variables. Wherever it runs, the CI configuration comes from the merge request's branch, so
a contributor can change or drop the gate job. A green pipeline counts only when the gate
job is in it and passed, and the merge request does not touch `.gitlab-ci.yml` or its
includes; a change there needs a maintainer's review before the gate means anything. Say so
in the report when the project takes merge requests from forks.

Sources, read 2026-10-29: <https://docs.gitlab.com/ci/yaml/> (`rules:changes`),
<https://docs.gitlab.com/user/compliance/license_scanning_of_cyclonedx_files/>,
<https://docs.gitlab.com/ci/runners/configure_runners/> (artifact provenance metadata),
<https://docs.gitlab.com/ci/pipeline_security/slsa/>,
<https://docs.gitlab.com/user/project/merge_requests/auto_merge/>,
<https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/>,
<https://docs.gitlab.com/user/application_security/cve_id_request/>.
