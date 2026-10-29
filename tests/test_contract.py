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
