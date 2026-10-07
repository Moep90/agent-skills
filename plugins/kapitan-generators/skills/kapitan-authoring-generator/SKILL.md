---
name: kapitan-authoring-generator
category: generators
description: >-
  Use when writing a reusable Kapitan generator: a kadet library that reads a
  parameters.generators.<name> (or components) block and emits many manifests, fetched into
  other projects. Reach for this whenever the user authors a new generator family, adds a
  main(input_params) entrypoint, uses kgenlib/BaseStore, or asks how a generator decides
  output file names.
---

# Authoring a reusable generator

A generator is a kadet library that turns an inventory block into a set of manifests, for
many projects, not one. This is a level above `kapitan-writing-kadet` (a one-off local
component): a generator reads a well-known parameters key, iterates every entry under it,
and controls its own output-file layout so consumers just fetch it and fill in data.

The `kgenlib` SDK surface (BaseStore, BaseObj/BaseModel, registration decorators, mutations)
is in [references/kgenlib-api.md](references/kgenlib-api.md); read it before building a
generator against `kgenlib`.

## The entrypoint contract

A generator module exposes `main(input_params)` and reads the resolved inventory:

```python
from kapitan.inputs.kadet import BaseModel, inventory, load_from_search_paths

kgenlib = load_from_search_paths("kgenlib")  # shared SDK: BaseStore, decorators, mutations

def main(input_params):
    inv = inventory(lazy=True)
    store = kgenlib.BaseStore()
    for name, config in inv.parameters.generators.mygen.items():
        store.add(build_objects(name, config))
    return store.dump()
```

- `main(input_params)` is the ABI kadet calls. `input_params` carries the compile-entry
  `input_params:` from the inventory.
- `inventory(lazy=True)` is the resolved, merged inventory for the current target. Read
  values, never re-merge classes yourself.
- Read exactly one top-level key (here `generators.mygen`); that key is your contract with
  consumers. See `kapitan-generator-wiring` for which key each generator family owns.

## The output-key convention

The keys you put on the returned object decide the on-disk layout. The convention every
kapicorp-style generator follows is `"{namespace}/{name}-{suffix}"`:

```python
obj.root[f"{namespace}/{name}-deploy"] = deployment   # -> <output>/<namespace>/<name>-deploy.yml
obj.root[f"{namespace}/{name}-svc"] = service          # -> <output>/<namespace>/<name>-svc.yml
```

- The part before `/` becomes the output subfolder; the part after becomes the filename.
- Emit one object per file. Colliding keys overwrite silently, so make the suffix unique per
  kind (`-deploy`, `-svc`, `-cm`, `-secret`, `-rbac`).
- When a component yields a single object, name the file after the component; when it yields
  siblings, name them `{name}-{object}` so they do not collide.

## Kind routing

Generators that emit many kinds route each to a file by matching on `kind`; a kind with no
rule falls through to a catch-all bundle file. If you add a new resource kind, add its
routing rule too, or it lands in the wrong file and surprises GitOps sync.

## Testing

It is Python: import the module, call `main(input_params)` with a stubbed inventory, and
assert on `store` / the returned `.root` keys. Test the output-key layout explicitly, since
that is the part consumers depend on and the part that silently overwrites when wrong.

## After editing

Compile and diff (`kapitan_compile_diff`) a target that uses the generator, and check the
file layout, not just the content. Never hand-edit compiled output.

## Validated against

kapicorp/generators and kgenlib as fetched by Kapitan 0.34 through 0.36. Re-check the
`kgenlib` API against the version your project fetched under `system/lib`.
