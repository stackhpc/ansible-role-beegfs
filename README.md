This role requires `/etc/hosts` file on each node to contain all nodes
named in the inventory.

Additionally, the following groups must be defined in the appliance
inventory:

- `cluster_beegfs_mgmt` (Management server - minimum one host)
- `cluster_beegfs_mds` (Metadata storage server nodes)
- `cluster_beegfs_oss` (Object storage server nodes)
- `cluster_beegfs_client` (Clients of the BeeGFS storage cluster)
- `cluster_beegfs_admon` (NOT IMPLEMENTED)

Example usage:

    ---
    - hosts: cluster
      roles:
        - role: stackhpc.beegfs
          beegfs_enable:
            mgmt: "{{ inventory_hostname in groups['cluster_beegfs_mgmt'] }}"
            admon: no
            meta: "{{ inventory_hostname in groups['cluster_beegfs_mds'] }}"
            oss: "{{ inventory_hostname in groups['cluster_beegfs_oss'] }}"
            client: "{{ inventory_hostname in groups['cluster_beegfs_client'] }}"
          beegfs_rdma: yes
          beegfs_host_mgmt: "{{ groups['cluster_beegfs_mgmt'] | first }}"
          beegfs_path_client: "/mnt/beegfs"
          beegfs_fstype: "xfs"
          beegfs_interfaces:
          - "ib0"
          #beegfs_path_client: "{{ cluster_scratchdir }}"
          #beegfs_dev_meta: "/dev/sdb"
          beegfs_path_meta: "/data/beegfs/beegfs_meta"
          # Enable to define block devices that should be formatted
          beegfs_dev_oss:
          - "sdb"
          - "sdc"
          - "sdd"
          beegfs_state: present
    ...
