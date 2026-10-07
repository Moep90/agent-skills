---
name: kapitan-terraform-generator
category: generators
description: >-
  Use when generating Terraform through the kapicorp Terraform generator: a Kapitan
  inventory that produces provider blocks, resources, and project layout for Terraform
  rather than hand-written .tf files. Reach for this whenever the user configures Terraform
  via a Kapitan components or terraform block, sets a provider, or asks how to manage cloud
  infrastructure from the inventory.
---

# The kapicorp Terraform generator

The Terraform generator produces Terraform configuration from the inventory, the same way
the Kubernetes generator produces manifests. You describe providers and resources in the
inventory; the generator writes the `.tf` output under `compiled/`.

Do not hallucinate the schema. The inventory keys, resource shape, and the HCL-vs-reclass
escaping rule live in [references/terraform-schema.md](references/terraform-schema.md); read
it before adding or editing a provider or resource.

## Layout

A target that uses the Terraform generator sets the provider and resource definitions in
its `parameters`, and the generator emits a Terraform project per target. The generated
files are output, not source: never hand-edit them, change the inventory and recompile.

## Providers and resources

Set the provider (region, project, credentials source) in the inventory. Resources are
described as structured entries the generator maps to Terraform resource blocks. The exact
keys are in [references/terraform-schema.md](references/terraform-schema.md); they evolve
between fetched versions, so confirm against the generator source under `system/` when one
is missing.

## Secrets and state

- Credentials and secret values use Kapitan refs, not inline values. See
  `kapitan-secrets-refs`.
- Terraform state configuration (backend, bucket) belongs in the inventory so it stays
  consistent across targets.

## After editing

Compile and diff (`kapitan_compile_diff`) to review the generated Terraform before applying
anything with Terraform itself.

## Validated against

kapicorp Terraform generator as fetched by Kapitan 0.34 through 0.36. Re-check field names
against your project's fetched version under `system/`.
