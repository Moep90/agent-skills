# agent-skills

Agent plugins for Claude Code, Codex CLI, Cursor and OpenCode, versioned per plugin.

| Plugin | What it does | Version |
|---|---|---|
| `kapitan-core` | Kapitan MCP server plus skills for the inventory model, secret refs and compile debugging | see [CHANGELOG](plugins/kapitan-core/CHANGELOG.md) |
| `kapitan-generators` | Skills for the kapicorp Kubernetes and Terraform generators, kadet authoring and project scaffolding | see [CHANGELOG](plugins/kapitan-generators/CHANGELOG.md) |

The Kapitan MCP server runs with `uvx`, so `uv` must be installed; see
[docs/kapitan-mcp-server.md](docs/kapitan-mcp-server.md).

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

MCP servers are configured by hand in OpenCode, using the command in the plugin's
`.mcp.json`.

## Versions and releases

Each plugin has its own SemVer version and changelog. A release is the git tag
`<plugin>--v<version>`. A plugin's MCP server is installed from the plugin's release tag, so a
plugin version always runs the server code it was released with.

## Development

```bash
mise install          # pinned uv and pre-commit
make sync             # server environment
make all              # lint, typecheck, unit tests, skill validation, generator check
make test-plugin-cli  # validate the marketplace with the real claude and codex CLIs
```

Manifests and marketplace files are generated: edit the registry in
`scripts/sync_plugins.py`, then run `make sync-plugins`. A change to a plugin needs a version
bump and a changelog entry; CI checks both. Specs live in [docs/specs](docs/specs/).

## License

Apache-2.0, see [LICENSE](LICENSE) and [NOTICE](NOTICE).
