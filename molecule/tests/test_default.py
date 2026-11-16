import os

import pytest
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def major(host):
    version = host.ansible.get_variables()['beegfs_version']
    return int(str(version).split('.')[0])


def mgmt_host(host):
    return host.ansible.get_variables()['groups']['cluster_beegfs_mgmt'][0]


@pytest.mark.parametrize('name', [
    'beegfs-mgmtd', 'beegfs-meta', 'beegfs-storage@8003', 'beegfs-client'])
def test_beegfs_services(host, name):
    s = host.service(name)
    assert s.is_running
    assert s.is_enabled


def test_beegfs_helperd_service(host):
    if major(host) >= 8:
        pytest.skip('beegfs-helperd was removed in BeeGFS 8')
    s = host.service('beegfs-helperd')
    assert s.is_running
    assert s.is_enabled


def test_beegfs_mount(host):
    mount1 = host.mount_point("/mnt/beegfs")
    assert mount1.exists
    assert mount1.filesystem == 'beegfs'
    cmd = host.run("sudo sh -c 'echo molecule > /mnt/beegfs/t' && "
                   "sudo cat /mnt/beegfs/t")
    assert cmd.rc == 0 and cmd.stdout.strip() == 'molecule'


def test_kmod(host):
    assert host.package('kmod-beegfs').is_installed
    assert 'beegfs' in host.file('/proc/modules').content_string
    path = host.check_output('modinfo -n beegfs')
    assert '/extra/beegfs/' in path or '/weak-updates/beegfs/' in path
    conf = host.file('/etc/beegfs/beegfs-client-autobuild.conf')
    assert conf.contains('^buildEnabled=false')


def test_no_compiler(host):
    assert not host.package('gcc').is_installed
    assert not host.package('kernel-devel').is_installed


def test_client_unit(host):
    show = host.check_output('systemctl show -p Type -p Restart beegfs-client')
    assert 'Type=oneshot' in show and 'Restart=on-failure' in show


def test_conn_auth_file(host):
    f = host.file('/etc/beegfs/conn.auth')
    assert f.user == 'root' and f.mode == 0o400


def test_mgmtd_v8(host):
    if major(host) < 8:
        pytest.skip('BeeGFS 8 only')
    assert host.file('/var/lib/beegfs/mgmtd.sqlite').exists
    toml = host.file('/etc/beegfs/beegfs-mgmtd.toml')
    for line in ('auth-disable = false', 'tls-disable = false'):
        assert toml.contains('^' + line)
    assert host.file('/etc/beegfs/key.pem').mode == 0o600
    assert host.file('/etc/beegfs/cert.pem').mode == 0o644


def test_health_check_v8(host):
    if major(host) < 8:
        pytest.skip('BeeGFS 8 only')
    cmd = host.run('sudo BEEGFS_MGMTD_ADDR=%s:8010 '
                   '/opt/beegfs/sbin/beegfs health check', mgmt_host(host))
    assert '\u2705 Management TLS' in cmd.stdout, cmd.stdout + cmd.stderr
    # Test VMs have no BeeGFS license; every other check must pass.
    failed = [line for line in cmd.stdout.splitlines()
              if '\U0001f6d1' in line and 'License Status' not in line]
    assert not failed, cmd.stdout + cmd.stderr
