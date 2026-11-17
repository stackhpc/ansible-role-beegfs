# T05 — Spike: beegfs-kmod against current BeeGFS / EL

Upstream: https://gitlab.com/ccad/beegfs-kmod (`build-srpm.sh`,
`beegfs-kmod.spec.tmpl`). Last changes target 7.2.4 / EL 8.4.

On one VM each of EL8, EL9, EL10:

```sh
dnf install -y rpm-build rpmdevtools kernel-devel-$(uname -r) \
  kernel-rpm-macros redhat-rpm-config elfutils-libelf-devel gcc make perl git
dnf download beegfs-client           # from the configured beegfs repo
git clone https://gitlab.com/ccad/beegfs-kmod && cd beegfs-kmod
./build-srpm.sh ../beegfs-client-*.rpm
rpmbuild --rebuild --define "kversion $(uname -r | sed 's/\.[^.]*$//')" \
  ~/rpmbuild/SRPMS/kmod-beegfs-*.src.rpm
```

Check, for BeeGFS 7.4.6 and 8.4:

1. Does the spec find the module sources in the 7.4/8.x `beegfs-client` RPM
   layout (`/opt/beegfs/src/client/client_module_*`)? Note the paths.
2. Does it build without RDMA, and with `BEEGFS_OPENTK_IBVERBS`/in-kernel
   RDMA (8.x may need `BEEGFS_NO_RDMA` / `OFED_INCLUDE_PATH` instead)?
3. Since `kmod-beegfs` *Conflicts* with `beegfs-client`, does it ship
   everything the client service needs: systemd unit `beegfs-client.service`,
   `/opt/beegfs/sbin/beegfs-client` (or init script), `beegfs-client.conf`,
   `beegfs-mounts.conf`, `mount.beegfs`/helper scripts? List what's missing.
4. Does `beegfs-client.service` try to autobuild/rebuild on start? If so, how
   to disable (`/etc/beegfs/beegfs-client-autobuild.conf`
   `buildEnabled=false`?).
5. Is the `files/beegfs-client.service.d/override.conf` `Type=forking` still
   correct for the 7.4/8.x unit?
6. Does `weak-modules` exist on EL10? (EL10 kernel tooling changed; if not,
   the `%post` needs a fallback to plain `depmod`.)
7. Epoch/version on the result: does `Provides: beegfs-client` satisfy
   `beegfs-utils`/`beegfs-tools` dependencies?

**Output:** append findings to this file; if the spec needs changes, put
patches under `files/beegfs-kmod/` (or a fork URL) and reference them from T12.

## How it runs

GitHub Actions, `.github/workflows/kmod-spike.yml` → `.github/kmod-spike/spike.sh`,
in `almalinux:{8,9,10}` containers × BeeGFS {7.4.6, 8.4} (EL10 uses 7.4.7).
Builds against the newest `kernel-devel` in the repos (no booted kernel
needed), then inspects the client RPM, the kmod RPM and a `dnf install`.
Findings are emitted as annotations (readable unauthenticated via
`/repos/joaquintorres/ansible-role-beegfs/check-runs/<id>/annotations`) and
the job summary; RPMs + logs are uploaded as artifacts.
Not covered by CI: question 4/5 at runtime (service start, `Type=forking`)
→ verified in Molecule (T11/T12).

## Findings — run 1 (39079553377, commit ee7d561, beegfs-kmod 614232a)

Build kernels: EL8 `4.18.0-553.174.1.el8_10`, EL9 `5.14.0-687.57.1.el9_8`,
EL10 `6.12.0-211.65.1.el10_2`.

| | 7.4.6 / 7.4.7 (EL10) | 8.4 |
|---|---|---|
| Module sources | `/opt/beegfs/src/client/client_module_7` | `/opt/beegfs/src/client/client_module_8` |
| rpmbuild | ✅ compiles on EL8, EL9, EL10 (job then died on a SIGPIPE in spike.sh, fixed) | ❌ spec hard-codes `client_module_7` |
| Service | `Type=oneshot`, `ExecStart=/etc/init.d/beegfs-client start`, After `beegfs-helperd` | `Type=oneshot`, `ExecStart=/opt/beegfs/sbin/beegfs-client start` |
| Autobuild conf | `buildArgs=-j8`, `buildEnabled=true` | same |
| beegfs-client Requires | `gcc`, `make` (→ installing it drags in a toolchain) | |

Answers so far:
1. Paths noted above; spec needs `client_module_*` → patched.
3. **kmod-beegfs ships only `beegfs.ko`, depmod.d conf and
   `beegfs-client.conf`**, while conflicting with `beegfs-client`: no
   service unit, no start script, no `beegfs-mounts.conf`. → patched to ship
   all beegfs-client files except `/opt/beegfs/src`, keep modes, and set
   `buildEnabled=false`.
4. Both majors' start scripts honour `beegfs-client-autobuild.conf`; the
   patch sets `buildEnabled=false` (runtime behaviour → verify in T11).
