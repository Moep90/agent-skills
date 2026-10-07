---
name: kapitan-secrets-refs
category: core
description: >-
  Use whenever a Kapitan project involves secrets, refs, or the ?{...} tag syntax: gpg,
  awskms, gcpkms, azkv, vaultkv, base64, plain refs, creating ref placeholders, or Tesoro.
  Reach for this when the user asks to add a secret, store a password, reference a key, or
  when you see ?{gpg:...} style tokens in inventory or templates. Explains ref syntax per
  backend and the rule that ref values are never revealed by an agent.
---

# Kapitan secret refs

Kapitan does not store secret values in the inventory. It stores **refs**: tagged pointers
that compile to references. Revealing a ref needs keys or cloud credentials and is a human
action, not something an agent does.

## The rule

Never reveal a ref value. Do not run `kapitan refs --reveal`, do not print secret values,
do not commit revealed output. If the `kapitan_*` MCP tools are available, use
`kapitan_refs_list` to see which refs exist and whether their ref files are present. There
is deliberately no reveal tool.

## Ref syntax

A ref token looks like `?{backend:path}`:

```yaml
parameters:
  mysql:
    password: ?{gpg:targets/prod/mysql_password}
```

The backend prefix selects how the value is encrypted or stored:

| Backend  | Prefix     | Needs to reveal                     |
|----------|------------|-------------------------------------|
| GPG      | `gpg`      | a GPG private key                   |
| AWS KMS  | `awskms`   | AWS credentials with KMS access     |
| GCP KMS  | `gcpkms`   | GCP credentials with KMS access     |
| Azure KV | `azkv`     | Azure credentials with Key Vault    |
| Vault    | `vaultkv`  | a Vault token and address           |
| base64   | `base64`   | nothing (encoding, not encryption)  |
| plain    | `plain`    | nothing (not secret, avoid)         |

## Creating a ref placeholder

When a project needs a secret that does not exist yet, create a placeholder ref, do not
invent a real secret value. If a compile fails because a ref file is missing under `refs/`,
ask the user to create the secret with their keys. Never fabricate credentials.

## Tesoro

Tesoro is a Kubernetes admission controller that reveals Kapitan refs inside the cluster at
apply time, so secrets stay encrypted in git and are decrypted only in the cluster. When a
project uses Tesoro, refs stay as tokens in the committed manifests by design.

## Validated against

Kapitan 0.34 through 0.36.
