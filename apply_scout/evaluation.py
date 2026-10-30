"""Constraint-based evaluation of fictional fixtures, offline by default."""

import json
from pathlib import Path

from .validation import validate, validate_consistency, validate_run_metadata


def compact(value):
    return ' '.join(value.split()).casefold()


def evaluate_case(directory, data, expected_run=None):
    directory = Path(directory)
    expected = json.loads((directory / 'expected.json').read_text(encoding='utf-8'))
    posting = json.loads((directory / 'posting.json').read_text(encoding='utf-8'))
    documents = {p.name: p.read_text(encoding='utf-8') for p in directory.glob('*.md')}
    result = {'fixture': directory.name, 'passed': False, 'failures': [], 'warnings': [], 'structure': []}

    def failure(rule, path, message):
        result['failures'].append({'rule': rule, 'path': path, 'message': message})

    if not isinstance(data, dict) or data.get('schema_version') != '2':
        failure('contract', '$.schema_version', 'quality evaluation requires v2 research')
        return result
    try:
        validate(data, input_files=documents)
        if expected_run is not None:
            validate_run_metadata(data, expected_run)
    except (ValueError, TypeError) as exc:
        message = str(exc)
        path, _, detail = message.partition(': ')
        failure('contract', path if path.startswith('$') else '$', detail or message)
        return result
    result['run'] = dict(data['run'])
    result['warnings'] = validate_consistency(data)
    if len(result['warnings']) != expected.get('warning_count', 0):
        failure('warnings', '$.jobs', f"expected {expected.get('warning_count', 0)} warnings; got {len(result['warnings'])}")
    if len(data['jobs']) != 1 or data['jobs'][0]['url'] != posting['url']:
        failure('posting_identity', '$.jobs', 'return exactly the supplied fictional posting')
        return result
    job = data['jobs'][0]
    if job['match'] not in expected['matches']:
        failure('overall_match', '$.jobs[0].match', f"expected one of {expected['matches']}")
    requirements = job['requirements']
    for condition in expected['requirements']:
        matches = [(i, r) for i, r in enumerate(requirements)
                   if compact(r['requirement']) == compact(condition['requirement'])]
        if len(matches) != 1:
            failure('requirement_coverage', '$.jobs[0].requirements',
                    f"include {condition['requirement']!r} exactly once")
            continue
        index, req = matches[0]
        path = f'$.jobs[0].requirements[{index}]'
        if req['importance'] != condition['importance']:
            failure('importance', path + '.importance', f"expected {condition['importance']}")
        if req['assessment'] not in condition['assessments']:
            failure('assessment', path + '.assessment', f"expected one of {condition['assessments']}")
    known = {compact(r['requirement']): r for r in posting['requirements']}
    for index, req in enumerate(requirements):
        path = f'$.jobs[0].requirements[{index}]'
        source = known.get(compact(req['requirement']))
        if source is None:
            failure('unsupported_requirement', path + '.requirement', 'requirement is absent from the extracted posting')
        elif compact(req['job_evidence']['detail']) not in compact(source['detail']):
            failure('posting_evidence', path + '.job_evidence.detail', 'use an excerpt from the extracted posting')
        for ei, evidence in enumerate(req['profile_evidence']):
            ep = f'{path}.profile_evidence[{ei}]'
            document = documents[evidence['file']]
            # Fixtures request short verbatim excerpts: this catches additions
            # without claiming to judge the meaning of arbitrary paraphrases.
            sections = {}
            current = None
            for line in document.splitlines():
                if line.startswith('#'):
                    current = compact(line.lstrip('#').strip())
                    sections.setdefault(current, [])
                elif current is not None:
                    sections[current].append(line)
            body = ' '.join(sections.get(compact(evidence['section']), []))
            if compact(evidence['detail']) not in compact(body):
                failure('input_evidence', ep, 'quote evidence from the named input file and section')
            for forbidden in expected.get('forbidden_evidence', []):
                if compact(forbidden) in compact(evidence['detail']):
                    failure('forbidden_evidence', ep + '.detail', f'unsupported claim: {forbidden}')
    result['structure'] = sorted([
        {'requirement': compact(r['requirement']), 'importance': r['importance'],
         'assessment': r['assessment'], 'evidence_count': len(r['profile_evidence'])}
        for r in requirements], key=lambda r: r['requirement'])
    result['passed'] = not result['failures']
    return result


def fixture_directories(root):
    directories = sorted(path.parent for path in Path(root).glob('*/expected.json'))
    if not directories:
        raise ValueError(f'No quality fixtures found: {root}')
    return directories


def evaluate(root, responses=None):
    """Read bundled responses, or <fixture>.json / <fixture>.<run>.json files."""
    cases = []
    for directory in fixture_directories(root):
        paths = [directory / 'response.json'] if responses is None else sorted(
            p for p in Path(responses).glob(directory.name + '*.json')
            if p.name == directory.name + '.json' or p.name.startswith(directory.name + '.'))
        if not paths:
            cases.append({'fixture': directory.name, 'passed': False, 'failures': [
                {'rule': 'response_missing', 'path': '$', 'message': 'no saved response for fixture'}],
                'warnings': [], 'structure': []})
        for path in paths:
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, OSError) as exc:
                cases.append({'fixture': directory.name, 'passed': False, 'failures': [
                    {'rule': 'response_read', 'path': '$', 'message': str(exc)}],
                    'warnings': [], 'structure': []})
            else:
                cases.append(evaluate_case(directory, data))
            cases[-1]['response'] = path.name
    return summarize(cases)


def summarize(cases):
    variation = []
    for name in sorted({case['fixture'] for case in cases}):
        runs = [case for case in cases if case['fixture'] == name]
        structures = {json.dumps(case['structure'], sort_keys=True) for case in runs if not case['failures']}
        variation.append({'fixture': name, 'runs': len(runs), 'valid_structures': len(structures)})
    return {'mode': 'offline', 'passed': all(case['passed'] for case in cases),
            'cases': cases, 'variation': variation}
