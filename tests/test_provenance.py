import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from apply_scout.__main__ import (build_request, call_provider, evaluate_live,
                                  instruction_hash, main, provider_command, research)
from apply_scout.schema import SCHEMA

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / 'tests/fixtures/quality'


class ProvenanceTests(unittest.TestCase):
    def test_hash_excludes_documents_date_limit_and_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'profile.md').write_text('# Fictional profile\nprivate marker alpha')
            (root / 'sources.md').write_text('https://example.com')
            before_prompt, before = build_request(root, 1, 'codex')
            (root / 'profile.md').write_text('# Different fictional profile\nprivate marker beta')
            after_prompt, after = build_request(root, 30, 'claude')
            self.assertNotEqual(before_prompt, after_prompt)
            self.assertEqual(before['instruction_hash'], after['instruction_hash'])
            self.assertNotIn('private marker', json.dumps(after))
            self.assertEqual(after['input_files'], ['profile.md', 'sources.md'])
        self.assertNotEqual(instruction_hash('one instruction'), instruction_hash('another instruction'))
        schema = copy.deepcopy(SCHEMA)
        schema['description'] = 'Changed contract'
        with patch('apply_scout.__main__.SCHEMA', schema):
            changed = instruction_hash()
        self.assertNotEqual(changed, instruction_hash())

    @patch('apply_scout.__main__.call_provider')
    def test_mismatched_metadata_is_rejected_before_output(self, provider):
        directory = FIXTURES / 'partial-evidence'
        prompt, metadata = build_request(directory, 1, 'codex')
        payload = json.loads((directory / 'response.json').read_text())
        payload['run'] = metadata
        provider.return_value = payload
        self.assertEqual(research('codex', prompt, metadata=metadata)['run'], metadata)
        for field, value in [('agent', 'invented'), ('instruction_hash', 'sha256:' + 'f' * 64),
                             ('input_files', ['profile.md', 'resume.md'])]:
            bad = copy.deepcopy(payload)
            bad['run'][field] = value
            provider.return_value = bad
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'output'
                with contextlib.redirect_stderr(io.StringIO()):
                    status = main(['run', '--agent', 'codex', '--inputs', str(directory), '--output', str(output)])
                self.assertEqual(status, 1)
                self.assertFalse(output.exists())

    @patch('apply_scout.__main__.call_provider')
    def test_run_records_trusted_metadata(self, provider):
        directory = FIXTURES / 'partial-evidence'
        _, metadata = build_request(directory, 20, 'codex')
        payload = json.loads((directory / 'response.json').read_text())
        payload['run'] = metadata
        provider.return_value = payload
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['run', '--agent', 'codex', '--inputs', str(directory), '--output', tmp]), 0)
            saved = json.loads(Path(tmp, 'research.json').read_text())
            self.assertEqual(saved['run'], metadata)

    def test_offline_result_records_evaluator_and_response_hashes(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            target = Path(tmp) / 'results/before.json'
            self.assertEqual(main(['evaluate', '--result', str(target)]), 0)
            report = json.loads(target.read_text())
            self.assertEqual(report['evaluator_instruction_hash'], instruction_hash())
            self.assertIn('evaluated_at', report)
            self.assertTrue(all('instruction_hash' in case['run'] for case in report['cases']))

    def test_live_provider_command_disables_web_tools(self):
        command = provider_command('codex', '.', Path('schema'), Path('result'), web=False)
        self.assertNotIn('--search', command)
        self.assertIn('web_search="disabled"', command)
        command = provider_command('claude', '.', Path('schema'), Path('result'), web=False)
        self.assertEqual(command[command.index('--tools') + 1], '')
        self.assertNotIn('--allowedTools', command)

    @patch('apply_scout.__main__.call_provider')
    def test_live_repeated_calls_save_responses_without_expected_conditions(self, provider):
        def fake(agent, prompt, timeout, **kwargs):
            posting = json.loads(prompt.splitlines()[-1])
            name = posting['url'].rsplit('/', 1)[-1]
            data = json.loads((FIXTURES / name / 'response.json').read_text())
            _, data['run'] = build_request(FIXTURES / name, 1, agent)
            self.assertNotIn('forbidden_evidence', prompt)
            self.assertNotIn('"assessments"', prompt)
            self.assertIn('Synthetic evaluation override', prompt)
            self.assertFalse(kwargs['web'])
            return data
        provider.side_effect = fake
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'live'
            with contextlib.redirect_stdout(io.StringIO()):
                status = main(['evaluate-live', '--agent', 'codex', '--output', str(output), '--runs', '2'])
            self.assertEqual(status, 0)
            self.assertEqual(provider.call_count, 12)
            report = json.loads((output / 'evaluation.json').read_text())
            self.assertEqual(report['mode'], 'live')
            self.assertTrue(report['complete'])
            self.assertEqual(len(list(output.glob('*.json'))), 13)
            before = (output / 'evaluation.json').read_bytes()
            with self.assertRaises(FileExistsError):
                evaluate_live(FIXTURES, output, 'codex')
            self.assertEqual(before, (output / 'evaluation.json').read_bytes())
            self.assertEqual(provider.call_count, 12)

    @patch('apply_scout.__main__.shutil.which', return_value='/bin/fake')
    @patch('apply_scout.__main__.subprocess.run')
    def test_live_invalid_json_preserves_raw_response_and_failure(self, run, which):
        run.return_value = CompletedProcess([], 0, 'not JSON from fake CLI')
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            output = Path(tmp) / 'live'
            report = evaluate_live(FIXTURES, output, 'claude')
            self.assertFalse(report['passed'])
            self.assertTrue(report['complete'])
            self.assertEqual(len(list(output.glob('*.raw.txt'))), 6)
            self.assertTrue(all(c['failures'][0]['rule'] == 'provider' for c in report['cases']))
            self.assertIn('not JSON', next(output.glob('*.raw.txt')).read_text())

    @patch('apply_scout.__main__.call_provider', side_effect=TimeoutExpired('fake', 1))
    def test_provider_timeouts_are_recorded_and_limits_checked(self, provider):
        with tempfile.TemporaryDirectory() as tmp:
            for runs, timeout in ((0, 1), (11, 1), (1, 0)):
                with self.assertRaises(ValueError):
                    evaluate_live(FIXTURES, Path(tmp) / 'invalid', 'codex', runs, timeout)
            self.assertEqual(provider.call_count, 0)
            report = evaluate_live(FIXTURES, Path(tmp) / 'timeouts', 'codex', timeout=1)
            self.assertFalse(report['passed'])
            self.assertEqual(len(report['cases']), 6)
