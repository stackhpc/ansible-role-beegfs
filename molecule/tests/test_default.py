import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_beegfs_meta_service(host):
    s = host.service('beegfs-meta')
    assert s.is_running
    assert s.is_enabled


def test_beegfs_mgmtd_service(host):
    s = host.service('beegfs-mgmtd')
    assert s.is_running
    assert s.is_enabled


def test_beegfs_helperd_service(host):
    s = host.service('beegfs-helperd')
    assert s.is_running
    assert s.is_enabled


def test_beegfs_client_service(host):
    s = host.service('beegfs-client')
    assert s.is_running
    assert s.is_enabled


def test_beegfs_mount(host):
    mount1 = host.mount_point("/mnt/beegfs")
    assert mount1.exists
    assert mount1.filesystem == 'beegfs'
