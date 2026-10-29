import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
from evaluate import evaluate

class PipelineTests(unittest.TestCase):
    def test_plan_score_cannot_ship_missing_media(self):
        report = evaluate(str(ROOT / 'projects/desert-beggars-vampires'))
        if not (ROOT / 'projects/desert-beggars-vampires/final/video.mp4').exists():
            self.assertFalse(report['media_verified'])
            self.assertFalse(report['shipping_ready'])
            self.assertTrue(report['shipping_findings'])

    def test_watcher_ignores_outputs_and_retries_failed_sources(self):
        spec = importlib.util.spec_from_file_location('watch', ROOT / 'watch.py')
        watch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(watch)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / 'projects/demo'
            (project / 'sequences').mkdir(parents=True)
            (root / 'pipeline').mkdir()
            (root / 'schemas').mkdir()
            (project / 'project.json').write_text('{"slug":"demo"}')
            (project / 'script.md').write_text('A first draft')
            with patch.object(watch, 'ROOT', root), patch.object(watch, 'STATE', root / '.watch-state.json'):
                watch.tick(True)
                baseline = watch.tracked()
                (project / 'evaluation.json').write_text('{}')
                (project / 'generation-queue.json').write_text('{}')
                (project / 'prompts').mkdir()
                (project / 'prompts/s01.txt').write_text('generated packet')
                self.assertEqual(watch.tracked(), baseline)
                (project / 'script.md').write_text('Changed source')
                class Result:
                    returncode = 1
                    stdout = 'Validation failed'
                    stderr = ''
                with patch.object(watch.subprocess, 'run', return_value=Result()):
                    self.assertEqual(watch.tick(), 1)
                    self.assertEqual(watch.tick(), 1)
                self.assertEqual(json.loads((root / '.watch-state.json').read_text()), baseline)
                Result.returncode = 0
                with patch.object(watch.subprocess, 'run', return_value=Result()) as run:
                    self.assertEqual(watch.tick(), 0)
                    self.assertEqual(run.call_count, 3)
                self.assertEqual(watch.tick(), 0)

if __name__ == '__main__':
    unittest.main()
