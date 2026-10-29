import copy
import json
import unittest
from pathlib import Path

from apply_scout.schema import (ASSESSMENTS, DEADLINES, IMPORTANCES, MATCHES,
                                V2_SCHEMA, validate_structure)


def example_v2():
    data = json.loads((Path(__file__).parent / 'fixtures/research-v1.json').read_text())
    data.update(schema_version='2', run={
        'agent': 'fixture', 'instruction_hash': 'sha256:' + '0' * 64,
        'input_files': ['profile.md', 'portfolio.md', 'sources.md'],
    })
    for job in data['jobs']:
        job['official_source_urls'] = []
        job['requirements'] = [{
            'requirement': 'Python API 설계 및 운영', 'importance': 'required',
            'assessment': 'partial',
            'job_evidence': {'source_url': job['url'], 'detail': 'Python API 설계 및 운영'},
            'profile_evidence': [{'file': 'portfolio.md', 'section': '주문 API 개선',
                                  'detail': 'API 설계와 배포'}],
            'rationale': 'API 설계·배포 근거는 있으나 운영 기간은 확인 필요',
        }]
    return data


class ContractTests(unittest.TestCase):
    def test_valid_v2_and_shared_enums(self):
        validate_structure(example_v2())
        job = V2_SCHEMA['properties']['jobs']['items']['properties']
        req = job['requirements']['items']['properties']
        for definition, values in ((job['match'], MATCHES), (job['deadline_kind'], DEADLINES),
                                   (req['importance'], IMPORTANCES), (req['assessment'], ASSESSMENTS)):
            self.assertEqual(definition['enum'], list(values))

    def test_invalid_fields_have_exact_paths(self):
        for field, value in [('importance', 'mandatory'), ('assessment', '충족'),
                             ('rationale', ' '), ('profile_evidence', {}), ('extra', 'x')]:
            with self.subTest(field=field):
                data = example_v2()
                data['jobs'][0]['requirements'][0][field] = value
                with self.assertRaisesRegex(ValueError, r'\$\.jobs\[0\]\.requirements\[0\]\.' + field):
                    validate_structure(data)

    def test_missing_field_and_wrong_scalar_type(self):
        data = example_v2()
        del data['run']['input_files']
        with self.assertRaisesRegex(ValueError, r'\$\.run\.input_files'):
            validate_structure(data)
        data = example_v2()
        data['jobs'][0]['closed'] = 1
        with self.assertRaisesRegex(ValueError, r'\$\.jobs\[0\]\.closed'):
            validate_structure(data)


class ConsistencyTests(unittest.TestCase):
    def test_evidence_and_input_manifest(self):
        from apply_scout.validation import validate
        for assessment in ('met', 'partial', 'unmet'):
            data = example_v2()
            req = data['jobs'][0]['requirements'][0]
            req.update(assessment=assessment, profile_evidence=[])
            with self.subTest(assessment=assessment), self.assertRaisesRegex(ValueError, 'profile_evidence'):
                validate(data)
        data = example_v2()
        data['jobs'][0]['requirements'][0]['profile_evidence'][0]['file'] = 'resume.md'
        with self.assertRaisesRegex(ValueError, r'profile_evidence\[0\].file'):
            validate(data)
        with self.assertRaisesRegex(ValueError, 'run.input_files'):
            validate(example_v2(), input_files=['profile.md'])

    def test_unknown_requires_explanation(self):
        from apply_scout.validation import validate
        data = example_v2()
        data['jobs'][0]['match'] = '판단 보류'
        req = data['jobs'][0]['requirements'][0]
        req.update(assessment='unknown', profile_evidence=[])
        validate(data)
        req['rationale'] = ''
        with self.assertRaisesRegex(ValueError, 'rationale'):
            validate(data)

    def test_contradictory_matches(self):
        from apply_scout.validation import validate
        for assessment, match in [('unmet', '높음'), ('unknown', '높음'), ('unknown', '보통')]:
            data = example_v2()
            data['jobs'][0]['match'] = match
            data['jobs'][0]['requirements'][0]['assessment'] = assessment
            with self.subTest(assessment=assessment, match=match), self.assertRaisesRegex(ValueError, r'\$\.jobs\[0\].match'):
                validate(data)
        data = example_v2()
        data['jobs'][0]['requirements'][0].update(importance='preferred', assessment='unmet')
        validate(data)  # A preferred gap is not an essential-condition conflict.

    def test_job_evidence_must_be_posting_or_checked_official_link(self):
        from apply_scout.validation import validate
        data = example_v2()
        url = 'https://example.com/official/requirements'
        data['jobs'][0]['requirements'][0]['job_evidence']['source_url'] = url
        with self.assertRaisesRegex(ValueError, 'job_evidence.source_url'):
            validate(data)
        data['jobs'][0]['official_source_urls'] = [url]
        data['sources'].append({'url': url, 'status': 'blocked', 'note': 'fictional'})
        with self.assertRaisesRegex(ValueError, 'official_source_urls'):
            validate(data)
        data['sources'][-1]['status'] = 'checked'
        validate(data)

    def test_warnings_and_common_error_paths(self):
        from apply_scout.validation import validate, validate_consistency
        data = example_v2()
        data['jobs'][0]['requirements'] = []
        validate(data)
        self.assertIn('$.jobs[0].requirements', validate_consistency(data)[0])
        data['jobs'][0]['deadline'] = 'bad-date'
        with self.assertRaisesRegex(ValueError, r'\$\.jobs\[0\].deadline'):
            validate(data)

    def test_legacy_conversion_is_lossless_and_does_not_mutate(self):
        from apply_scout.validation import normalize, validate
        path = Path(__file__).parent / 'fixtures/research-v1.json'
        data = json.loads(path.read_text())
        data['jobs'][0]['requirements'][0]['assessment'] = 'legacy custom assessment'
        original = copy.deepcopy(data)
        validate(data)
        result = normalize(data)
        req = result['jobs'][0]['requirements'][0]
        self.assertEqual(req['legacy'], data['jobs'][0]['requirements'][0])
        self.assertEqual(req['assessment'], 'legacy custom assessment')
        self.assertEqual(req['importance'], 'unknown')
        self.assertEqual(req['profile_evidence'], [])
        self.assertEqual(result['schema_version'], '1')
        self.assertEqual(data, original)
