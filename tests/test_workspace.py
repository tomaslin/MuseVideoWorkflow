import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from workspace import batch,complete,record_failure,clear_failure

class WorkspaceTests(unittest.TestCase):
    def make_project(self,root,name,archived=False):
        p=root/'projects'/name
        (p/'sequences').mkdir(parents=True);(p/'prompts').mkdir()
        (p/'project.json').write_text(json.dumps({'slug':name,'title':name,'archived':archived}))
        (p/'sequences/seq.json').write_text(json.dumps({'shots':[{'shotId':f's{i:02d}'} for i in range(1,10)]+[{'shotId':'title','kind':'title'}]}))
        for i in range(1,10):(p/f'prompts/s{i:02d}.txt').write_text(f'{name} shot {i}')

    def test_fair_shared_cap_leases_and_verified_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ['a','b','c']:self.make_project(root,name)
            self.make_project(root,'archived',True)
            first=batch(root,True)
            self.assertEqual(len(first['jobs']),6)
            self.assertEqual([j['project'] for j in first['jobs']],['a','b','c','a','b','c'])
            second=batch(root,True)
            keys=lambda b:{(j['project'],j['shotId']) for j in b['jobs']}
            self.assertFalse(keys(first)&keys(second))
            with self.assertRaises(ValueError):complete(root,first['leaseId'])
            # Explicit failures release only those items with a bounded backoff.
            failed=[j['project']+':'+j['shotId'] for j in first['jobs']]
            complete(root,first['leaseId'],failed)
            third=batch(root)
            self.assertFalse(keys(first)&keys(third))
            self.assertTrue(all(j['project']!='archived' and j['shotId']!='title' for j in third['jobs']))

    def test_provider_failure_is_not_retried_until_explicitly_cleared(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.make_project(root,'a')
            record_failure(root,'a','s01','integrity_check_failed')
            self.assertNotIn('s01',[j['shotId'] for j in batch(root)['jobs']])
            (root/'projects/a/prompts/s01.txt').write_text('New approved packet')
            self.assertNotIn('s01',[j['shotId'] for j in batch(root)['jobs']])
            record_failure(root,'a','s01','integrity_check_failed')
            clear_failure(root,'a','s01')
            self.assertIn('s01',[j['shotId'] for j in batch(root)['jobs']])

    def test_unapproved_reference_blocks_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.make_project(root,'a')
            path=root/'projects/a/generation-blockers.json'
            path.write_text(json.dumps({'shots':{'s01':{'type':'unapproved-reference'}}}))
            self.assertNotIn('s01',[j['shotId'] for j in batch(root)['jobs']])
            path.write_text(json.dumps({'shots':{}}))
            self.assertIn('s01',[j['shotId'] for j in batch(root)['jobs']])

    def test_lease_expiry_and_total_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.make_project(root,'a')
            first=batch(root,True,99,ttl=-1)
            self.assertEqual(len(first['jobs']),6)
            second=batch(root,True)
            self.assertEqual(first['jobs'],second['jobs'])
            self.assertNotEqual(first['leaseId'],second['leaseId'])

if __name__=='__main__':unittest.main()
