# stackhpc.beegfs

This Ansible role can be used to create and destroy a BeegFS cluster. In
summary, BeegFS is a parallel file system that spreads user data across
multiple servers. It is designed to be scalable both in terms of
performance and capacity. Learn more about BeeFS [here](www.beegfs.io).

The role was last tested using Ansible version 2.5.2.

## Example

Say we have an inventory that looks like this (`inventory-beegfs`):

    [leader]
    bgfs1.novalocal ansible_host=172.16.1.1 ansible_user=centos

    [follower]
    bgfs2.novalocal ansible_host=172.16.1.2 ansible_user=centos

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
    - hosts: cluster
      vars:
        devs:
        - "sdb"
        - "sdc"
        - "sdd"
      roles:
        - role: stackhpc.beegfs
          beegfs_enable:
            mgmt: "{{ inventory_hostname in groups['cluster_beegfs_mgmt'] }}"
            admon: no
            meta: "{{ inventory_hostname in groups['cluster_beegfs_mds'] }}"
            oss: "{{ inventory_hostname in groups['cluster_beegfs_oss'] }}"
            client: "{{ inventory_hostname in groups['cluster_beegfs_client'] }}"
          beegfs_rdma: yes
          beegfs_force_format: no
          beegfs_host_mgmt: "{{ groups['cluster_beegfs_mgmt'] | first }}"
          beegfs_path_client: "/mnt/beegfs"
          beegfs_fstype: "xfs"
          beegfs_interfaces:
          - "ib0"
          #beegfs_path_client: "{{ cluster_scratchdir }}"
          #beegfs_dev_meta: "/dev/sdb"
          beegfs_path_meta: "/data/beegfs/beegfs_meta"
          # Enable to define block devices that should be formatted
          beegfs_dev_oss: "{{ (['/dev/'] * devs|length) | zip(devs) | map('join') | list }}"
          beegfs_path_oss: "{{ (['/data/beegfs/beegfs_oss/'] * devs|length) | zip(devs) | map('join') | list }}"
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
