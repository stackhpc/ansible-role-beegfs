# T13 — Update testinfra tests

**Files:** `molecule/tests/test_default.py`

- `test_beegfs_helperd_service`: skip when `beegfs_version` (read from
  `host.ansible.get_variables()`) is ≥ 8.
- add `test_beegfs_storage_service` (`beegfs-storage@8003`).
- add `test_kmod_installed`: `host.package('kmod-beegfs').is_installed`,
  and `beegfs` in `/proc/modules`.
- add `test_no_compiler`: `gcc` not installed on the client.
- add `test_mount_writable`: write/read a file under `/mnt/beegfs`.
- 8.x only: `beegfs health check` exit code 0 on the mgmt host (with
  `BEEGFS_MGMTD_ADDR` set).
- keep flake8-clean.

**Done when:** tests pass on all scenarios.

## Deferred from T06 (2026-11-03)

Add to the checks above:

- `modinfo -n beegfs` is under `/lib/modules/<kernel>/extra/beegfs/` or
  `weak-updates/beegfs/`, never `beegfs_autobuild`.
- `/etc/beegfs/beegfs-client-autobuild.conf` has `buildEnabled=false`, and
  neither `gcc` nor `kernel-devel` is installed (T12 removes them after the
  build).
- `beegfs-client.service` is `Type=oneshot` (`systemctl show -p Type`) and
  active; the override's `Restart=on-failure` is applied.
- The client survives `systemctl restart beegfs-client` (module unloads and
  reloads, mount comes back).

## Deferred from T07 (2026-11-13)

- With `beegfs_conn_auth_secret: molecule-test` (T11): `/etc/beegfs/conn.auth`
  exists, mode `0400`, root-owned; every service is active and the client
  mount is writable (proves auth works end to end).
- Auth disabled: one scenario (`vagrant-el8`) converges again with
  `beegfs_conn_auth_secret: ""` as a side effect, then the same service and
  mount checks pass and the configs show `connDisableAuthentication = true`.

## Deferred from T09 (2026-11-13)

8.x only:
- `beegfs-mgmtd` active; `/var/lib/beegfs/mgmtd.sqlite` exists;
  `beegfs-mgmtd.toml` has the four role-set keys uncommented.
- `/etc/beegfs/key.pem` is `0600` and `cert.pem` `0644` on the mgmt host;
  each client's `cert.pem` matches the mgmt host's.
- `BEEGFS_MGMTD_ADDR=<mgmt>:8010 beegfs health check` exits 0 on a client
  (proves TLS + auth through the CLI), and `beegfs node list` shows meta,
  storage and client nodes.
- No `beegfs-mgmtd.conf` edits and no `beegfs_mgmt_path` directory on 8.x.
- `beegfs_tls_disable: true` variant (side effect in `vagrant-el10`): no
  cert generated, `tls-disable = true`, health check passes with
  `--tls-disable`.

## Phase 1 (2026-11-13) — committed, waiting for the first CI run

Approved plan: phase 1 = `default` (EL9, 8.4) green; phase 2 = el8/el10 +
multi-node `vagrant-all`; phase 3 = side-effect variants. Runs on GitHub
Actions with KVM (`.github/workflows/molecule.yml`), failures surface as
annotations. Shared `molecule/shared/{prepare,converge,build-kmod}.yml`
and `molecule/INSTALL.rst` replace the per-scenario copies; the role is
referenced as `stackhpc.beegfs` (meta namespace + role_name). Prepare
updates the kernel and reboots so `kernel-devel-$(uname -r)` exists; the
kmod RPM is left at `/var/tmp/kmod-beegfs.rpm` for converge.

## Status (2026-11-17)

All six scenarios green. Implemented: every item above except
- not written: "client survives `systemctl restart beegfs-client`" (T06),
  "no `beegfs-mgmtd.conf` edits / no `beegfs_mgmt_path` dir on 8.x" (T09);
- covered differently (agreed): auth-off and TLS-off run from scratch in
  `vagrant-noauth` (8.4), not as a switch in vagrant-el8/el10 — so 7.x with
  auth disabled (incl. helperd) is untested; health check tolerates only
  the missing license.
- 2026-11-17: added `test_client_survives_restart` (client hosts) and
  `test_no_v7_mgmtd_setup_v8` (no beegfs-mgmtd.conf, no default
  `beegfs_mgmt_path` on 8.x mgmt hosts), +16. Close T13 once CI is green.

## Outcome (2026-11-17)

Done. Run 44139388963 (9f528de): all six scenarios green with the two new
checks. Remaining known gap (agreed trade-off): 7.x with auth disabled is
untested.
