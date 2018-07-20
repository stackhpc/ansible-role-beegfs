Example usage:

    ---
    # Deploy BeeGFS on an HPC appliance.
    # The following groups must be defined in the appliance inventory:
    # - beegfs_mgmt (Management server - must have one host in this group)
    # - beegfs_admon (zero or one hosts in this group - optional)
    # - beegfs_mds (Metadata storage server nodes)
    # - beegfs_oss (Object storage server nodes)
    # - beegfs_client (Clients of the BeeGFS storage cluster)
    - hosts: cluster
      roles:
        - role: stackhpc.beegfs
          beegfs_enable:
            mgmt: "{{ inventory_hostname in groups['cluster_beegfs_mgmt'] }}"
            admon: False
            meta: "{{ inventory_hostname in groups['cluster_beegfs_mds'] }}"
            oss: "{{ inventory_hostname in groups['cluster_beegfs_oss'] }}"
            client: "{{ inventory_hostname in groups['cluster_beegfs_client'] }}"
          beegfs_rdma: True
          beegfs_host_mgmt: "{{ groups['cluster_beegfs_mgmt'] | first }}"
          beegfs_path_client: "/mnt/beegfs"
          beegfs_fstype: "xfs"
          beegfs_force_format: yes
          beegfs_interfaces:
          - "ib0"
          #beegfs_path_client: "{{ cluster_scratchdir }}"
          #beegfs_dev_meta: "/dev/sdb"
          beegfs_path_meta: "/data/beegfs/beegfs_meta"
          # Enable to define block devices that should be formatted
          beegfs_dev_oss: [ "/dev/md0" ]
          beegfs_path_oss: [ "/data/beegfs/beegfs_data_0" ]
