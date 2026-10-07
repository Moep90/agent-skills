---
name: kapitan-helm-input
category: generators
description: >-
  Use when rendering a Helm chart through Kapitan: the input_type helm compile entry plus the
  type helm dependency that fetches the chart, driven by chart_name, chart_version, namespace,
  and helm_values in the inventory. Reach for this whenever the user adds a chart, sets
  helm_values, wires a release_name or namespace, or asks how to pull a third-party chart into
  compiled output without vendoring it.
---

# Rendering Helm charts with Kapitan

Kapitan renders Helm charts natively with `input_type: helm`. You declare the chart as a
dependency (Kapitan fetches it) and a compile entry (Kapitan templates it with your values).
The rendered manifests land in `compiled/`; you never vendor the chart or run `helm` yourself.

Two halves live under one `parameters.<app>` block, referenced by `${<app>:key}` self-links
so a value is written once.

## Shape

```yaml
parameters:
  cert-manager:
    chart_name: cert-manager
    chart_version: "v1.4.0"
    chart_dir: system/sources/charts/${cert-manager:chart_name}
    application_version: "v1.4.0"
    namespace: ${namespace}
    helm_values:
      installCRDs: true
      prometheus:
        enabled: true
  kapitan:
    dependencies:
      - type: helm
        output_path: ${cert-manager:chart_dir}
        source: https://charts.jetstack.io/
        version: ${cert-manager:chart_version}
        chart_name: ${cert-manager:chart_name}
    compile:
      - input_type: helm
        input_paths:
          - ${cert-manager:chart_dir}
        output_path: .
        helm_params:
          namespace: ${cert-manager:namespace}
          release_name: ${cert-manager:chart_name}
        helm_values: ${cert-manager:helm_values}
```

## The two halves

- **Dependency (`type: helm`)** fetches the chart from `source` at `version` into
  `output_path`. It only runs when fetch is enabled, so the first compile of a target needs a
  fetch; later compiles reuse the fetched chart.
- **Compile (`input_type: helm`)** templates the fetched chart. `helm_params.release_name`
  and `helm_params.namespace` are the `helm template` flags; `helm_values` is the values
  document passed to the chart.

## Key contract

`chart_name`, `chart_version`, `namespace`, and `helm_values` are the values you set;
everything else references them with `${<app>:...}`. Keep `chart_dir` pointing at where the
dependency fetches, or the compile entry templates an empty directory and emits nothing.

Some inventories (especially omegaconf ones) wrap this whole block in a custom resolver so a
single line expands to the dependency and compile entries, which makes charts duplicatable.
The underlying contract is still the two halves above; see `kapitan-omegaconf-resolvers` for
that reuse mechanism.

## After editing

Compile and diff (`kapitan_compile_diff`) to review the rendered manifests. A chart bump is a
`chart_version` change plus a re-fetch, never a hand-edit of `compiled/`.

## Validated against

Kapitan 0.34 through 0.36 with Helm 3.