5. **`files/beegfs-client.service.d/override.conf` sets `Type=forking`, but
   upstream is `Type=oneshot` + `RemainAfterExit=yes` on 7.4 and 8.4.**
   Overriding to forking is likely wrong now → drop `Type=` from the
   override in T06 (keep `Restart=`; note `Restart=on-failure` with oneshot
   needs systemd ≥ 244 — fine on EL8+).
2, 6, 7: pending run 3.

Patch: `files/beegfs-kmod/0001-client-layout-and-runtime.patch`, applied by
spike.sh (and later by T12's build playbook).

## Findings — run 2 (39134160698, commit 3930051, patch v1)

- ✅ **rpmbuild succeeds on all six** (EL8/9 × 7.4.6, EL10 × 7.4.7,
  EL8/9/10 × 8.4) with the patch.
- ✅ 7.x: patched kmod-beegfs contains every non-source beegfs-client file.
- ⚠️ 8.4: `/sbin/mount.beegfs` missing (patch only copied `etc usr opt`) →
  patch v2 also copies `sbin` when present (guarded for `sh -e` on 7.x).
- `dnf install kmod-beegfs beegfs-utils [beegfs-tools]` then ran; the job
  died afterwards (exit 2) on an `ls` of the other major's client script
  under `set -e` — spike bug, fixed. The install itself got past, so
  `Provides: beegfs-client` very likely satisfies beegfs-utils/tools (7) —
  confirm in run 3.
- weak-modules (6) result was dropped: GitHub keeps 10 notices per step.
  spike.sh now writes one consolidated "report" notice on exit.
- Spike also prints `modinfo` vermagic/depends now, to answer (2) RDMA.

## Findings — run 3 (39135588814, commit d19b9d4, patch v2) ✅ all green

- ✅ All six combinations build **and** `dnf install kmod-beegfs beegfs-utils
  [beegfs-tools]` succeeds → (7) `Provides: beegfs-client` satisfies the
  tools' dependencies.
- ✅ No "missing vs beegfs-client" warning on any job → the patched package
  now carries every non-source client file, incl. `/sbin/mount.beegfs` (8.x).
- ✅ `%post` ran without error, so `weak-modules` resolved on EL10 as well
  (it's a `Requires(post)`); which package provides it is in run 4.
- The API truncates annotation messages at 4096 bytes, so the report notice
  lost the install/modinfo sections. spike.sh now emits a short
  "key findings" notice first and the report in <4 KB chunks; the noisy
  RDMA grep was replaced by `modinfo depends`.

## Still open (review 2026-11-03)

The run 3 conclusions for (6) and (7) are not proven yet. Run 4 must show:

- **R4 — (6) weak-modules:** grep `install.log` for `scriptlet failed` /
  `warning: %post` (a failing `%post` doesn't fail `dnf install`, and the
  trailing `depmod -a` hides `weak-modules`' exit code). Record
  `rpm -qf /usr/sbin/weak-modules` and a non-empty `weak-updates/beegfs/`
  listing (or explain why it is empty for the build kernel).
- **R5 — (7) Provides:** record `rpm -q --requires beegfs-utils [beegfs-tools]`.
  If neither requires `beegfs-client`, (7) is moot; say so.
- **R8 — (2) RDMA:** add one build per major with RDMA (`modinfo depends`
  should list `ib_core`/`rdma_cm`). Note which `buildArgs` 7.4/8.x accept
  (`BEEGFS_OPENTK_IBVERBS`, `BEEGFS_NO_RDMA`, `OFED_INCLUDE_PATH`) by reading
  the module's `build/Makefile`.

Patch v3 (`files/beegfs-kmod/0001-client-layout-and-runtime.patch`):

- **R6:** `%config(noreplace) /etc/beegfs` so package upgrades keep the
  role-templated `beegfs-mounts.conf` and autobuild conf. Spike check:
  modify `beegfs-mounts.conf`, `dnf reinstall`/upgrade, file is kept.
- **R7:** `Release: %{beegfs_release}.k<kversion with '-' → '_'>` so builds
  for different kernels have distinct NEVRs. Spike check: `rpm -qp
  --qf '%{RELEASE}'` contains the kernel.

Spike fixes:

- **R9:** `spike.sh` uses `${GITHUB_WORKSPACE:-$PWD}` everywhere (repo root
  when run locally); `kmod-spike.yml` gets `permissions: contents: read`.

**Done when:** run 4 is green on all six jobs, the findings above are
recorded here, and T05 is ticked in the index.

## Findings — run 4 (39138841299, commit 36bb3a1, patch v2) ✅ all green

Recorded 2026-11-03 from the "key findings" annotations.

- ✅ Build + `dnf install kmod-beegfs beegfs-utils [beegfs-tools]` on all six
  (8.4 resolves to 8.4.1). No files missing vs `beegfs-client`.
- **(2) RDMA — answered (R8):** every build has `depends: ib_core,rdma_cm`,
  so 7.4 and 8.4 build in-kernel RDMA by default with no `buildArgs`.
  `BEEGFS_OPENTK_IBVERBS` isn't needed; MOFED still needs
  `build_extra_options` (T12).
- **(6) weak-modules:** `/usr/sbin/weak-modules` is in the `kmod` package on
  EL8 (`kmod-25`), EL9 (`kmod-28`) and EL10 (`kmod-31`); not preinstalled in
  the EL8 container, pulled in by `Requires(post)`. `weak-updates/beegfs/` is
  empty, as expected with only the build kernel installed. `%post` success
  still unproven (R4) → run 5.
- Install pulls in `kernel-core` (+ firmware on EL9/10) through
  `Requires: kernel >= kversion`; 7.x also pulls `beegfs-common` (from
  `beegfs-utils`). `beegfs-client` itself isn't in the pulled-in list,
  so (7) depends on R5 → run 5.
- Entry points: 7.x `/etc/init.d/beegfs-client` + `beegfs-client{,@}.service`;
  8.4 adds `/opt/beegfs/sbin/beegfs-client` and `/sbin/mount.beegfs`.
  `buildEnabled=false` on all.
- Compiler warnings: 0–2 per build (EL9/EL10); not investigated.

## Findings — run 5 (41698009705, commit ff98727, patch v3) — green, but `%post` fails

Changes: kernel tag in `Release` via `--define beegfs_release` (R7, no spec
change needed: the spec only sets it when undefined), `%config(noreplace)
/etc/beegfs` (R6), report scriptlet failures (R4) and what the tools require
(R5), `GITHUB_WORKSPACE` fallback and `permissions: contents: read` (R9).

- ✅ **R7:** release is e.g. `el9.k5.14.0_687.65.1.el9_8` →
  `kmod-beegfs-8.4.1-el9.k5.14.0_687.65.1.el9_8.x86_64`.
- ✅ **R6:** every file under `/etc/beegfs` is flagged `cn` (config, noreplace).
- ✅ **R5 / (7):** neither `beegfs-utils` nor `beegfs-tools` requires
  `beegfs-client` (7.4 or 8.4), so (7) is moot. `Provides: beegfs-client`
  is harmless and stays.
- ❌ **R4 / (6):** `%post(kmod-beegfs) scriptlet failed, exit status 1` on
  **all six** jobs; `dnf` still exits 0. The run 3 conclusion was wrong.
  `%posttrans(kernel-core)` also fails on EL9/EL10 (not EL8).
  Likely cause (unconfirmed, error text not captured): in the container
  `uname -r` is the runner's kernel, so the trailing `depmod -a` (which
  targets the *running* kernel) fails. That is also a real bug on hosts:
  installing a kmod for a newly installed, not-yet-booted kernel updates
  the wrong `modules.dep`. Next: capture the scriptlet's stderr and change
  `%post` to `depmod -a %{kversion}.%{_arch}`.
- Unchanged from run 4: builds, no missing files, `buildEnabled=false`,
  `depends: ib_core,rdma_cm`, `weak-updates/` empty. 8.4 also ships
  `beegfs-client@.service`.
- `actions/upload-artifact@v5` triggers a Node 20 deprecation warning.

## Findings — run 6 (41710528658, commit 592c252, patch v3 + depmod fix) ✅ done

- ✅ **R4 / (6):** with `%post` running `depmod -a %{kversion}.%{_arch}`, no
  `kmod-beegfs` scriptlet fails on any of the six jobs. Run 5's failures
  were the bare `depmod -a` targeting the runner's kernel.
- Remaining: `%posttrans(kernel-core)` fails on EL9/EL10 because dracut can't
  write `/boot` in a container ("running in hostonly mode in a container").
  Container-only, not our package; EL8's kernel-core doesn't run dracut here.
- Everything else as in run 5 (release tag, `cn` flags, install, RDMA deps).

## Outcome (2026-11-03)

Done. Inputs for T12's build playbook:

- beegfs-kmod commit `614232a` + `files/beegfs-kmod/0001-client-layout-and-runtime.patch`
  (client_module_*, ships client runtime with `buildEnabled=false`,
  `%config(noreplace) /etc/beegfs`, `depmod -a <kversion>`).
- `rpmbuild --rebuild --define "kversion <ver-rel>" --define
  "beegfs_release <client release>.k<ver-rel with - → _>"`.
- Build deps: `rpm-build git perl make gcc elfutils-libelf-devel
  kernel-rpm-macros redhat-rpm-config bzip2 cpio kernel-devel-<kver>`;
  `kernel-rpm-macros` needs PowerTools (EL8) / CRB (EL9/10).
- RDMA is built in by default (`depends: ib_core,rdma_cm`); MOFED via
  `build_extra_options`.

Inputs for T06: the client needs no compiler; neither `beegfs-utils` nor
`beegfs-tools` requires `beegfs-client`; drop `Type=forking` from the
override; the IB `buildArgs` task only applies to autobuild.

Note (2026-11-17): `.github/workflows/kmod-spike.yml` and
`.github/kmod-spike/spike.sh` were removed in T15; Molecule's
`molecule/shared/build-kmod.yml` covers the build on real VMs. They remain in
git history (last at 592c252's successors up to T15).
