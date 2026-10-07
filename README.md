# agent-skills

Agent plugins for Claude Code, Codex CLI, Cursor and OpenCode, versioned per plugin.

| Plugin | What it does | Version |
|---|---|---|
| `kapitan-core` | Skills for the Kapitan inventory model, input types, secret refs and compile debugging | see [CHANGELOG](plugins/kapitan-core/CHANGELOG.md) |
| `kapitan-generators` | Skills for the kapicorp Kubernetes and Terraform generators, kadet authoring and project scaffolding | see [CHANGELOG](plugins/kapitan-generators/CHANGELOG.md) |

## Install

### Claude Code

```text
/plugin marketplace add Moep90/agent-skills
/plugin install kapitan-core@agent-skills
```

### Codex CLI

```bash
codex plugin marketplace add Moep90/agent-skills
codex plugin add kapitan-core@agent-skills
```

`codex plugin marketplace upgrade` fetches new versions. To stay on one release, add the
marketplace with `--ref <plugin>--v<version>`, for example `--ref kapitan-core--v0.1.0`.

### Cursor

Cursor Settings, Plugins, Team Marketplaces: add `https://github.com/Moep90/agent-skills`,
then install the plugin.

### OpenCode

OpenCode reads skills from `~/.agents/skills`. Link each skill you want:

```bash
git clone https://github.com/Moep90/agent-skills.git
ln -s "$PWD/agent-skills/plugins/kapitan-core/skills/kapitan-inventory-model" ~/.agents/skills/
```

## Versions and releases

Each plugin has its own SemVer version and changelog. A release is the git tag
`<plugin>--v<version>`.

## Development

```bash
mise install          # pinned uv and pre-commit
make sync             # test environment
make all              # lint, tests, skill validation, generator check
make test-plugin-cli  # validate the marketplace with the real claude and codex CLIs
```

Manifests and marketplace files are generated: edit the registry in
`scripts/sync_plugins.py`, then run `make sync-plugins`. A change to a plugin needs a version
bump and a changelog entry; CI checks both. Specs live in [docs/specs](docs/specs/).

## License

Apache-2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE).
