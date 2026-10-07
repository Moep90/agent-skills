# components: schema reference

This is the one place the generator schema is written down. Other skills link here rather
than repeat it, so it cannot drift. Field availability depends on the fetched generator
version; confirm against your project's `system/` generators.

## A component

```yaml
parameters:
  components:
    <name>:
      image: <repo:tag>
      type: deployment | statefulset | daemonset   # default deployment
      replicas: <int>
      env:
        <KEY>: <value>
        <KEY_FROM_SECRET>:
          secretKeyRef:
            name: <secret-name>
            key: <key>
        <KEY_FROM_CONFIG>:
          configMapKeyRef:
            name: <configmap-name>
            key: <key>
      ports:
        <port-name>:
          service_port: <int>       # generates a Service port
          container_port: <int>     # defaults to service_port
      config_maps:
        <cm-name>:
          mount: /path/in/container
          data:
            <file>: <content>
      secrets:
        <secret-name>:
          mount: /path/in/container
          data:
            <file>: ?{gpg:path/to/ref}   # a Kapitan ref, never a raw value
      healthcheck:
        liveness:
          type: http
          path: /healthz
          port: <port-name>
      resources:
        requests: { cpu: 100m, memory: 128Mi }
        limits: { cpu: 500m, memory: 256Mi }
```

## Notes

- `service_port` under a named port is what generates the Service; omit it for a
  container-only port.
- Secret data uses Kapitan refs. Do not inline secret values.
- `config_maps` and `secrets` support `mount` (as a volume) or exposure through env via
  `configMapKeyRef` / `secretKeyRef`.
- `type` selects the workload kind; the default is a Deployment.

When a field here does not work, the fetched generator version is likely older or newer.
Check the generator source under `system/` for the exact accepted keys.
