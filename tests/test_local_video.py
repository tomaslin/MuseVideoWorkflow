"""Real media integration tests: order, trims, silence, cache, redo, corruption."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/local-video.sh'

class LocalVideoTests(unittest.TestCase):
    def run_cli(self, *args, ok=True):
        result = subprocess.run([str(CLI), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_media_roundtrip_and_failure_gates(self):
        with tempfile.TemporaryDirectory(prefix="muse's footage ") as tmp:
            p = Path(tmp)
            for name in ['sequences', 'prompts', 'incoming']:
                (p / name).mkdir()
            (p / 'project.json').write_text(json.dumps(dict(slug='test', title='Real media test', durationSec=4)))
            (p / 'sequences/seq.json').write_text(json.dumps({'shots': [dict(shotId='s01', durationSec=2), dict(shotId='s02', durationSec=2)]}))
            for shot in ['s01', 's02']:
                (p / f'prompts/{shot}.txt').write_text(f'A real prompt for {shot}')
            def fixture(shot, color, size, audio):
                args = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c={color}:s={size}:r=30:d=3']
                if audio:
                    args += ['-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', '-c:a', 'aac']
                subprocess.run(args + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(p / f'incoming/media-generation-{shot}-0-test.mp4')], check=True)
            fixture('s01', 'red', '320x240', False)
            fixture('s02', 'blue', '240x320', True)
            (p / 'edit.json').write_text(json.dumps(dict(width=320, height=180, fps=24, shots=[dict(shotId='s02', inSec=.5, durationSec=1.5), dict(shotId='s01', inSec=.5, durationSec=1.5)])))
            self.run_cli('import', p, p / 'incoming')
            first = json.loads((p / 'manifest.json').read_text())
            self.run_cli('import', p, p / 'incoming')
            self.assertEqual(len(json.loads((p / 'manifest.json').read_text())['clips']), 2)
            # A fresh checkout lacks ignored raw clips; published, checksum-verified
            # previews must remain usable for status and local assembly.
            self.run_cli('publish-preview', p, '--shot', 's02')
            original_s02 = next(c for c in first['clips'] if c['shotId']=='s02')
            (p / original_s02['file']).unlink()
            self.assertIn('s02: generated', self.run_cli('status', p))
            self.run_cli('assemble', p)
            man = json.loads((p / 'final/final-manifest.json').read_text())
            self.assertEqual(man['shotOrder'], ['s02', 's01'])
            self.assertEqual(man['reviewState'], 'unreviewed')
            self.assertAlmostEqual(man['durationSec'], 3, delta=.12)
            # A short excerpt cannot be mistaken for the requested full delivery.
            definition = json.loads((p / 'project.json').read_text())
            definition['timingMode'] = 'edited'
            (p / 'project.json').write_text(json.dumps(definition))
            verify = subprocess.run(['python3', str(ROOT / 'pipeline/musevideo.py'), 'verify-final', str(p)], capture_output=True, text=True)
            self.assertNotEqual(verify.returncode, 0, verify.stdout)
            del definition['timingMode']
            (p / 'project.json').write_text(json.dumps(definition))
            # Decode frames on both sides of the cut to prove actual picture order.
            for sec, channel in [(.5, 2), (2.0, 0)]:
                rgb = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(sec), '-i', str(p / 'final/video.mp4'), '-vf', 'crop=10:10:150:85,scale=1:1', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
                self.assertGreater(rgb[channel], 150, (sec, list(rgb)))
            # Decode all streams to catch damaged concatenations.
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p / 'final/video.mp4'), '-f', 'null', '-'], check=True)
            self.assertIn('Cached s02', self.run_cli('assemble', p))
            self.run_cli('verify', p)
            (p / 'prompts/s02.txt').write_text('Changed character direction')
            self.assertIn('stale', self.run_cli('assemble', p, ok=False))
            self.run_cli('verify', p, ok=False)
            self.run_cli('import', p, p / 'incoming/media-generation-s02-0-test.mp4', '--shot', 's02')
            self.run_cli('redo', p, '--shot', 's01', '--reason', 'Bent vampire knees at 1.2 seconds')
            self.assertIn('identical file', self.run_cli('import', p, p / 'incoming/media-generation-s01-0-test.mp4', '--shot', 's01', ok=False))
            self.assertIn('redo', self.run_cli('assemble', p, ok=False))
            queue = json.loads((p / 'generation-queue.json').read_text())
            self.assertEqual(queue['nextBatch'][0]['shotId'], 's01')
            self.assertEqual(queue['nextBatch'][0]['redoReason'], 'Bent vampire knees at 1.2 seconds')
            self.assertTrue((p / first['clips'][0]['file']).exists())
            # Duplicate downloads must not silently select an arbitrary take.
            (p / 'incoming/duplicate-s01.mp4').write_bytes((p / 'incoming/media-generation-s01-0-test.mp4').read_bytes())
            self.run_cli('import', p, p / 'incoming', ok=False)

if __name__ == '__main__':
    unittest.main()
