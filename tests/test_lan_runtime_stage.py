import contextlib
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('stage',Path(__file__).parents[1]/'scripts/lan-runtime-stage.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class RuntimeStage(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        (self.root/'operation.lock').touch(mode=0o600)
        self.p={'operation_id':'stage-ace-test1234','host':'ace','candidate':'candidate','baseline':'baseline',
                'launch_not_after':(s.now()+dt.timedelta(minutes=5)).isoformat()}
        self.before={'kaiba_pilot_fleet':{'pilot_enrollments':{'rows':2,'sha256':'a'*64}},
                     'kaiba_pilot_issuer':{'pilot_issuer_ledger':{'rows':2,'sha256':'b'*64}}}
        self.events=[]

    @contextlib.contextmanager
    def backend(self, *, switch_error=None, health_error=None, after=None):
        def switch(profile,*_):
            self.events.append(('switch',profile))
            if switch_error:raise switch_error
        def health(p,c,profile):
            self.events.append(('health',profile))
            if profile=='candidate' and health_error:raise health_error
            return {'profile':profile}
        def run(args,**_):
            self.events.append(('native',args));return b'active\n'
        with patch.object(s,'candidate_scope'),patch.object(s,'stable'),patch.object(s,'switch',side_effect=switch), \
             patch.object(s,'start_dependents',side_effect=lambda _:self.events.append(('start',))), \
             patch.object(s,'health',side_effect=health),patch.object(s,'run',side_effect=run), \
             patch.object(s,'private',side_effect=lambda p:p.read_bytes()), \
             patch.object(s,'database',side_effect=[self.before,after if after is not None else self.before]):
            yield

    def test_success_commits_acceptance_after_health_and_history(self):
        with self.backend():s.apply(self.p,self.root,None)
        self.assertTrue((self.root/'apply.intent.json').exists())
        self.assertTrue((self.root/'accepted.json').exists())
        self.assertEqual(self.events[-1],('health','candidate'))
        with self.backend(),self.assertRaises(FileExistsError):s.apply(self.p,self.root,None)
        self.assertEqual(sum(x==('switch','candidate') for x in self.events),1)

    def test_lost_switch_reply_preserves_intent_without_acceptance(self):
        with self.backend(switch_error=TimeoutError()),self.assertRaises(TimeoutError):s.apply(self.p,self.root,None)
        self.assertTrue((self.root/'apply.intent.json').exists())
        self.assertFalse((self.root/'accepted.json').exists())

    def test_failed_acceptance_keeps_database_observation(self):
        with self.backend(health_error=ValueError('denied')),self.assertRaises(ValueError):s.apply(self.p,self.root,None)
        self.assertTrue((self.root/'database-after.json').exists())
        self.assertFalse((self.root/'accepted.json').exists())

    def test_retained_history_change_is_never_accepted(self):
        after=copy.deepcopy(self.before);after['kaiba_pilot_issuer']['pilot_issuer_ledger']['sha256']='c'*64
        with self.backend(after=after),self.assertRaisesRegex(ValueError,'retained-authority-history-changed'):
            s.apply(self.p,self.root,None)
        self.assertFalse((self.root/'accepted.json').exists())
        self.assertEqual(json.loads((self.root/'database-after.json').read_text()),after)

    def test_only_reviewed_empty_additions_are_allowed(self):
        after=copy.deepcopy(self.before)
        after['kaiba_pilot_fleet']['pilot_renewal_delegations']={'rows':0,'sha256':'d'*64}
        s.compare_database(self.before,after)
        after['kaiba_pilot_fleet']['pilot_renewal_delegations']['rows']=1
        with self.assertRaisesRegex(ValueError,'unexpected-authority-state-added'):s.compare_database(self.before,after)
        after=copy.deepcopy(self.before);after['kaiba_pilot_fleet']['unexpected']={'rows':0,'sha256':'d'*64}
        with self.assertRaises(ValueError):s.compare_database(self.before,after)
        after=copy.deepcopy(self.before);del after['kaiba_pilot_issuer']['pilot_issuer_ledger']
        with self.assertRaises(ValueError):s.compare_database(self.before,after)

    def test_watchdog_stops_worker_before_restoring_partial_switch(self):
        s.save(self.root/'apply.intent.json',{});s.save(self.root/'database-before.json',self.before)
        with self.backend():s.rescue(self.p,self.root,None)
        self.assertEqual(self.events[0],('native',[s.SYSTEMCTL,'stop','kaiba-stage-ace-test1234.service']))
        self.assertLess(self.events.index(('switch','baseline')),self.events.index(('health','baseline')))
        self.assertTrue((self.root/'restored.json').exists())
        self.assertTrue((self.root/'apply.intent.json').exists())

    def test_no_intent_does_not_change_runtime(self):
        with self.backend():s.rescue(self.p,self.root,None)
        self.assertEqual(len(self.events),1)

    def test_watchdog_preserves_verified_accepted_candidate(self):
        s.save(self.root/'accepted.json',{'status':'passed'})
        with self.backend():s.rescue(self.p,self.root,None)
        self.assertNotIn(('switch','baseline'),self.events)
        self.assertIn(('health','candidate'),self.events)

    def test_ambiguous_restore_is_not_retried(self):
        s.save(self.root/'apply.intent.json',{});s.save(self.root/'baseline-restore.intent.json',{})
        with self.backend(),self.assertRaisesRegex(ValueError,'restoration-requires-reconciliation'):
            s.rescue(self.p,self.root,None)
        self.assertNotIn(('switch','baseline'),self.events)

    def test_missing_watchdog_denies_before_intent(self):
        with self.backend(),patch.object(s,'run',return_value=b'inactive\n'),self.assertRaisesRegex(ValueError,'watchdog-required'):
            s.apply(self.p,self.root,None)
        self.assertFalse((self.root/'apply.intent.json').exists())

    def test_expired_launch_denies_before_commands(self):
        self.p['launch_not_after']=(s.now()-dt.timedelta(seconds=1)).isoformat()
        with self.backend(),self.assertRaisesRegex(ValueError,'launch-window-expired'):s.apply(self.p,self.root,None)
        self.assertEqual(self.events,[])

    def test_receipts_never_overwrite_prior_evidence(self):
        p=self.root/'receipt.json';s.save(p,{'a':1})
        with self.assertRaises(FileExistsError):s.save(p,{'a':2})
        self.assertEqual(json.loads(p.read_text()),{'a':1})
        self.assertEqual(p.stat().st_mode&0o777,0o600)

    def test_exec_wrapper_requires_exact_reviewed_agent(self):
        unit = 'ExecStart=/nix/store/a27bsl8l5i4zr5jrcymilg4qjlzcrnyz-kaiba-spire-agent-start\n'
        command = '/nix/store/xprm29ibxp2g3s4j2p1n075gp18n21lv-spire-1.15.2-agent/bin/spire-agent run -expandEnv -config /nix/store/s60n8b4i5rgh6f5d2mj8i1208isf0091-agent.conf'
        with patch.object(Path, 'read_text', side_effect=[unit, '#!/bin/sh\nexec '+command+'\n\n']):
            self.assertEqual(s.expected_command(Path('unit'), 'mako', 'spire-agent'), command.split())
        for script in ['#!/bin/sh\nexec '+command+' --extra\n\n',
                       '#!/bin/sh\nexec '+command+'\nexec /bin/false\n\n']:
            with patch.object(Path, 'read_text', side_effect=[unit, script]), self.assertRaises(ValueError):
                s.expected_command(Path('unit'), 'mako', 'spire-agent')

    def test_unreviewed_wrapper_denied_before_read(self):
        with patch.object(Path, 'read_text', return_value='ExecStart=/unknown/wrapper\n') as read, self.assertRaisesRegex(ValueError, 'unreviewed-agent-launcher'):
            s.expected_command(Path('unit'), 'mako', 'spire-agent')
        self.assertEqual(read.call_count, 1)

if __name__=='__main__':unittest.main()
