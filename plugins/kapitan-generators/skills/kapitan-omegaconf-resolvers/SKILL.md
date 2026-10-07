---
name: kapitan-omegaconf-resolvers
category: generators
description: >-
  Use when making inventory blocks reusable with custom omegaconf resolvers: an
  inventory/resolvers.py that pass_resolvers() registers, expanding one compact object into
  the full kapitan.compile and kapitan.dependencies entries. Reach for this whenever the user
  wants a duplicatable block for helm, kustomize, or any input, uses ${merge:...}/${escape:...},
  or asks how to stop copy-pasting the same compile/dependency boilerplate per component.
---

# Reusable inventory blocks with custom resolvers

On the omegaconf backend, Kapitan loads `inventory/resolvers.py` and registers whatever its
`pass_resolvers()` returns. A resolver is just a function you call from the inventory as
`${name:arg1,arg2}`. The high-value use is turning a compact object into the verbose
`kapitan.compile` / `kapitan.dependencies` wiring, so a component is one block instead of
thirty lines copied per instance.

This is the reuse mechanism behind inputs like helm and kustomize: see
`kapitan-helm-input` for the native shape a resolver expands *into*.

## The mechanism

`inventory/resolvers.py` must define `pass_resolvers()` returning a `dict` of name to
callable. Kapitan registers each with OmegaConf:

```python
def helm_block(obj):
    # obj is the resolved object passed in; return the compile/dependency fragment
    return {
        "compile": [{
            "input_type": "helm",
            "input_paths": [obj["chart_dir"]],
            "output_path": ".",
            "helm_params": {"namespace": obj["namespace"], "release_name": obj["chart_name"]},
            "helm_values": obj["helm_values"],
        }],
        "dependencies": [{
            "type": "helm", "output_path": obj["chart_dir"],
            "source": obj["source"], "version": obj["chart_version"],
            "chart_name": obj["chart_name"],
        }],
    }

def pass_resolvers():
    return {"helm_block": helm_block}
```

Now one line reuses it:

```yaml
parameters:
  kapitan: ${helm_block:${cert-manager}}
```

Every chart becomes a small `cert-manager:` object plus that one reference, instead of the
full compile/dependency pair each time. The same shape wraps kustomize or any other input.

## Built-in resolvers you already have

Kapitan ships resolvers you can use without writing any: `merge`, `dict`, `list`, `yaml`,
`escape`, `if` / `ifelse` / `and` / `or` / `not`, `from_file`, `default`, `add`, `key` /
`parentkey` / `fullkey`. `merge` is the workhorse for layering.

## Layering with merge

Build a block from a shared base plus per-instance overrides so defaults live once:

```yaml
parameters:
  chart_defaults: { namespace: ${namespace}, source: https://charts.example/ }
  cert-manager: ${merge:${chart_defaults}, {chart_name: cert-manager, chart_version: "v1.4.0"}}
```

## The escaping gotcha

A value that itself contains `${...}` and must reach the tool literally (an HCL reference, a
Helm template expression) will otherwise be resolved by omegaconf first. Wrap it with
`${escape:...}` (or the input's own escaping) so it passes through untouched.

## Testing

Resolvers are plain Python: import `resolvers.py`, call the function with a sample object, and
assert on the returned compile/dependency fragment. Then `kapitan_compile_diff` a target to
confirm the expansion, and `kapitan_generator_trace` to confirm the expanded block is wired.

## Validated against

Kapitan 0.34 through 0.36, omegaconf inventory backend.
