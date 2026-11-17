# Tasks

Work in order; see [`../plan.md`](../plan.md) for context and
[`../support-matrix.md`](../support-matrix.md) for versions. Tick the box in
this index when a task is merged.

Limit: no task adds more than 20 lines of code (outside `.claude/`) without
the user's explicit approval, asked for with a justification — see
[`../plan.md`](../plan.md) → Ground rules.

- [x] [T00](T00-decisions.md) Resolve open questions
- [x] [T01](T01-tooling.md) Tooling: ansible-core, collections, lint config
- [x] [T02](T02-include-tasks.md) `include:` → `include_tasks:`
- [x] [T03](T03-version-and-repos.md) Pin BeeGFS version, versioned EL repos
- [x] [T04](T04-xfs-mount-opts.md) Drop `nobarrier`
- [x] [T05](T05-kmod-spike.md) Spike: beegfs-kmod against 7.4 / 8.x / EL8-10
- [x] [T06](T06-client-kmod.md) Client installs `kmod-beegfs`
- [x] [T07](T07-conn-auth.md) Connection authentication
- [x] [T08](T08-helperd.md) Guard `beegfs-helperd` for 8.x
- [x] [T09](T09-mgmtd-v8.md) 8.x mgmtd, TLS, `beegfs-tools`
- [x] [T10](T10-rdma-packages.md) RDMA package list for EL8+
- [x] [T11](T11-molecule-scenarios.md) Molecule scenarios for EL8/9/10
- [x] [T12](T12-molecule-prepare-kmod.md) Molecule prepare builds kmod RPM
- [ ] [T13](T13-molecule-tests.md) Update testinfra tests (two checks open, see Status)
- [ ] [T14](T14-meta-readme.md) meta/main.yml + README
- [ ] [T15](T15-ci.md) Replace Travis with GitHub Actions
- [x] [T16](T16-remove-debian.md) Remove Debian/Ubuntu support (do after T05)
