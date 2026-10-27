---
name: kapitan-ocm-generator
category: generators
description: >-
  Use when a Kapitan project must describe its compiled output as an Open Component Model
  (OCM) component: writing a component-constructor.yaml for `ocm add component-version`,
  listing every container image of a target as an ociImage resource, pointing image access
  at a mirror or pull-through cache, or packaging a target for an air-gapped transfer. Covers
  the kadet-hub `ocm` generator, its compile-entry placement, and escaping the CLI's ${VAR}
  placeholders in the inventory.
---

# The kadet-hub `ocm` generator

`ocm` writes an OCM component constructor during `kapitan compile`. It reads the YAML that
earlier compile entries of the same target wrote, collects every `image` value and emits one
`ociImage` resource per image. Everything that is not an image (the manifests as an OCI
artifact, a Git bundle, a directory of operations files) comes from the inventory as it is.
Building, signing and transferring the component stay with the `ocm` CLI.

Do not hallucinate the schema. The parameters and failure modes are in the generator's
README (`lib/ocm/README.md` once fetched, or `ocm/README.md` in kadet-hub/generators). Read
it before writing the block.

Do not hand-write the image list or keep it in a script that greps manifests. A chart bump
that adds a sidecar is then missing from the component, and you only find out when the
target environment cannot pull it.

## Shape

```yaml
parameters:
  ocm:
    components:
      app:
        name: example.org/acme/app
        version: \${VERSION}
        provider:
          name: acme
        resources:
          manifests:
            type: ociArtifact
            version: \${VERSION}
            access:
              type: ociArtifact
              imageReference: \${REGISTRY}/acme/app-manifests:v\${VERSION}
        images:
          scan: [k8s/**/*.yml, k8s/**/*.yaml]
          access: \${PROXY_%registry_id%}/%path%
          label: upstream
          require_digest: true
  kapitan:
    compile:
      # ... every entry that writes k8s/, including mutate ...
      - input_type: kadet
        input_paths: [lib/ocm]
        output_path: .
        output_type: plain
        input_params:
          file: ocm/component-constructor.yaml
          components: ${ocm:components}
```

This is the reclass-rs form. For OmegaConf see the placeholder footgun below.

## Footguns

- **Placement.** The entry must come after every entry whose output it should scan. Kapitan
  runs entries in order, so an `ocm` entry above the `helm` entry sees no images from that
  chart. Put it last, after `mutate` too, which can change images.
- **`output_path: .`** The generator gets its own output directory as `compile_path` and
  scans relative to it. Any other `output_path` hides the rest of the target; write into a
  subdirectory with `file:` instead.
- **`output_type: plain`.** Without it Kapitan dumps the returned text as one YAML string.
- **`${VAR}` placeholders.** `${VERSION}`, `${REGISTRY}` and similar belong to the CLI,
  filled in by `ocm add cv ... VERSION=1.2.3`. Unescaped in the inventory they are
  references and fail to resolve. The escape depends on the backend: reclass-rs takes
  `\${VERSION}`; Kapitan's OmegaConf backend resolves escaped values twice, so there it is
  `${escape:VERSION}` and `${ocm.components}`. Check `.kapitan` or `--inventory-backend`
  before writing either.
- **Template tokens are `%...%`.** `%ref%`, `%registry%`, `%registry_id%` and `%path%`, no
  others. Do not write `{registry_id}`: OmegaConf rejects `{` inside `${escape:...}`. A
  static mirror needs no placeholder (`mirror.example.org/%registry%/%path%`); a mirror
  known only at build time is `${escape:PROXY_%registry_id%}/%path%` (OmegaConf) or
  `\${PROXY_%registry_id%}/%path%` (reclass-rs).
- **Resources are a map.** `resources.<name>` merges across classes; a list would be
  replaced by the last class. A class that adds an operations directory only to some
  targets adds one key.
- **Name clashes.** Resources are named after the last path segment of the repository, so
  `bitnami/redis` and `library/redis` clash and the compile fails. Map one of them in
  `images.names` (`docker.io/bitnami/redis: bitnami-redis`); do not drop the image.
- **Digest without tag.** `image@sha256:...` has no version to derive and fails the
  compile. Pin `name:tag@sha256:...`.
- **`--cache`.** The kadet cache key is the inventory, not the files the generator scans. A
  changed image with no inventory change can reuse the old constructor; compile without
  `--cache` before building the component.

## After editing

Compile, open `compiled/<target>/<file>` and check the image resources against the images
the manifests reference. Then let the CLI validate it:
`ocm add component-version --repository ./ctf --constructor compiled/<target>/<file>`
with the placeholder values set.
