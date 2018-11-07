[![Build Status](https://travis-ci.com/stackhpc/ansible-role-beegfs.svg?branch=master)](https://travis-ci.com/stackhpc/ansible-role-beegfs)

# stackhpc.beegfs

This Ansible role can be used to create and destroy a BeegFS cluster. In
summary, BeegFS is a parallel file system that spreads user data across
multiple servers. It is designed to be scalable both in terms of
performance and capacity. Learn more about BeeFS [here](www.beegfs.io).

The role was last tested using Ansible version 2.5.0.

## Example

Say we have an inventory that looks like this (`inventory-beegfs`):

    [leader]
    bgfs1 ansible_host=172.16.1.1 ansible_user=centos

    [follower]
    bgfs2 ansible_host=172.16.1.2 ansible_user=centos

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

Some tests are provided in [molecule folder](molecule). To run them locally you need:

- [Vagrant](https://www.vagrantup.com/)
- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
- [Molecule](https://molecule.readthedocs.io/en/latest/)
- [python-vagrant](https://pypi.org/project/python-vagrant/)

Once you have all the dependencies installed you can run the tests from the root folder of the role:

```
$> molecule lint
$> molecule test
$> molecule test -s vagrant-ubuntu-16.04
$> molecule test -s vagrant-ubuntu-18.04
```

- The default molecule scenario will test the role in a Centos7.5 machine.
- All the tests will deploy all the services in a single machine.
- yaml lint and ansible lint are tested
- idempotence is checked
- Once the execution finishes some [testinfra](https://testinfra.readthedocs.io/en/latest/) are
executed. All the scenarios use the same tests located in [molecule/tests](molecule/tests)
