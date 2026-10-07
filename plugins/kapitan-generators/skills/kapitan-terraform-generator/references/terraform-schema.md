# Terraform generator schema

The inventory contract the kapicorp Terraform generator reads. Fields evolve between fetched
versions; confirm against the generator source under `system/` when a key is missing.

## Top-level keys

| Key | Purpose |
|---|---|
| `parameters.terraform.<gen_*>` | Generator blocks that emit provider/backend/module wiring (names are prefixed `gen_`, e.g. `gen_provider`, `gen_backend`). |
| `parameters.resources.generic.resource.<type>.<name>` | Individual Terraform resources, keyed by resource type then name, mapped to `resource "<type>" "<name>"` blocks. |
| `parameters.terraform.provider` | Provider configuration (region, project, credentials source). |
| `parameters.terraform.backend` | Remote state backend (bucket, prefix), kept in the inventory so it is consistent across targets. |

## Resource shape

A resource entry is the structured form of an HCL resource block. Keys map to Terraform
arguments; nested blocks become nested maps:

```yaml
parameters:
  resources:
    generic:
      resource:
        google_storage_bucket:
          my-bucket:
            name: ${target_name}-state
            location: EU
            versioning:
              enabled: true
```

## Interpolation: HCL vs reclass

Two `${...}` syntaxes collide in Terraform blocks. Get the escaping wrong and you get either
an unresolved-reference compile error or a literal string in the output.

- `${target_name}`, `${namespace}` — reclass/inventory references, resolved at compile time.
- `\${google_storage_bucket.terraform-state.name}` — HCL interpolation that must reach the
  generated `.tf` verbatim. Escape the `$` so reclass does not try to resolve it.

## Secrets and state

- Provider credentials and secret values use Kapitan refs, never inline. See
  `kapitan-secrets-refs`.
- State backend config lives in the inventory (see the table above), not in hand-edited
  `.tf`.

## Validated against

kapicorp Terraform generator as fetched by Kapitan 0.34 through 0.36. Re-check field names
against your project's fetched version under `system/`.
