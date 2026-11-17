[![Molecule](https://github.com/joaquintorres/ansible-role-beegfs/actions/workflows/molecule.yml/badge.svg)](https://github.com/joaquintorres/ansible-role-beegfs/actions/workflows/molecule.yml)

# stackhpc.beegfs

This Ansible role can be used to create and destroy a BeegFS cluster. In
summary, BeegFS is a parallel file system that spreads user data across
multiple servers. It is designed to be scalable both in terms of
performance and capacity. Learn more about BeeFS [here](www.beegfs.io).

The role is tested with Molecule on every push (see [Tests](#tests)) using
current ansible-core, and ansible-core 2.16 for EL8.

## Supported platforms

| BeeGFS | EL8 | EL9 | EL10 |
|--------|-----|-----|------|
| 7.4.x  | tested (7.4.6) | supported | best effort (`beegfs_version: "7.4.7"`, 7.4.6 has no EL10 packages) |
| 8.x (8.1+, default 8.4) | supported | tested | tested |

Only EL 8/9/10 (Rocky, Alma, RHEL) are supported; Debian, Ubuntu and EL7 are
not, and the role stops early on them. Requirements: ansible-core >= 2.15 and
the collections in `requirements.yml`
(`ansible-galaxy collection install -r requirements.yml`). **EL8 hosts need
ansible-core < 2.17 and community.general < 12**: EL8's dnf bindings and
module runtime are Python 3.6.

## Upgrading from earlier versions of this role

The default `beegfs_version` is now `"8.4"`. Existing 7.x clusters must pin
their release (e.g. `beegfs_version: "7.4.6"`) before updating the role. The
role does not upgrade across major versions and fails if the installed
packages are from a different major; follow the upstream upgrade guide.

## Example

Say we have an inventory that looks like this (`inventory-beegfs`):

    [leader]
    bgfs1 ansible_host=172.16.1.1 ansible_user=almalinux

    [follower]
    bgfs2 ansible_host=172.16.1.2 ansible_user=almalinux

    [cluster:children]
    leader
    follower

    [cluster_beegfs_mgmt:children]
    leader

    [cluster_beegfs_mds:children]
    leader

    [cluster_beegfs_oss:children]
    leader
    follower

    [cluster_beegfs_client:children]
    leader
    follower

And a corresponding playbook as this (`beegfs.yml`):

    ---
    - hosts:
      - cluster_beegfs_mgmt
      - cluster_beegfs_mds
      - cluster_beegfs_oss
      - cluster_beegfs_client 
      roles:
      - role: stackhpc.beegfs
        beegfs_version: "8.4"
        beegfs_conn_auth_secret: "{{ vault_beegfs_conn_auth_secret }}"
        beegfs_client_kmod_packages: ["kmod-beegfs"]  # from your site repo
        beegfs_enable:
          admon: false
          mgmt: "{{ inventory_hostname in groups['cluster_beegfs_mgmt'] }}"
          meta: "{{ inventory_hostname in groups['cluster_beegfs_mds'] }}"
          oss: "{{ inventory_hostname in groups['cluster_beegfs_oss'] }}"
          tuning: "{{ inventory_hostname in groups['cluster_beegfs_oss'] }}"
          client: "{{ inventory_hostname in groups['cluster_beegfs_client'] }}"
        beegfs_oss:
        - dev: "/dev/sdb"
          port: 8003
        - dev: "/dev/sdc"
          port: 8103
        - dev: "/dev/sdd"
          port: 8203
        beegfs_mgmt_host: "{{ groups['cluster_beegfs_mgmt'] | first }}"
        beegfs_client:
        - path: "/mnt/beegfs"
          port: 8004
        beegfs_fstype: "xfs"
        beegfs_force_format: false
        beegfs_interfaces: ["ib0"]
        beegfs_rdma: true
        beegfs_state: present
    ...

To create a cluster:

    # ansible-playbook beegfs.yml -i inventory-beegfs -e beegfs_state=present

To destroy a cluster:

    # ansible-playbook beegfs.yml -i inventory-beegfs -e beegfs_state=absent

## Notes

Enabling various BeegFS services is as simple as configuring toggles
under `beegfs_enable` to `true` or `false` where:

- `mgmt`: Management server - minimum one host
- `mds`: Metadata storage server nodes
- `oss`: Object storage server nodes
- `client`: Clients of the BeeGFS storage cluster
- `admon`: NOT IMPLEMENTED

This role is dependent upon each node's hostname resolving to the IP address
used to reach the management host, as configured via `beegfs_host_mgmt`. In
this case, `bgsf1` and `bgfs2` must resolve to `172.16.1.1` and `172.16.1.2`
respectively. This may be done via DNS or `/etc/hosts`.

### Client kernel module

By default (`beegfs_client_kmod: true`) clients install a prebuilt
`kmod-beegfs` RPM (`beegfs_client_kmod_packages`) instead of compiling the
module on every node, so clients need no compiler. Build it with
[beegfs-kmod](https://gitlab.com/ccad/beegfs-kmod) plus the patch in
`files/beegfs-kmod/`, e.g. against a build host running the target kernel:

    ansible-playbook -i <build-host>, molecule/shared/build-kmod.yml -e beegfs_version=8.4

and publish `/var/tmp/kmod-beegfs.rpm` to a repo your clients use. Builds are
per kernel (the release carries the kernel version); `weak-modules` keeps them
working across kABI-compatible updates. Existing autobuild clients are
switched over on the next run. `beegfs_client_kmod: false` keeps the old
autobuild; on 7.x with SELinux enforcing, rebuilds the client service does on
its own (e.g. after a kernel update) stay unloadable until the role runs
again, so prefer kmod-beegfs there.

### Connection authentication

Set `beegfs_conn_auth_secret` (keep it in Ansible Vault); it is written to
`beegfs_conn_auth_file` (`/etc/beegfs/conn.auth`) on every node. An empty
secret disables authentication (`connDisableAuthentication = true`).

### BeeGFS 8

- The management service needs TLS: the role generates a self-signed
  certificate on the mgmt host and copies it to clients for the `beegfs` CLI.
  To use your own, place `/etc/beegfs/cert.pem` and `key.pem` on the mgmt host
  before running the role; `beegfs_tls_disable: true` turns TLS off. A client
  with several mgmt hosts keeps the last one's certificate.
- The admin CLI is `beegfs` (`beegfs-tools`), e.g.
  `BEEGFS_MGMTD_ADDR=<mgmt-host>:8010 /opt/beegfs/sbin/beegfs health check`.
- Without a license, BeeGFS 8 limits the number of clients to 5; place a
  license at `/etc/beegfs/license.pem` on the mgmt host.
- `beegfs_mgmt_path` is unused; mgmtd keeps its database in
  `/var/lib/beegfs/mgmtd.sqlite`.

### Storage devices

It is important to note that when provisioning the cluster, if the block
devices specified already have a file system specified, or the disk is not
empty, it is important to force format the disk. This can be set my setting
`beegfs_force_format` to `true`. THIS WILL DELETE THE CONTENT OF THE DISK(S).
Make sure you have made backups if you care about their content.

Partitions are supported but they must already have been created through
another means. Additionally, you will also need override the variable
`beegfs_oss_tunable` with a list of parent block devices since partitions do
not live under `/sys/block/`. For example, to create partitions using an
Ansible module called `parted` (works on Ansible version 2.5+), you can run the
following playbook:

    ---
    - hosts:
      - cluster_beegfs_oss
      vars:
        partitions:
        - dev: /dev/sdb
          start: 0%
          end: 50%
          number: 1
        - dev: /dev/sdb
          start: 50%
          end: 100%
          number: 2
      tasks:
      - name: Create partitions
        parted:
          label: gpt
          state: present
          part_type: primary
          device: "{{ item.dev }}"
          part_start: "{{ item.start }}"
          part_end: "{{ item.end }}"
          number: "{{ item.number }}"
        with_items: "{{ partitions }}"
        become: true
    ...

## Tests

Molecule scenarios in [molecule](molecule) run on GitHub Actions
([workflow](.github/workflows/molecule.yml)) with Vagrant + libvirt:

| Scenario | Hosts | BeeGFS |
|----------|-------|--------|
| `default` | 1 × AlmaLinux 9 | 8.4 |
| `vagrant-el8` | 1 × AlmaLinux 8 | 7.4.6 |
| `vagrant-el10` | 1 × AlmaLinux 10 | 8.4 |
| `vagrant-all` | mgmt+meta, storage and client on 3 × AlmaLinux 9/10 | 8.4 |
| `vagrant-migrate` | 1 × AlmaLinux 8, autobuild client switched to kmod-beegfs | 7.4.6 |
| `vagrant-noauth` | 1 × AlmaLinux 9, auth and TLS disabled | 8.4 |

Each builds `kmod-beegfs` in prepare, converges, checks idempotence and runs
the shared [testinfra tests](molecule/tests). To run one locally you need KVM,
libvirt and Vagrant with the `vagrant-libvirt` plugin; see
[molecule/INSTALL.rst](molecule/INSTALL.rst):

    $ molecule test -s default
