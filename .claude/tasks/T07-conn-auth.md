# T07 — Connection authentication

Since 7.3.1 every service refuses to start unless `connAuthFile` is set or
`connDisableAuthentication = true`.

**Files:** `defaults/main.yml`, `tasks/create.yml` (one block near
"Create connInterfacesFile"), `mgmt.yml`, `meta.yml`, `oss.yml`, `client.yml`

```yaml
# Shared secret for BeeGFS connection authentication. Set to "" to disable
# authentication (connDisableAuthentication = true). Use vault.
beegfs_conn_auth_secret: ""
beegfs_conn_auth_file: /etc/beegfs/conn.auth
```

- `create.yml`: `copy: content="{{ beegfs_conn_auth_secret }}" mode=0400
  no_log=true` when the secret is set.
- Each existing "Specify connInterfacesFile" `lineinfile` gets one sibling
  `lineinfile` setting `connAuthFile` or `connDisableAuthentication`
  (meta, storage per-port conf, client per-mgmt conf, mgmtd 7.4 conf).
  8.x mgmtd TOML is handled in T09.
- Molecule: set a fixed test secret (exercise the real path).

**Done when:** all services start with auth enabled and with auth disabled.

## Outcome (2026-11-13)

Done (+44, approved: option A + explanatory comment). Instead of a sibling
`lineinfile` per service file (option B, +58), one loop in `create.yml`
(after the services' config files exist, before they start) sets both
`connAuthFile` and `connDisableAuthentication` in every enabled service's
config file, incl. `beegfs-client.conf` that beegfs-ctl reads. Setting both
keys means switching modes leaves no stale value. Skips mgmtd on 8.x (TOML,
T09).

- Defaults: `beegfs_conn_auth_secret` (empty → disabled),
  `beegfs_conn_auth_file`, internal `beegfs_conn_auth_lines`.
- Secret file written `0400` with `no_log` when set.
- The mgmt/meta/storage/client restart handlers `listen` to
  `Restart BeeGFS services`, notified by both tasks (secret rotation and mode
  switches restart everything enabled on the host).

Verified here: lint, syntax; loop evaluated for all services on 7.4.6 with a
secret (mgmtd, meta, 2 storage ports, 2 client mgmt hosts + beegfs-client.conf)
and on 8.4 without one (mgmtd skipped, `connDisableAuthentication = true`).
Not verified: services actually starting → T13 "Deferred from T07".

Follow-up (2026-11-16): `beegfs-helperd.conf` (7.x clients) was missing from
the loop; helperd refused to start (Molecule vagrant-el8). Added.
