# stackhpc.beegfs

This Ansible role can be used to create and destroy a BeegFS cluster. In
summary, BeegFS is a parallel file system that spreads user data across
multiple servers. It is designed to be scalable both in terms of
performance and capacity. Learn more about BeeFS [here](www.beegfs.io).

The role was last tested using Ansible version 2.5.2.

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
          mgmt: "{{ inventory_hostname in groups['cluster_beegfs_mgmt'] }}"
          admon: no
          meta: "{{ inventory_hostname in groups['cluster_beegfs_mds'] }}"
          oss: "{{ inventory_hostname in groups['cluster_beegfs_oss'] }}"
          client: "{{ inventory_hostname in groups['cluster_beegfs_client'] }}"
        beegfs_oss:
        - dev: "sdb"
          port: 8003
        - dev: "sdc"
          port: 8103
        - dev: "sdd"
          port: 8203
        beegfs_mgmt_host: "{{ groups['cluster_beegfs_mgmt'] | first }}"
        beegfs_client:
          path: "/mnt/beegfs"
          port: 8004
        beegfs_fstype: "xfs"
        beegfs_force_format: no
        beegfs_interfaces: ["ib0"]
        beegfs_rdma: yes
        beegfs_state: present
    ...

To create a cluster:

    # ansible-playbook beegfs.yml -i inventory-beegfs -e beegfs_state=present

To destroy a cluster:

    # ansible-playbook beegfs.yml -i inventory-beegfs -e beegfs_state=absent

## Notes

Enabling various BeegFS services is as simple as configuring toggles
under `beegfs_enable` to `yes` or `no` where:

- `mgmt`: Management server - minimum one host
- `mds`: Metadata storage server nodes
- `oss`: Object storage server nodes
- `client`: Clients of the BeeGFS storage cluster
- `admon`: NOT IMPLEMENTED

Additionally, this role is dependent upon each node's hostname
resolving to the IP address used to reach the management host, as
configured via `beegfs_host_mgmt`. In this case, `bgsf1.novalocal` and
`bgfs2.novalocal` must resolve to `172.16.1.1` and `172.16.1.2`
respectively. This may be done via DNS or `/etc/hosts`.

It is also important to note that when provisioning the cluster, if the
block devices specified already have a file system specified, or the
disk is not empty, it is important to force format the disk. This can be
set my setting `beegfs_force_format` to `yes`. THIS WILL DELETE THE
CONTENT OF THE DISK(S). Make sure you have made backups if you care
about their content.
