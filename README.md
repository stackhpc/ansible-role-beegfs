# stackhpc.beegfs

This role was last tested on Ansible version 2.5.2.

The role requires `/etc/hosts` file on each node to contain all nodes
named in the inventory. This means running the following Ansible task:

    ---
    - name: Generate /etc/hosts file
      template:
        src: hosts.j2
        dest: /etc/hosts
      become: yes
    ...

Where `hosts.j2` is a jinja2 template containing:

    # {{ ansible_managed }}
    127.0.0.1   localhost localhost.localdomain localhost4
    localhost4.localdomain4
    ::1         localhost localhost.localdomain localhost6
    localhost6.localdomain6

    {% for item in ansible_play_hosts %}
    {% set short_name = item.split('.') %}
    {{ hostvars[item]['ansible_host'] }}  {{ item }} {{ short_name[0] }}
    {% endfor %}

Additionally, the following groups must be defined in the appliance
inventory:

- `cluster_beegfs_mgmt` (Management server - minimum one host)
- `cluster_beegfs_mds` (Metadata storage server nodes)
- `cluster_beegfs_oss` (Object storage server nodes)
- `cluster_beegfs_client` (Clients of the BeeGFS storage cluster)
- `cluster_beegfs_admon` (NOT IMPLEMENTED)

Example playbook:

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

Example inventory:

    [leader]
    bgfs1.novalocal ansible_host=172.16.1.6 ansible_user=centos

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

To create a cluster:

    # ansible-playbook beegfs.yml -i inventory-beegfs -e beegfs_state=present

To destroy a cluster:

    # ansible-playbook beegfs.yml -i inventory-beegfs -e beegfs_state=absent

