# Plugins

Plugins that bundle skills and MCP config for one-command install. The repo is itself a
marketplace for three clients, via a manifest each: `.claude-plugin/` (Claude Code),
`.cursor-plugin/` (Cursor), and `.agents/plugins/` (Codex).

- `kapitan-core`: the MCP server (via `uvx kapitan-mcp-server`) plus the inventory-model,
  secrets-refs, and debugging-compile skills.
- `kapitan-generators`: the Kubernetes and Terraform generator skills, kadet authoring, and
  project scaffolding.

The MCP server command lives in one hand-written file per plugin, `plugins/<name>/.mcp.json`;
the per-client manifests (`.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/`) only
reference it, so the git URL is never duplicated.

Everything else is generated from the `PLUGINS` registry in `scripts/sync_plugins.py`: the
marketplace manifests, the per-plugin manifests, and the skill bundles (skills live once
under `skills/` and are copied in). Run `make sync-plugins` after editing the registry or a
skill; `make check-plugins` fails on drift. Do not edit generated files or the copies under
`plugins/*/skills/` directly.
