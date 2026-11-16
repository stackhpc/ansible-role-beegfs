import os

import pytest
import testinfra
import testinfra.utils.ansible_runner

INVENTORY = os.environ['MOLECULE_INVENTORY_FILE']
testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    INVENTORY).get_hosts('all')

MGMT, META = 'cluster_beegfs_mgmt', 'cluster_beegfs_mds'
OSS, CLIENT = 'cluster_beegfs_oss', 'cluster_beegfs_client'


def major(host):
    version = host.ansible.get_variables()['beegfs_version']
    return int(str(version).split('.')[0])


def mgmt_host(host):
    return host.ansible.get_variables()['groups'][MGMT][0]


def need(host, group, min_major=None):
    """Skip unless the host is in group (and runs at least min_major)."""
    if group not in host.ansible.get_variables()['group_names']:
        pytest.skip('not in %s' % group)
    if min_major and major(host) < min_major:
        pytest.skip('BeeGFS %s+ only' % min_major)


def beegfs_cli(host, args):
    return host.run('sudo BEEGFS_MGMTD_ADDR=%s:8010 /opt/beegfs/sbin/beegfs '
                    + args, mgmt_host(host))


@pytest.mark.parametrize('group,name', [
    (MGMT, 'beegfs-mgmtd'), (META, 'beegfs-meta'),
    (OSS, 'beegfs-storage@8003'), (CLIENT, 'beegfs-client')])
def test_beegfs_services(host, group, name):
    need(host, group)
    s = host.service(name)
    assert s.is_running
    assert s.is_enabled


def test_beegfs_helperd_service(host):
    need(host, CLIENT)
    if major(host) >= 8:
        pytest.skip('beegfs-helperd was removed in BeeGFS 8')
    s = host.service('beegfs-helperd')
    assert s.is_running
    assert s.is_enabled


def test_beegfs_mount(host):
    need(host, CLIENT)
    mount1 = host.mount_point("/mnt/beegfs")
    assert mount1.exists
    assert mount1.filesystem == 'beegfs'
    cmd = host.run("sudo sh -c 'echo molecule > /mnt/beegfs/t' && "
                   "sudo cat /mnt/beegfs/t")
    assert cmd.rc == 0 and cmd.stdout.strip() == 'molecule'


def test_kmod(host):
    need(host, CLIENT)
    assert host.package('kmod-beegfs').is_installed
    assert 'beegfs' in host.file('/proc/modules').content_string
    path = host.check_output('modinfo -n beegfs')
    assert '/extra/beegfs/' in path or '/weak-updates/beegfs/' in path
    conf = host.file('/etc/beegfs/beegfs-client-autobuild.conf')
    assert conf.contains('^buildEnabled=false')


def test_no_compiler(host):
    need(host, CLIENT)
    assert not host.package('gcc').is_installed
    assert not host.package('kernel-devel').is_installed


def test_client_unit(host):
    need(host, CLIENT)
    show = host.check_output('systemctl show -p Type -p Restart beegfs-client')
    assert 'Type=oneshot' in show and 'Restart=on-failure' in show


def test_conn_auth_file(host):
    f = host.file('/etc/beegfs/conn.auth')
    assert f.user == 'root' and f.mode == 0o400


def test_mgmtd_v8(host):
    need(host, MGMT, min_major=8)
    assert host.file('/var/lib/beegfs/mgmtd.sqlite').exists
    toml = host.file('/etc/beegfs/beegfs-mgmtd.toml')
    for line in ('auth-disable = false', 'tls-disable = false'):
        assert toml.contains('^' + line)
    assert host.file('/etc/beegfs/key.pem').mode == 0o600
    assert host.file('/etc/beegfs/cert.pem').mode == 0o644


def test_client_cert_matches_mgmt(host):
    need(host, CLIENT, min_major=8)
    mgmt = testinfra.get_host('ansible://%s?ansible_inventory=%s'
                              % (mgmt_host(host), INVENTORY))
    cert = '/etc/beegfs/cert.pem'
    assert host.file(cert).mode == 0o644
    assert host.file(cert).sha256sum == mgmt.file(cert).sha256sum


def test_health_check_v8(host):
    need(host, CLIENT, min_major=8)
    cmd = beegfs_cli(host, 'health check')
    assert '✅ Management TLS' in cmd.stdout, cmd.stdout + cmd.stderr
    # Test VMs have no BeeGFS license; every other check must pass.
    failed = [line for line in cmd.stdout.splitlines()
              if '\U0001f6d1' in line and 'License Status' not in line]
    assert not failed, cmd.stdout + cmd.stderr


def test_node_list_v8(host):
    need(host, CLIENT, min_major=8)
    out = beegfs_cli(host, 'node list').stdout
    for node_type in ('management', 'meta', 'storage', 'client'):
        assert node_type in out, out
