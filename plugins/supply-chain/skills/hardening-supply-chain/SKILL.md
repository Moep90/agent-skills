---
name: hardening-supply-chain
category: workflow
description: >-
  Use when a maintainer asks whether new or updated dependencies are checked for a valid
  licence, wants a complete picture of a repository's dependencies, asks about known
  vulnerabilities in dependencies, SBOMs, third-party licence notices, SECURITY.md, or whether
  a project is aligned with the EU Cyber Resilience Act (CRA), the AI Act, NIST SSDF, NIST CSF
  or the CIS Controls, and wants the gaps closed with pull or merge requests. Applies to
  GitHub and GitLab and to any language: Cargo, Python with uv or pip, npm, Go, container
  images, vendored files, GitHub Actions and GitLab CI.
---

# Hardening a repository's supply chain

The job has two halves: an audit a maintainer can trust, then pull requests that close the
gaps the repository can close on its own. Framework wording comes from
[references/frameworks.md](references/frameworks.md), tools and gate snippets from
[references/ecosystems.md](references/ecosystems.md), and the GitHub and GitLab
mechanics (CI triggers, update bot, required checks, provenance, private reporting) from
[references/forges.md](references/forges.md). "Pull request" below means a merge request
on GitLab.

## 1. Inventory

List every ecosystem in the repository and say for each whether it ships to users:

- package manifests and lockfiles, in every directory (an editor extension, docs, tests)
- container images: the Dockerfile's base image, OS packages, and binaries fetched with
  `curl`, `go install` or `@latest`
- vendored code and data (schemas, CRDs, fixtures) with their upstream licence and NOTICE
- CI definitions (`.github/workflows/`, `.gitlab-ci.yml` and its `include:`s), the actions,
  images and components they pull, pre-commit hooks, and how each is pinned

Then read the existing checks and their triggers. A step with `continue-on-error`, a check
that only runs on a schedule, or a bot whose pull requests sit unmerged detects but does
not gate. Report it as detection.

Every number states its unit and the key it was deduplicated on: package name plus
version, advisory ID after merging aliases (CVE, GHSA, PYSEC, RUSTSEC). A package or
advisory found in two ecosystems or release targets counts once. Read a sample of the raw
records behind each number before you report it.

## 2. Scan

Scan what ships, with the tools in references/ecosystems.md, resolving each tool's current
version from its registry. Build or pull the container image and scan the image itself,
not the lockfile it was built from. If a scanner cannot run, say which ecosystem stayed
unscanned.

Licences are judged on SPDX IDs ("MIT License" and "MIT" are one licence). Copyleft in a
runtime dependency, an unknown licence, and code copied from a copyleft project are
findings for the maintainers, not for you to decide.

## 3. Map to the frameworks

Cite only from references/frameworks.md. Give each item one of four states: closed by a
PR you will open, partly met, gap, decision for the maintainers.

For the CRA, give the role as an assessment: out of scope (not monetised, recital 18),
open-source software steward (Article 3(14), Article 24), or manufacturer. Name the facts
that decide it and that only the maintainers know: whether the organisation is a legal
person, and whether companies that ship the software contribute or pay regularly. Never
call a project compliant.

## 4. Plan the pull requests

Order them by dependency:

1. Clear the advisories a blocking gate would hit. Update where a fixed version exists.
   Ignore an advisory in the scanner config, with the reason and the date, only when you
   can show the project does not reach the vulnerable code. When it is reachable or you
   cannot tell, replace or remove the dependency, or hand it to the maintainers as a
   decision; the gate waits until it is settled.
2. Gates on pull requests that change dependencies: licences against one allow list that
   every ecosystem reads, and advisories, both failing the job. The paths that trigger
   them come from the inventory: every manifest, lockfile, Dockerfile, vendored directory
   and script that fetches something that ships. The same advisory check runs weekly.
3. Release artefacts: an SBOM per release (CycloneDX or SPDX, with licences, generated
   from what ships), and third-party licence notices inside every archive, wheel, image
   and extension package. Both covered by checksums and attestation where those exist.
4. Disclosure: SECURITY.md with supported versions and the promise to publish fixed
   vulnerabilities with affected versions and severity, and release notes that put
   security fixes first.

Response times, support periods and security-only releases are the maintainers' to
promise. Put them in the pull request as questions.

## 5. Deliver

Follow the target repository's own rules first: its spec process, commit convention,
default branch, fork-only contribution. When two of your pull requests touch the same
file, merge both onto a scratch branch off the default branch and build it before opening
the second. Prove each gate in both directions: it passes on the repository and fails on a
planted violation.

## Report

End with what each pull request closes, what stays a decision for the maintainers (with
the question to ask), and what you could not verify.
