#!/usr/bin/env python3
"""One bounded, reversible test activation of reviewed LAN host closures.

The root-private plan pins both closures and nonsecret acceptance baselines.
This does not install a boot profile, approve a delegation, issue credentials,
restore database files, or retry an interrupted activation. An independent
systemd watchdog invokes rescue after stopping this worker's whole cgroup.
"""
import datetime as dt
import ctypes
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import shlex
import stat
import subprocess
import sys
import time

ROOT = Path('/var/lib/kaiba-pilot-runtime-stage')
DEADLINE = '2026-10-03T02:06:35Z'
COLLECTOR_SHA = '504d9a253cec9d98e88c065d2f8ddd182acee8bce3adaff81d2171997ffe25c4'
SYSTEMCTL = '/run/current-system/sw/bin/systemctl'
EXTRA = ['kaiba-workload-registry.service', 'kaiba-controller.service',
         'kaiba-agent.service', 'kaiba-publisher.service', 'kaiba-lan-primary.service']
ADDED_TABLES = {
    'kaiba_pilot_fleet': {'pilot_renewal_delegations', 'pilot_renewal_delegated_operations'},
    'kaiba_pilot_issuer': {'pilot_issuer_trust_transitions', 'pilot_issuer_delegated_renewal_grants'},
}


def need(value, code):
    if not value:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def now():
    return dt.datetime.now(dt.timezone.utc)


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    staged = path.with_name('.' + path.name + '.pending')
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(staged), -100, os.fsencode(path), 1):
        raise OSError(ctypes.get_errno(), 'receipt-publication-unconfirmed')
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def private(path):
    for parent in path.parents:
        m = parent.lstat()
        need(stat.S_ISDIR(m.st_mode) and m.st_uid == 0 and not m.st_mode & 0o022,
             'unsafe-operation-parent')
    m = path.lstat()
    need(stat.S_ISREG(m.st_mode) and m.st_uid == 0 and m.st_nlink == 1
         and stat.S_IMODE(m.st_mode) == 0o600 and m.st_size <= 1048576,
         'unsafe-operation-file')
    return path.read_bytes()


def run(args, timeout=30):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
                       env={'PATH': '/run/current-system/sw/bin', 'LANG': 'C', 'LC_ALL': 'C',
                            'PGOPTIONS': '-c default_transaction_read_only=on -c statement_timeout=5000'})
    need(p.returncode == 0 and len(p.stdout) + len(p.stderr) <= 1048576, 'command-unconfirmed')
    return p.stdout


