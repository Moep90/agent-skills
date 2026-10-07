---
name: kapitan-kubernetes-generator
category: generators
description: >-
  Use when configuring Kubernetes workloads through the kapicorp generators: the
  components: block in a Kapitan inventory that produces Deployments, StatefulSets, Services,
  ConfigMaps, Secrets, env and secretKeyRef, ports and service_port, volume mounts, and
  images. Reach for this whenever the user edits a components: entry, adds a container, wires
  a config map, or asks how to expose a port without hand-writing Kubernetes manifests.
---

# The kapicorp Kubernetes generators

The generators turn a compact `components:` block in the inventory into full Kubernetes
manifests. You describe intent (an image, some env, a port); the generator writes the
Deployment, Service, ConfigMap, and so on. You rarely write raw manifests.

Do not hallucinate the schema. The exact fields live in
[references/components-schema.md](references/components-schema.md); read it before adding or
editing a component.

## Shape

```yaml
parameters:
  components:
    web:
      image: nginx:1.27
      ports:
        http:
          service_port: 80
      env:
        LOG_LEVEL: info
```

That single block generates a Deployment, a Service exposing port 80, and the wiring
between them.

## Common tasks

- **Config maps**: put keys under `config_maps`, mount them, or expose them as env.
- **Secrets**: reference a Kapitan ref through `secretKeyRef` rather than inlining a value.
  See the `kapitan-secrets-refs` skill for the ref rule.
- **Ports and services**: `ports.<name>.service_port` drives the generated Service.
- **Mounts**: attach config maps or secrets as volume mounts.

## Generators live out of your repo

The generators are fetched as dependencies into `system/`, and versions drift between
projects. A field that works in one project may not exist in another. Confirm the fetched
generator version (`kapitan_project_info` reports it when detectable) and match the schema
reference to that version.

## After editing

Compile and diff (`kapitan_compile_diff`) to see the generated manifests before finishing.
Never hand-edit the compiled output; change the `components:` block and recompile.

## Validated against

kapicorp/generators as fetched by Kapitan 0.34 through 0.36. Re-check field names against
the version your project fetched.
