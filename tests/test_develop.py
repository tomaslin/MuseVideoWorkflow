import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from develop import materialize, validate

class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'projects/the-five-outcasts/production.json').read_text())

    def test_complete_package_exact_timing_and_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'production.json'; source.write_text(json.dumps(self.data))
            project=Path(temp)/'project'
            materialize(source,project)
            for name in ['script.md','lore-bible.md','reference-plan.json','audio-plan.json','budget.json','responsibilities.json','batches.json','final/edl.json','prompts/s13.production.md']:
                self.assertTrue((project/name).exists(),name)
            edl=json.loads((project/'final/edl.json').read_text())
            self.assertEqual(edl['totalSec'],60)
            self.assertEqual(len(edl['entries']),20)
            batches=json.loads((project/'batches.json').read_text())['batches']
            self.assertEqual([len(b['shotIds']) for b in batches],[6,6,6])
            before=(project/'script.md').stat().st_mtime_ns
            materialize(source,project,True)
            self.assertEqual((project/'script.md').stat().st_mtime_ns,before)
            # Missing derived text can be restored without overwriting edits.
            (project/'script.md').write_text('Editor-kept draft')
            (project/'prompts/s01.txt').unlink()
            materialize(source,project,True)
            self.assertTrue((project/'prompts/s01.txt').exists())
            self.assertEqual((project/'script.md').read_text(),'Editor-kept draft')
            # A missing mutable manifest is never silently replaced by an empty one.
            (project/'manifest.json').unlink()
            with self.assertRaises(ValueError): materialize(source,project,True)
            # A story refresh must retain imported take history and version documents.
            definition=json.loads((project/'project.json').read_text())
            definition.update(archived=True,active=False,generationEnabled=False)
            (project/'project.json').write_text(json.dumps(definition))
            (project/'manifest.json').write_text('{"clips":[{"shotId":"s01","sha256":"keep-me","selected":true}]}')
            self.data['sequences'][0]['shots'][0]['generationBrief'] += ' Hold the pennant still.'
            source.write_text(json.dumps(self.data))
            materialize(source,project,True)
            self.assertEqual(json.loads((project/'manifest.json').read_text())['clips'][0]['sha256'],'keep-me')
            retained=json.loads((project/'project.json').read_text())
            self.assertTrue(retained['archived'])
            self.assertFalse(retained['active'])
            self.assertFalse(retained['generationEnabled'])
            queued=json.loads((project/'generation-queue.json').read_text())['pending']
            self.assertEqual(next(job for job in queued if job['shotId']=='s01')['reason'],'stale-prompt')
            self.assertTrue(list((project/'variants').glob('*/script.md')))

    def test_reject_invalid_timing_character_and_path(self):
        for mutate in [lambda d:d['edit']['shots'][0].update(durationSec=9),lambda d:d['sequences'][0]['shots'][0]['characters'].append('Invented tribe'),lambda d:d['departments'].update({'../../escape':'bad'}),lambda d:d['sequences'][0]['shots'][0].update(action='[TBD]')]:
            data=copy.deepcopy(self.data);mutate(data)
            with self.assertRaises(ValueError):validate(data)

if __name__=='__main__':unittest.main()
