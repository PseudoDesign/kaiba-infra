#!/usr/bin/env python3
"""Export public Malak pilot configuration for LAN integration; read-only SQL."""
import argparse
import datetime
import json
import os
from pathlib import Path
import stat
import subprocess

CONFIG = Path('/srv/kaiba-pilot/fleet/config.json')
PSQL = '/nix/store/kad8bzk4i8gz87k4ljf2dsbidyfx245g-postgresql-17.10/bin/psql'
ACE_INSTANCE = '857bfe871759fd73c32f565ab5db97412fd049af9941eab4'
READER_FIELDS = ('client_cert', 'client_key', 'tenant_id', 'security_domain_id',
                 'repository', 'commit', 'audience', 'issuer_id', 'approvers',
                 'targets', 'qualification_policy_ref')
QUERY = """BEGIN READ ONLY;
SELECT jsonb_build_object(
 'instance_id', id, 'logical_device_id', data->'logical_device_id',
 'state', data->'state', 'authority_id', data->'binding'->'authority_id',
 'tenant_id', data->'binding'->'tenant_id',
 'security_domain_id', data->'binding'->'security_domain_id',
 'policy_ref', data->'binding'->'policy_ref',
 'credential_not_after', data->'binding'->'credential'->'not_after',
 'binding_contract_version', data->'binding'->'contract_version',
 'full_qualification', data->'binding'->'full_qualification')
FROM pilot_enrollments WHERE id = :'instance';
COMMIT;
"""

def public_config(config):
    reader = config['reader']
    out = {key: reader[key] for key in READER_FIELDS}
    for endpoint in ('observation', 'admission'):
        out[endpoint] = {key: reader[endpoint][key] for key in ('url', 'ca', 'authority_id')}
    return {'inventory_authority_id': config['inventory_authority_id'],
            'issuer_certificate': config['issuer_certificate'], 'reader': out}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError('root is required to read the existing protected configuration')
    if not args.output.is_absolute():
        raise ValueError('absolute output path required')
    metadata = CONFIG.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
        # The installed fleet service may own its read-only config; accept that
        # exact service UID too, without reading private key material.
        import pwd
        fleet_uid = pwd.getpwnam('kaiba-pilot-fleet').pw_uid
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != fleet_uid or metadata.st_mode & 0o022:
            raise ValueError('unexpected configuration ownership or permissions')
    config = json.loads(CONFIG.read_text())
    result = public_config(config)
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'PGHOST': '/run/kaiba-pilot-pg', 'PGPORT': '18445',
           'PGDATABASE': 'kaiba_pilot_fleet', 'PGUSER': 'kaiba-pilot-fleet',
           'PGCONNECT_TIMEOUT': '5', 'PGOPTIONS': '-c default_transaction_read_only=on -c statement_timeout=5000'}
    process = subprocess.run(['/usr/sbin/runuser', '-u', 'kaiba-pilot-fleet', '--', PSQL,
                              '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                              '-v', 'instance=' + ACE_INSTANCE], input=QUERY,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=15, env=env)
    if process.returncode:
        raise ValueError('read-only pilot inventory query failed; no database changes made')
    enrollment = json.loads(process.stdout)
    if enrollment.get('instance_id') != ACE_INSTANCE:
        raise ValueError('expected existing Ace enrollment not found')
    result.update({'schema_version': 'kaiba.pilot-lan-preflight/v1alpha1',
                   'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'ace_enrollment': enrollment, 'read_only': True})
    data = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'wb') as output:
        os.fchmod(output.fileno(), 0o644)
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    print('Public LAN preflight written to ' + str(args.output) + '; no keys or database credentials exported')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # Never print raw JSON, command environment, SQL output or subprocess stderr.
        print('Preflight could not complete: ' + type(error).__name__)
        raise SystemExit(1)
