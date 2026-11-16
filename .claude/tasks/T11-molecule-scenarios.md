# T11 — Molecule scenarios for EL8/9/10

**Files:** `molecule/default/*`, `molecule/vagrant-all/*`, new
`molecule/vagrant-el8/` and `molecule/vagrant-el10/` (same file set as
`default`: `INSTALL.rst`, `molecule.yml`, `converge.yml` (was
`playbook.yml`), `prepare.yml`). The Ubuntu scenarios are deleted in T16.

`molecule.yml` changes (molecule ≥ 6):

- remove top-level `lint:` and nested `lint:` blocks (lint runs from CI, T15)
- replace the VirtualBox `provider_raw_config_args` (`createhd`/`storageattach`)
  with the libvirt one below
- `INSTALL.rst`: libvirt + `vagrant-libvirt` + `molecule-plugins[vagrant]`
- `driver: name: vagrant`, `provider: name: libvirt`
- platforms: `box: almalinux/8|9|10`, `memory: 2048`, `cpus: 2`, extra disk:
  ```yaml
  provider_raw_config_args:
    - "storage :file, :size => '20G'"
  ```
  (R12: `provider_options` renders `libvirt.storage = …`, but `storage` is a
  method; raw args render `libvirt.storage :file, …`. Check the generated
  Vagrantfile in `~/.cache/molecule/…` on the first run.)
- `provisioner.playbooks.prepare/converge`; `inventory.group_vars.all`
  carries `beegfs_version` so one converge playbook serves every scenario
- `verifier: name: testinfra`, `directory: ../tests`
- `dependency: name: galaxy`, `options: requirements-file: ../../requirements.yml`

`converge.yml`: same role vars as today, but `dev: /dev/vdb`,
`beegfs_interfaces: ["{{ ansible_default_ipv4.interface }}"]` (EL uses
`eth0`/`ens*` depending on box), `beegfs_conn_auth_secret: molecule-test`,
`beegfs_client_kmod_packages` from prepare (T12). Role name: use
`role: "{{ lookup('env', 'MOLECULE_PROJECT_DIRECTORY') | basename }}"`.

Scenario → version map in `plan.md`.

**Done when:** `molecule test` and `molecule test -s vagrant-el8|vagrant-el10`
pass, including idempotence.

## Deferred from T06 (2026-11-03)

- **Autobuild → kmod migration** in `vagrant-el8` (7.4.6) as a Molecule
  `side_effect` playbook: converge with `beegfs_client_kmod: false`, then
  re-converge with the kmod RPM. Expect: `beegfs-client` replaced by
  `kmod-beegfs` (no conflict error), `…/updates/fs/beegfs_autobuild/beegfs.ko`
  gone, `modinfo -n beegfs` under `extra/` or `weak-updates/`, client mounted,
  second converge idempotent. Then `verify` (T13).

## Deferred from T10 (2026-11-13)

Molecule runs with `beegfs_rdma: false`, so the RDMA list is never
installed by converge. In each scenario's verify (or a side effect), per EL:

- `dnf -y install --setopt=tsflags=test <beegfs_distro_vars.RedHat.rdma_dev_pkgs>`
  succeeds (BeeGFS repo configured; AppStream enabled on EL9/10).
- Converge `tasks/rdma.yml` alone twice with `beegfs_rdma: true` and
  `state: present`: second run reports no changes (idempotence with
  `infiniband-diags`). Loading the IB modules may fail without RDMA
  hardware — check only the package task.

## Phase 1 (2026-11-13) — committed, waiting for the first CI run

Approved plan: phase 1 = `default` (EL9, 8.4) green; phase 2 = el8/el10 +
multi-node `vagrant-all`; phase 3 = side-effect variants. Runs on GitHub
Actions with KVM (`.github/workflows/molecule.yml`), failures surface as
annotations. Shared `molecule/shared/{prepare,converge,build-kmod}.yml`
and `molecule/INSTALL.rst` replace the per-scenario copies; the role is
referenced as `stackhpc.beegfs` (meta namespace + role_name). Prepare
updates the kernel and reboots so `kernel-devel-$(uname -r)` exists; the
kmod RPM is left at `/var/tmp/kmod-beegfs.rpm` for converge.

### Run 1 (43470029513, ee3294c) — converge failed

- ✅ Runner KVM, vagrant-libvirt install, `create`, `prepare` (kernel
  update + reboot + kmod build) all passed.
- ❌ converge: `tasks/oss.yml` read `oss_dev_stat.exists` / `.islnk` /
  `.lnk_source` / `.path` instead of `oss_dev_stat.stat.*` — broken since
  2019 (506ed19) for any OSS with `dev`. Fixed (2 lines).
- CI note: anonymous GitHub API allows 60 req/h; poll runs every ≥4 min.

### Run 2 (43478365055, 0404a4c) — converge failed

- ✅ OSS stat fix works; converge reached `meta: flush_handlers`.
- ❌ `Restart BeeGFS mgmt service` handler: beegfs-mgmtd failed to start.
  Most likely cause (journal not captured): the flush sat before
  client.yml, i.e. before `connInterfacesFile` and `/etc/beegfs/conn.auth`
  are written, while the 8.x TOML already says `auth-disable = false`.
  Fix: flush handlers just before "Start and enable BeeGFS server
  services". Workflow now keeps the VM on failure and annotates
  `systemctl --failed` + the beegfs-* journal before destroying it.

### Run 3 (43485723293, 89eefe8) — converge failed at client start

