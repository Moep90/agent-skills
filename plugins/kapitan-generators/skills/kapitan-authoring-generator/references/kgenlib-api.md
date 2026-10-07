# kgenlib API for generator authors

`kgenlib` is the shared SDK every kapicorp-style generator loads with
`load_from_search_paths("kgenlib")`. It provides the store, the base object classes, the
class-registration decorators, and the mutation pass. Confirm names against the version your
project fetched under `system/lib`; this is the 0.34-0.36 surface.

## BaseStore

The accumulator a generator returns. You add objects to it and dump it.

- `store = kgenlib.BaseStore()` — create it in `main`.
- `store.add(obj)` / `store.add_list([...])` — add one object or many.
- `store.dump(output_filename=None)` — serialize to the mapping kadet writes. With no
  argument, each object routes to its own file by its output key (see below); pass
  `output_filename` to force everything into one file.

## BaseObj vs BaseModel

- `BaseObj` — the classic container. Build `.root` as nested dicts/lists. Use for anything
  whose schema you do not want to model.
- `BaseModel` — pydantic-backed, typed and validated. Prefer it when the block has a schema
  worth enforcing; the generator then rejects a malformed component instead of emitting
  garbage.

## The output-key convention

The key each object carries decides its file. The convention is `"{namespace}/{name}-{suffix}"`:
the part before `/` is the output subfolder, the part after is the filename. Make the suffix
unique per kind (`-deploy`, `-svc`, `-cm`) so objects do not overwrite each other.

## GenerateMultipleObjectsForClass: the naming rule

When one component yields several objects of the same kind, the naming rule is:

- a **single** object of a kind is named after the component (`{name}`);
- **sibling** objects are named `{name}-{object_name}` so they stay distinct.

Follow this so a consumer's compiled tree is predictable and two components never collide on
a filename.

## Class registration and mutations

- Generators register the classes that emit each kind with a decorator (commonly
  `@kgenlib.register_generator(path="...")`), keyed by the inventory path they consume. The
  registry is what lets `store` dispatch a config block to the right emitter.
- After objects are built, a **mutation pass** applies cross-cutting edits (adding common
  labels, annotations, namespaces) to every object. Mutations are declared in the inventory
  (for example under a generator's `mutations` block) and applied by `kgenlib`, so a label
  policy lives in one place instead of in every emitter.

## Testing

Import the module, call `main(input_params)` with a stubbed inventory, and assert on the
`store` contents and the returned output keys. Test the key layout explicitly: it is the
contract consumers depend on and the part that silently overwrites when a suffix is not
unique.
