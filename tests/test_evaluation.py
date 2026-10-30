import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from apply_scout.__main__ import main
from apply_scout.evaluation import evaluate, evaluate_case, fixture_directories

FIXTURES = Path(__file__).parent / 'fixtures/quality'


class EvaluationTests(unittest.TestCase):
    def payload(self, name):
        return json.loads((FIXTURES / name / 'response.json').read_text())

    def rules(self, name, data):
        result = evaluate_case(FIXTURES / name, data)
        self.assertEqual(result['fixture'], name)
        self.assertFalse(result['passed'], result)
        return {failure['rule'] for failure in result['failures']}

    @patch('subprocess.run', side_effect=AssertionError('offline evaluation called a provider'))
    def test_all_fictional_cases_pass_offline(self, run):
        report = evaluate(FIXTURES)
        self.assertEqual(len(report['cases']), 6)
        self.assertTrue(report['passed'], report)
        for directory in fixture_directories(FIXTURES):
            with self.subTest(fixture=directory.name):
                data = self.payload(directory.name)
                self.assertIn('Fictional', (directory / 'profile.md').read_text())
                urls = [j['url'] for j in data['jobs']] + [s['url'] for s in data['sources']]
                self.assertTrue(all(urlsplit(url).hostname == 'example.com' for url in urls))

    def test_missing_requirement_and_incorrect_importance(self):
        data = self.payload('preferred-gap')
        data['jobs'][0]['requirements'].pop()
        self.assertIn('requirement_coverage', self.rules('preferred-gap', data))
        data = self.payload('preferred-gap')
        data['jobs'][0]['requirements'][1]['importance'] = 'responsibility'
        self.assertIn('importance', self.rules('preferred-gap', data))

    def test_missing_information_stays_unknown(self):
        data = self.payload('missing-experience')
        req = data['jobs'][0]['requirements'][0]
        req.update(assessment='unmet', profile_evidence=[{
            'file':'profile.md', 'section':'Python API design', 'detail':'I designed Python APIs.'}])
        self.assertIn('assessment', self.rules('missing-experience', data))

    def test_unsupported_numbers_technologies_and_responsibilities(self):
        for claim in ('Kubernetes', '99.9%', 'Led a team of 12'):
            data = self.payload('unsupported-claims')
            data['jobs'][0]['requirements'][0]['profile_evidence'][0]['detail'] += ' ' + claim
            with self.subTest(claim=claim):
                rules = self.rules('unsupported-claims', data)
                self.assertIn('input_evidence', rules)
                self.assertIn('forbidden_evidence', rules)

    def test_contract_failure_reports_fixture_and_path(self):
        data = self.payload('required-gap')
        data['jobs'][0]['match'] = '높음'
        result = evaluate_case(FIXTURES / 'required-gap', data)
        self.assertFalse(result['passed'])
        self.assertEqual(result['fixture'], 'required-gap')
        self.assertIn('$.jobs[0].match', result['failures'][0]['message'])
        data = self.payload('partial-evidence')
        data['jobs'][0]['requirements'][0]['profile_evidence'] = []
        self.assertIn('contract', self.rules('partial-evidence', data))

    def test_wrong_evidence_section_is_rejected(self):
        data = self.payload('partial-evidence')
        data['jobs'][0]['requirements'][0]['profile_evidence'][0]['section'] = 'Imaginary section'
        self.assertIn('input_evidence', self.rules('partial-evidence', data))

    def test_repeated_responses_and_missing_or_invalid_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for directory in fixture_directories(FIXTURES):
                data = self.payload(directory.name)
                for index in (1, 2):
                    Path(tmp, f'{directory.name}.{index}.json').write_text(json.dumps(data))
            report = evaluate(FIXTURES, tmp)
            self.assertTrue(report['passed'])
            self.assertTrue(all(item['runs'] == 2 and item['valid_structures'] == 1 for item in report['variation']))
            # A different valid evidence count is observed, not a golden-text failure.
            data = self.payload('partial-evidence')
            evidence = data['jobs'][0]['requirements'][0]['profile_evidence']
            evidence.append(dict(evidence[0]))
            Path(tmp, 'partial-evidence.2.json').write_text(json.dumps(data))
            report = evaluate(FIXTURES, tmp)
            item = next(item for item in report['variation'] if item['fixture'] == 'partial-evidence')
            self.assertEqual(item['valid_structures'], 2)
            Path(tmp, 'partial-evidence.2.json').write_text('invalid JSON')
            self.assertFalse(evaluate(FIXTURES, tmp)['passed'])
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate(FIXTURES, tmp)
            self.assertEqual(len(report['cases']), 6)
            self.assertTrue(all(c['failures'][0]['rule'] == 'response_missing' for c in report['cases']))

    @patch('subprocess.run', side_effect=AssertionError('CLI must remain offline'))
    def test_cli_exit_status_and_json_report(self, run):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['evaluate']), 0)
        self.assertTrue(json.loads(output.getvalue())['passed'])
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['evaluate', '--responses', tmp]), 1)
        self.assertFalse(json.loads(output.getvalue())['passed'])