- ✅ Flush move works: mgmtd, meta, storage restarted without errors.
- ❌ beegfs-client: `mount(2) … Operation canceled`, with
  `sysMgmtdHost=127.0.1.1`. In the 8.4 module source this is the mount
  sanity check (`__App_mountServerCheck`): mgmt init, root stat on meta,
  storage free space — any failing cancels the mount; the reason goes to
  the kernel log, which wasn't captured.
- Suspect: Vagrant maps the hostname to 127.0.1.1 while mgmtd uses
  `interfaces = ["eth0"]`. prepare now maps the hostname to the VM's IP
  like real DNS would (test-environment fix, not role). Diagnostics now
  annotate services/ports/hostname, the beegfs kernel log and the server
  journals separately.
- 8.4 client also warns that SELinux needs `sysSELinuxEnabled = true`
  (client) and `storeClientXAttrs = true` (meta); not a mount blocker per
  the source, but likely needed for correct labels → check after green.

### Run 4 (43488179023, 77a430c) — converge failed, causes found

- ✅ Hostname fix: meta reached mgmtd at the VM IP and registered.
- ❌ beegfs-storage@8003 exited: 8.x renamed `connStoragePortTCP/UDP` to
  `connStoragePort` and refuses both together.
- ❌ client: `connClientPortUDP` renamed to `connClientPort` in 8.x →
  "Configuration error: Initialization of common objects failed" → mount
  sanity check cancels the mount.
- Fix (role, +9): key names depend on `beegfs_major_version`; UDP storage
  task 7.x only. Tested against the shipped 8.4 and 7.4.6 confs (keys set
  in place, idempotent).
- mgmtd logs "no license loaded … Feature verification failed" for some
  requests; registration still works. Watch whether it matters.

### Run 5 (43502765692, bf2d383) — converge ✅, idempotence ❌

- ✅ Converge passes: all services up, client "BeeGFS mount ready".
- ❌ Idempotence: meta and storage setup scripts ran again. Their `creates:`
  marker `originalNodeID` isn't written on 8.x (T09 assumed it was from a
  string in the binary — wrong). With `-f`, re-running re-initialises the
  target; storage then fails ("Storage path list and storage UUID list have
  different sizes"). On a real cluster this risks orphaned data.
- Fix: `creates: <path>/format.conf`, which both 7.4.6 and 8.4 setup
  scripts always write. `mgmt.yml` (7.x only) still uses `originalNodeID` →
  verify in `vagrant-el8` (phase 2).

### Run 6 (43890981591, ef99e71) — converge ✅, idempotence ✅, verify 10/12

- 10 passed, 1 skipped (helperd on 8.x), 1 failed: `beegfs health check`
  exits 1 only for "🛑 License Status -> No valid license found"; TLS,
  reachability, consistency, connections all ✅. Test now requires
  "✅ Management TLS" and no 🛑 other than License Status.
- Phase 1 size so far: test infra +272 (approved ~285), role fixes found
  by the runs +17 (oss stat, flush order, 8.x port keys, setup marker).

### Run 7 (43892832806, 0edc240) — ✅ phase 1 green (2026-11-16)

`molecule test -s default` passes end to end on GitHub Actions (~10 min):
create, prepare (kernel update, reboot, kmod build), converge,
idempotence, verify, destroy. Phase 1 done; phase 2 (el8/el10, multi-node
vagrant-all) and phase 3 (variants) still to estimate and approve.

## Phase 2 (2026-11-16) — committed, waiting for CI

Approved (~165 + reserve; role changes need separate approval). Shared
`.config/molecule/config.yml`; scenarios only list platforms +
`beegfs_version`: `default` (EL9, 8.4), `vagrant-el8` (EL8, 7.4.6,
ansible-core <2.17 in CI only), `vagrant-el10` (EL10, 8.4), `vagrant-all`
(node1 EL9 mgmt+meta, node2 EL10 storage, node3 EL10 client, 8.4).
prepare writes /etc/hosts for all nodes and stops firewalld if present.
Tests are group-aware; new cross-host tests: client cert == mgmt cert,
`beegfs node list` shows management/meta/storage/client.

### Phase 2 run 1 (43910930061, cf9c2d4) — 3/4 green

- ✅ default, vagrant-el10, vagrant-all (multi-node: cross-host auth, TLS
  cert distribution, node list all pass).
- ❌ vagrant-el8: not a role bug. ansible-core <2.17 worked (dnf ran), but
  the latest community.general (12.x) uses `from __future__ import
  annotations` → SyntaxError under EL8's Python 3.6. Checked branch
  sources: stable-11 and older and all ansible.posix branches are 3.6-OK.
  CI now installs `community.general:<12.0.0` for the EL8 job only.

### Phase 2 run 2 (43914731486, b61e0f6) — 3/4 green, EL8 never started

- default, vagrant-el10, vagrant-all ✅ again.
- vagrant-el8 failed installing collections: the unquoted
  `community.general:<12.0.0` was a shell redirect (my bug). Quoted now.
  Failure diagnostics skip the VM checks when no Molecule inventory exists
  (they had run against the CI runner).

### Phase 2 run 3 (43919704596, bcf9315) — 3/4 green; EL8 role bug (approved fix)

- vagrant-el8 (7.4.6): mgmtd (7.x setup), meta, storage start; client mount
  fails: "Communication with user-space helper daemon failed". helperd
  failed to start: its shipped conf has `connAuthFile =` and
  `connDisableAuthentication = false`, and T07's loop didn't include
  `beegfs-helperd.conf`. Fix (role, 2 lines, approved): add it on 7.x
  client hosts. The 7.x mgmtd `originalNodeID` marker was fine.
