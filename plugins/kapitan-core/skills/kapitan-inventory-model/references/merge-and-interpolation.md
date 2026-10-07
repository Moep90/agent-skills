# Merge and interpolation, in detail

## Merge order

For a target, walk the `classes:` list top to bottom. For each class, recurse into its own
`classes:` first (depth-first), then apply that class's `parameters`. After all classes,
apply the target's own `parameters` last.

Deep-merge means nested maps combine key by key. Scalars and lists at the same key are
replaced by the later value, not concatenated (unless the project uses reclass merge tags).

### Worked example

`inventory/classes/common.yml`:

```yaml
parameters:
  mysql:
    image: mysql:5.7
    port: 3306
```

`inventory/classes/component/mysql.yml`:

```yaml
parameters:
  mysql:
    image: mysql:8.0
```

`inventory/targets/prod.yml`:

```yaml
classes:
  - common
  - component.mysql
parameters:
  mysql:
    image: mysql:8.0-prod
```

Resolved `mysql`:

```yaml
mysql:
  image: mysql:8.0-prod   # target wins last
  port: 3306              # only common set it, so it survives
```

`dev.yml` with no `mysql.image` override resolves `image` to `mysql:8.0`, the value from
`component.mysql`.

## Interpolation happens after merge

```yaml
# common.yml
parameters:
  namespace: ${target_name}
```

```yaml
# prod.yml
parameters:
  target_name: prod
```

`namespace` resolves to `prod`. The reference in `common.yml` does not fail even though
`common.yml` never sets `target_name`, because resolution runs against the merged result.

## Debugging a wrong value

1. `kapitan_inventory_target(target, parameter_path="the.key")` to see the resolved value.
2. `kapitan_search_inventory("the_key", kind="key")` to find every file that sets it.
3. `kapitan_class_hierarchy(target)` to see include order, so you know which set wins.

The winner is the last one applied in merge order, with the target itself last of all.
