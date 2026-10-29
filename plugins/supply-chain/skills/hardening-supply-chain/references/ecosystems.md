# Tools and gates per ecosystem

No versions here: resolve each tool's current release from its registry when you use it.
Prefer what the repository already runs over adding a tool.

| Ecosystem | Licences | Advisories | SBOM | Notices in the artefact |
|---|---|---|---|---|
| Cargo | `cargo deny check licenses` (`deny.toml` allow list) | `cargo deny check advisories` | `cargo cyclonedx -f json --spec-version 1.5 --no-build-deps --target all` (default is the host target only) | `cargo about generate --fail` with a template |
| Python, uv | `pip-licenses` in a `uv sync --frozen --no-dev --all-extras` venv, normalised to SPDX | `uv export --frozen --no-dev --all-extras --no-hashes \| pip-audit -r /dev/stdin` | `cyclonedx-py environment` on the synced venv (carries licences; `cyclonedx-py requirements` does not) | `pip-licenses --with-license-file --format=plain-vertical` into the wheel or image |
| npm | `license` field of non-dev entries in `package-lock.json` | `npm audit --omit=dev` | `@cyclonedx/cyclonedx-npm --omit dev` | `vsce`/bundlers copy `node_modules/*/LICENSE`; check the package |
| Container image | `syft <image> -o spdx-json`, then read licences | `grype <image>` or `trivy image` | `syft <image> -o cyclonedx-json` | `/usr/share/doc/*/copyright` stays in the image |
| Vendored files | Upstream `LICENSE` at the pinned ref (`gh api repos/<r>/license?ref=<tag>`) | none | one component per vendored group | copy upstream `NOTICE` next to the files |
| GitHub Actions | none | zizmor; pin by full SHA | none | none |

Extras ship, so they are scanned: `--all-extras` covers them, and extras declared as
conflicting in `[tool.uv] conflicts` are synced and scanned one at a time.

`pip-audit` and `npm audit` match versions only; neither checks whether the code reaches
the vulnerable function. Merge aliases (PYSEC, GHSA, CVE) before counting.

## One allow list

Keep the list where the main ecosystem's tool reads it and let the other gates read that
file. A gate in a second ecosystem, reading `deny.toml`:

```yaml
- name: Licences of shipped dependencies
  shell: python3 {0}
  run: |
    import json, re, sys, tomllib
    with open("deny.toml", "rb") as f:
        allow = set(tomllib.load(f)["licenses"]["allow"])
    with open("editors/vscode/package-lock.json") as f:
        packages = json.load(f)["packages"]
    lic = r"[A-Za-z0-9][A-Za-z0-9.+-]*(?: WITH [A-Za-z0-9][A-Za-z0-9.+-]*)?"
    alts = rf"{lic}(?: OR {lic})*"
    def ok(expr):
        # shortcut: IDs joined by OR, in at most one pair of parentheses; AND,
        # nesting and anything malformed fail closed.
        if not expr or not re.fullmatch(rf"{alts}|\({alts}\)", expr):
            return False
        return any(p in allow for p in expr.strip("()").split(" OR "))
    bad = [f"{name}: {meta.get('license')}" for name, meta in packages.items()
           if name and not meta.get("dev") and not ok(meta.get("license"))]
    for line in bad:
        print(f"::error::licence not in the allow list: {line}")
    sys.exit(1 if bad else 0)
```

The allow list holds SPDX identifiers, as cargo-deny requires, and an `OR` expression
passes when one of its identifiers is allowed, which is how cargo-deny judges it too. Test
it both ways: green on the repository, red after setting one shipped package to `GPL-3.0`,
to `MIT AND GPL-3.0` and to a malformed `(MIT` in a copy of the lockfile.

Excluding dev dependencies is right only when nothing bundles them. An extension or web
app built with esbuild, webpack or similar ships whatever the bundle imports, dev
dependency or not: read the bundler's config or metafile and gate, scan and list those
packages too.

## Advisory gate

Run it on pull requests whose paths touch anything the inventory found that changes what
ships (manifests, lockfiles, Dockerfiles, vendored directories, fetch scripts) or the
scanner config, as a failing step, and in a separate workflow on `schedule` plus `workflow_dispatch`. In
cargo-deny an accepted advisory is

```toml
[advisories]
ignore = [
    { id = "RUSTSEC-2023-0071", reason = "<why it does not reach us>. Checked <date>." },
]
```

`unmaintained = "all"` is cargo-deny's default and covers CIS 16.4 "still supported".

## Release

Notices and SBOM have to cover every target that ships. One pass before the per-target
builds is enough when the tool sees all targets: `cargo about` does by default, `cargo
cyclonedx` only with `--target all`. A container image gets its own SBOM from the built
image. Name the SBOM like the other release assets so the existing checksum and
attestation steps pick it up. A file copied into a Python package directory (`python/<pkg>/`) lands in a maturin
wheel without configuration. Tools installed through `taiki-e/install-action` without a
version follow the action's own manifest, so Dependabot's bump of the action updates them.

## Release notes

With git-cliff, a parser placed before the area parsers:

```toml
{ message = 'CVE-\d{4}-\d+|GHSA(-[0-9a-z]{4}){3}|RUSTSEC-\d{4}-\d{4}|PYSEC-\d{4}-\d+', group = "<!-- 0 -->Security" },
```

and `{{ group | striptags | trim }}` in the template. Groups sort by name, so the hidden
`0` puts Security first. The commit message has to name the advisory ID. A TOML literal
string (single quotes) keeps `\d` intact. Check the pattern against one real ID of each
scheme, e.g. `GHSA-c3h9-896r-86jm`, which starts with a letter.
