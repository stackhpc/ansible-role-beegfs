# T14 — meta/main.yml and README

**meta/main.yml:** `namespace: stackhpc`, `min_ansible_version: "2.15"`,
platforms `EL: ["8", "9", "10"]` only.

**README:** keep structure; update only:
- "last tested" line → ansible-core version used in T11.
- Example playbook: add `beegfs_version`, `beegfs_conn_auth_secret`,
  `beegfs_client_kmod_packages`; device names.
- New short section "Client kernel module" pointing to beegfs-kmod and
  `molecule/shared/build-kmod.yml`.
- Link `.claude/support-matrix.md` content (copy the "What this role will
  support" table into README).
- Notes: default is now 8.4 — **existing 7.x clusters must set
  `beegfs_version` before upgrading the role**; no major-version upgrades;
  8.x license/5-client limit; self-signed TLS cert and how to supply your own;
  `kmod-beegfs` must be in a site repo; EL 8/9/10 only (Debian/Ubuntu removed).
- Example inventory: `ansible_user=centos` → `rocky`/`almalinux`.
- Tests section: new scenario names, libvirt deps
  (`vagrant-libvirt`, `molecule-plugins[vagrant]`).

## From T09 (2026-11-13)

- TLS: the role generates a self-signed cert on the mgmt host unless
  `/etc/beegfs/cert.pem` + `key.pem` already exist (place your own there
  first); `beegfs_tls_disable: true` turns TLS off. Clients get the cert
  copied for the `beegfs` CLI; with several mgmt hosts per client, the last
  one's cert wins (the CLI reads one default path).
- `beegfs_mgmt_path` is unused on 8.x (DB at `/var/lib/beegfs/mgmtd.sqlite`).
- The `beegfs` CLI needs `BEEGFS_MGMTD_ADDR=<mgmt>:8010` (or
  `--mgmtd-addr`).

## From Molecule phase 2 (2026-11-16)

- EL8 managed hosts need ansible-core < 2.17 (dnf bindings are Python 3.6
  only) **and** community.general < 12 (12 uses Python 3.7+ syntax in
  modules). EL9/EL10 work with current versions. Put in the support table.