def collector():
    path = Path(__file__).with_name('collector.py')
    need(digest(path.read_bytes()) == COLLECTOR_SHA, 'collector-changed')
    spec = importlib.util.spec_from_file_location('collector', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    value.secure_environment()
    return value


def validate(p):
    need(set(p) == {'schema_version', 'operation_id', 'host', 'candidate', 'baseline',
                    'candidate_switch_sha256', 'baseline_switch_sha256', 'pins', 'unit_changes',
                    'stable_files', 'launch_not_after', 'policy_not_after', 'collector_sha256',
                    'backup_complete', 'backup_complete_sha256', 'psql'}, 'plan-fields')
    need(p['schema_version'] == 'kaiba.lan-runtime-stage/v1alpha1' and p['host'] in ('ace', 'mako')
         and re.fullmatch(r'stage-(ace|mako)-[a-z0-9-]{8,48}', p['operation_id'])
         and p['operation_id'].startswith('stage-' + p['host'] + '-'), 'plan-scope')
    for key in ('candidate', 'baseline'):
        need(re.fullmatch(r'/nix/store/[a-z0-9]{32}-nixos-system-' + p['host'] + r'-[A-Za-z0-9._-]+', p[key]),
             'profile-scope')
    need(p['baseline'] != p['candidate'] and p['collector_sha256'] == COLLECTOR_SHA
         and p['pins']['host'] == p['host'] and set(p['pins']['profiles'].values()) == {p['baseline']}
         and p['policy_not_after'] == DEADLINE
         and stamp(p['launch_not_after']) + dt.timedelta(minutes=15) < stamp(DEADLINE), 'plan-boundary')
    allowed = {'ace': {'kaiba-pilot-' + x + '.service' for x in
                       ('admission', 'fleet', 'issuer', 'observation', 'operator', 'import-guard', 'storage-guard')}
                       | {'kaiba-workload-registry.service'},
               'mako': {'spire-agent.service', 'systemd-tmpfiles-resetup.service'}}
    need(set(p['unit_changes']) == allowed[p['host']] and bool(p['stable_files']), 'service-scope')
    for values in p['unit_changes'].values():
        need(set(values) == {'previous', 'candidate'} and all(re.fullmatch('[a-f0-9]{64}', x) for x in values.values()),
             'unit-pins')
    need(all(Path(x).is_absolute() and '..' not in Path(x).parts and re.fullmatch('[a-f0-9]{64}', y)
             for x, y in p['stable_files'].items()), 'stable-file-pins')
    if p['host'] == 'ace':
        need(re.fullmatch(r'/var/lib/kaiba-pilot-continuity/cold-authority-backup-[a-z0-9-]+/complete.json', p['backup_complete'])
             and re.fullmatch('[a-f0-9]{64}', p['backup_complete_sha256'])
             and re.fullmatch(r'/nix/store/[a-z0-9]{32}-postgresql-18[.][A-Za-z0-9._-]+/bin/psql', p['psql']), 'backup-required')
    else:
        need(p['backup_complete'] is None and p['backup_complete_sha256'] is None and p['psql'] is None,
             'member-has-no-authority-database')


def stable(p, c):
    need(socket.gethostname() == p['host'] and c.boot() == p['pins']['boot_id'], 'host-or-boot-changed')
    need(now() < stamp(DEADLINE) and run([SYSTEMCTL.replace('systemctl', 'timedatectl'), 'show',
                                      '-p', 'NTPSynchronized', '--value']).strip() == b'yes', 'clock-or-policy')
    paths = c.paths()
    need(paths['persistent'] == paths['booted'] == p['baseline'], 'persistent-profile-changed')
    need(c.encrypted() == p['pins']['storage'] and c.device_bytes() == p['pins']['device']
         and c.admission(p['host']) == p['pins']['admission'], 'retained-state-changed')
    need(all(digest(Path(x).read_bytes()) == y for x, y in p['stable_files'].items()), 'policy-files-changed')
    need(len(Path('/proc/swaps').read_text().splitlines()) == 1, 'swap-active')


def candidate_scope(p):
    old, new = Path(p['baseline']), Path(p['candidate'])
    for part in ('kernel', 'initrd', 'dtbs', 'firmware', 'kernel-modules'):
        need((old / part).resolve() == (new / part).resolve(), 'boot-components-changed')
    need((old / 'etc/fstab').read_bytes() == (new / 'etc/fstab').read_bytes(), 'mounts-changed')
    def units(root):
        return {f.name: digest(f.read_bytes()) for f in (root / 'etc/systemd/system').iterdir() if f.is_file()}
    a, b = units(old), units(new)
    need(set(a) == set(b), 'unit-set-changed')
    changes = {k: {'previous': a[k], 'candidate': b[k]} for k in a if a[k] != b[k]}
    need(changes == p['unit_changes'], 'unreviewed-unit-changes')
    def enabled(root):
        base = root / 'etc/systemd/system'
        return {str(f.relative_to(base)): str(f.resolve()) for d in base.iterdir()
                if d.is_dir() and d.name.endswith(('.wants', '.requires')) for f in d.iterdir()}
    # Targets refer to the profile's own unit files, whose allowed differences
    # are checked above. Preserve membership of every wants/requires directory.
    need(set(enabled(old)) == set(enabled(new)), 'enabled-units-changed')
    for name, root in (('baseline', old), ('candidate', new)):
        need(digest((root / 'bin/switch-to-configuration').read_bytes()) == p[name + '_switch_sha256'],
             'switch-command-changed')


def database(p):
    """Only aggregate hashes/counts leave PostgreSQL; rows and credentials stay there."""
    if p['host'] != 'ace':
        return {}
    def query(db, sql):
        return run(['/run/current-system/sw/bin/runuser', '-u', 'kaiba-pilot-pg', '--', p['psql'],
                    '-X', '-w', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-h', '/run/kaiba-pilot-pg',
                    '-p', '18445', '-U', 'kaiba-pilot-pg', '-d', db, '-c', sql]).decode().strip()
    result = {}
    for db in ADDED_TABLES:
        names = query(db, "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'pilot\\_%' ESCAPE '\\' ORDER BY tablename").splitlines()
        need(names and all(re.fullmatch('[a-z][a-z0-9_]{0,62}', n) for n in names), 'table-inventory')
        result[db] = {}
        for name in names:
            raw = query(db, 'SELECT count(*)::text || \':\' || encode(sha256(convert_to(coalesce(string_agg(row_to_json(t)::text, E\'\\n\' ORDER BY row_to_json(t)::text COLLATE "C"),\'\'),\'UTF8\')),\'hex\') FROM public."' + name + '" t')
            count, sha = raw.split(':')
            need(count.isdigit() and re.fullmatch('[a-f0-9]{64}', sha), 'table-observation')
            result[db][name] = {'rows': int(count), 'sha256': sha}
    return result


def compare_database(before, after):
    need(set(before) == set(after), 'authority-databases-changed')
    for db, tables in before.items():
        need(all(after[db].get(k) == v for k, v in tables.items()), 'retained-authority-history-changed')
        added = set(after[db]) - set(tables)
        need(added <= ADDED_TABLES[db] and all(after[db][k]['rows'] == 0 for k in added),
             'unexpected-authority-state-added')


def expected_command(unit, host, name):
    starts = [line.split('=', 1)[1] for line in unit.read_text().splitlines()
              if line.startswith('ExecStart=')]
    need(len(starts) == 1, 'ambiguous-service-command')
    args = shlex.split(starts[0])
    if host == 'mako' and name == 'spire-agent':
        # Both reviewed profiles use this unchanged, immutable launcher. It
        # consumes only the blank join-token fallback and execs the agent.
        need(args == ['/nix/store/a27bsl8l5i4zr5jrcymilg4qjlzcrnyz-kaiba-spire-agent-start'],
             'unreviewed-agent-launcher')
        lines = Path(args[0]).read_text().splitlines()
        commands = [line[5:] for line in lines if line.startswith('exec ')]
        need(len(commands) == 1 and lines[-2] == 'exec ' + commands[0], 'ambiguous-agent-launcher')
        args = shlex.split(commands[0])
        need(args == ['/nix/store/xprm29ibxp2g3s4j2p1n075gp18n21lv-spire-1.15.2-agent/bin/spire-agent',
                      'run', '-expandEnv', '-config',
                      '/nix/store/s60n8b4i5rgh6f5d2mj8i1208isf0091-agent.conf'], 'unreviewed-agent-command')
    return args


def health(p, c, profile):
    stable(p, c)
    need(c.paths()['current'] == profile, 'runtime-profile-unconfirmed')
    services = {k: c.service(k) for k in p['pins']['services']}
    for name, previous in p['pins']['services'].items():
        expected = Path(profile) / 'etc/systemd/system' / (name + '.service')
        need(services[name]['unit_sha256'] == digest(expected.read_bytes()), 'loaded-unit-unconfirmed')
        # Guard replacement deliberately stops its dependent pilot consumers.
        affected = name.startswith('kaiba-') if p['host'] == 'ace' else name == 'spire-agent'
        if not affected:
            need(services[name] == previous, 'unrelated-service-changed')
        elif name + '.service' in p['unit_changes']:
            args = expected_command(expected, p['host'], name)
            process = Path('/proc') / services[name]['properties']['MainPID']
            actual = (process / 'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            need(Path(actual[0]).resolve() == Path(args[0]).resolve() and actual[1:] == args[1:],
                 'running-command-unconfirmed')
    pins = dict(p['pins'], services=services, profiles=c.paths())
    c.base_check(pins)
    identity, dns = c.self_check(pins), c.dns(pins)
    probe = c.probe(pins)
    until = time.monotonic() + 10
    while probe is None and time.monotonic() < until:
        time.sleep(.25)
        probe = c.probe(pins)
    need(probe is not None and c.timestamp(probe['not_after']) > time.time(), 'workload-unavailable')
    updater = c.updater() if p['host'] == 'ace' else None
    need(updater is None or updater['active'], 'updater-unavailable')
    return {'checked_at': now().isoformat(), 'profile': profile, 'services': len(services),
            'retained_membership': identity, 'dns': dns, 'probe': probe,
            'updater': updater, 'full_qualification': False}


def start_dependents(p):
    if p['host'] == 'ace':
        run([SYSTEMCTL, 'start', 'kaiba-pilot-control-plane.target', *EXTRA], timeout=65)
    else:
        run([SYSTEMCTL, 'start', 'spire-agent.service', 'kaiba-lan-secondary.service'], timeout=100)
    # Obtain a new observation through the existing attested unit after startup.
    # Its ordinary timer and all updater intervals remain unchanged. This stage
    # precedes the unattended observation campaign.
    probe = 'kaiba-identity-pilot-probe' if p['host'] == 'ace' else 'kaiba-member-identity-probe'
    run([SYSTEMCTL, 'start', probe + '.service'], timeout=45)


def switch(profile, directory, label):
    save(directory / (label + '.intent.json'), {'profile': profile, 'action': 'test', 'at': now().isoformat()})
    fd = os.open(directory / (label + '.log'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as log:
        result = subprocess.run([profile + '/bin/switch-to-configuration', 'test'],
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=120,
                                env={'PATH': '/run/current-system/sw/bin', 'LANG': 'C', 'LC_ALL': 'C'})
        log.flush(); os.fsync(log.fileno())
    save(directory / (label + '.result.json'), {'exit_code': result.returncode})
    need(result.returncode == 0, 'runtime-switch-unconfirmed')


def apply(p, directory, c):
    need(now() < stamp(p['launch_not_after']), 'launch-window-expired')
    candidate_scope(p)
    timer = 'kaiba-' + p['operation_id'] + '-watchdog.timer'
    need(run([SYSTEMCTL, 'show', timer, '-p', 'ActiveState', '--value']).strip() == b'active',
         'restoration-watchdog-required')
    health(p, c, p['baseline'])
    before = database(p)
    save(directory / 'database-before.json', before)
    # One durable activation intent, even if the native command loses its reply.
    save(directory / 'apply.intent.json', {'at': now().isoformat(), 'candidate': p['candidate']})
    switch(p['candidate'], directory, 'candidate-switch')
    start_dependents(p)
    after = database(p)
    save(directory / 'database-after.json', after)
    compare_database(before, after)
    accepted = health(p, c, p['candidate'])
    save(directory / 'accepted.json', {'schema_version': 'kaiba.lan-runtime-stage-result/v1alpha1',
         'operation_id': p['operation_id'], 'status': 'passed', 'acceptance': accepted,
         'history_unchanged': True, 'persistent_profile_changed': False, 'boot_installation_requested': False,
         'delegation_activated': False, 'full_qualification': False})


def rescue(p, directory, c):
    # Kill the whole activation worker before examining a possibly partial switch.
    run([SYSTEMCTL, 'stop', 'kaiba-' + p['operation_id'] + '.service'], timeout=20)
    fd = os.open(directory / 'operation.lock', os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (directory / 'accepted.json').exists():
            value = json.loads(private(directory / 'accepted.json'))
            need(value['status'] == 'passed', 'acceptance-incomplete')
            health(p, c, p['candidate'])
            return
        if not (directory / 'apply.intent.json').exists():
            return
        stable(p, c)
        candidate_scope(p)
        # The previous configuration is reapplied even when a partial switch
        # never updated /run/current-system. Database state is never restored.
        if (directory / 'baseline-restore.intent.json').exists():
            need((directory / 'baseline-restore.result.json').exists()
                 and json.loads(private(directory / 'baseline-restore.result.json'))['exit_code'] == 0,
                 'restoration-requires-reconciliation')
        else:
            switch(p['baseline'], directory, 'baseline-restore')
        start_dependents(p)
        acceptance = health(p, c, p['baseline'])
        compare_database(json.loads(private(directory / 'database-before.json')), database(p))
        if not (directory / 'restored.json').exists():
            save(directory / 'restored.json', {'status': 'restored', 'acceptance': acceptance,
                 'failed_attempt_preserved': True, 'database_files_restored': False})
    finally:
        os.close(fd)


def main():
    need(len(sys.argv) == 4 and sys.argv[1] in ('apply', 'rescue', 'check') and os.geteuid() == 0
         and str(Path(__file__).resolve()).startswith('/nix/store/'), 'immutable-root-command-required')
    path = Path(sys.argv[2]); raw = private(path)
    need(digest(raw) == sys.argv[3], 'plan-changed')
    p = json.loads(raw); validate(p)
    need(path == ROOT / p['operation_id'] / 'plan.json', 'operation-location')
    c = collector(); c.secure_environment()
    if p['host'] == 'ace':
        raw = private(Path(p['backup_complete']))
        need(digest(raw) == p['backup_complete_sha256'], 'backup-receipt-changed')
        backup = json.loads(raw)
        need(backup['original_services_restored'] and backup['backup']['verified_decryption']
             and backup['backup']['exact_file_bytes_and_metadata'], 'unverified-backup')
        need(dt.timedelta(0) <= now() - stamp(backup['backup']['checked_at']) < dt.timedelta(hours=2),
             'fresh-backup-required')
    if sys.argv[1] == 'rescue':
        rescue(p, path.parent, c)
    elif sys.argv[1] == 'check':
        candidate_scope(p); health(p, c, p['baseline']); database(p)
    else:
        fd = os.open(path.parent / 'operation.lock', os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            need(not (path.parent / 'apply.intent.json').exists(), 'activation-already-attempted')
            apply(p, path.parent, c)
        finally:
            os.close(fd)
    print(json.dumps({'operation_id': p['operation_id'], 'action': sys.argv[1], 'status': 'complete'}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z-]+', str(error)) else type(error).__name__
        print(json.dumps({'status': 'unconfirmed', 'code': code, 'rerun_safe': False,
                          'instruction': 'Preserve the attempt; inspect its independent restoration watchdog.'}))
        sys.exit(1)
