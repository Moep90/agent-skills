---
name: kapitan-writing-kadet
category: authoring
description: >-
  Use when writing or debugging a Kapitan kadet input: Python components that build
  manifests with BaseObj or BaseModel, read the inventory via inventory(), and return a
  Dict of output files. Reach for this whenever the user edits a component under a kadet
  input_path, sees kadet in parameters.kapitan.compile, or wants to generate Kubernetes or
  other config programmatically in Python rather than templating.
---

# Writing kadet components

Kadet is Kapitan's Python input type. A kadet component is Python that returns objects
Kapitan serializes to output files. Unlike jinja2, it is real code, so it unit-tests.

## Shape of a component

A kadet module exposes a `main()` that returns a `BaseObj` whose `root` maps output
filenames to content:

```python
from kapitan.inputs.kadet import BaseObj, inventory

def main():
    inv = inventory()
    name = inv.parameters.name
    obj = BaseObj()
    obj.root.deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name},
    }
    return obj
```

`inventory()` returns the resolved inventory for the current target, so you read merged and
interpolated values directly. Do not re-merge classes yourself; if the value is wrong, the
inventory is wrong, and `kapitan_inventory_target` will show you the resolved value.

## BaseObj vs BaseModel

- `BaseObj` is the classic container: build `.root` as nested dicts and lists.
- `BaseModel` (pydantic-backed, newer Kapitan) gives typed, validated components. Prefer it
  for anything with a schema worth enforcing.

## Returning multiple files

Each key under `obj.root` becomes an output document. Split resources into separate keys
when you want separate files.

## Unit-testing a kadet component

Because it is Python, import the module in a test, call `main()` with a stubbed inventory,
and assert on the returned structure. This is the main reason to prefer kadet over jinja2
for non-trivial output.

## Wiring it into a target

```yaml
parameters:
  kapitan:
    compile:
      - input_type: kadet
        input_paths:
          - components/mycomponent
        output_path: manifests
```

After editing a component, compile and diff (`kapitan_compile_diff`) before finishing.

## Validated against

Kapitan 0.34 through 0.36.
