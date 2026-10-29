"""Research validation and lossless v1 reading, independent of rendering."""

import copy
import hashlib
import re
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .schema import V1_SCHEMA, V2_SCHEMA, validate_structure


def canonical_url(value):
    parts = urlsplit(value)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise ValueError("공고·출처 링크는 자격 증명이 없는 http(s) URL이어야 합니다.")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")]
    # Preserve fragments: several ATS products use hash-based job routes.
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/",
                       urlencode(sorted(query)), parts.fragment))


def job_id(url):
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()[:16]


def fail(path, message):
    raise ValueError(f"{path}: {message}")


def at(path, function, value):
    try:
        return function(value)
    except (ValueError, TypeError) as exc:
        fail(path, str(exc))


def legacy_schema():
    # Existing readers allowed additional keys. Do not narrow the v1 contract.
    schema = copy.deepcopy(V1_SCHEMA)
    def relax(node):
        if node.get('type') == 'object':
            node['additionalProperties'] = True
            for item in node['properties'].values():
                relax(item)
        elif node.get('type') == 'array':
            relax(node['items'])
    relax(schema)
    return schema


LEGACY_SCHEMA = legacy_schema()


def validate(data, input_files=None):
    """Return the unchanged payload after validation; no disk access is needed.

    Live runs pass the actual input filenames. Offline rendering can only check
    the manifest recorded in the result, not prove what the agent originally saw.
    """
    if not isinstance(data, dict):
        fail('$', 'provide a research object')
    version = data.get('schema_version', '1')
    if version not in ('1', '2'):
        fail('$.schema_version', 'supported versions are "1" and "2"')
    validate_structure(data, V2_SCHEMA if version == '2' else LEGACY_SCHEMA)
    searched = at('$.searched_at', date.fromisoformat, data['searched_at'])
    seen = set()
    for index, job in enumerate(data['jobs']):
        path = f'$.jobs[{index}]'
        key = at(path + '.url', job_id, job['url'])
        if key in seen:
            fail(path + '.url', 'merge duplicate posting URLs into one job')
        seen.add(key)
        checked = at(path + '.checked_at', date.fromisoformat, job['checked_at'])
        if checked > searched:
            fail(path + '.checked_at', 'check date cannot be later than searched_at')
        if job['deadline_kind'] == 'dated':
            at(path + '.deadline', date.fromisoformat, job['deadline'])
        elif job['deadline'] is not None:
            fail(path + '.deadline', 'use null for an undated deadline kind')
        if version == '1':
            if not job['requirements']:
                fail(path + '.requirements', 'provide at least one requirement')
            for ri, requirement in enumerate(job['requirements']):
                at(f'{path}.requirements[{ri}].source_url', canonical_url, requirement['source_url'])
    if not data['sources']:
        fail('$.sources', 'record at least one checked, blocked, or failed source')
    for index, source in enumerate(data['sources']):
        at(f'$.sources[{index}].url', canonical_url, source['url'])
    if version == '2':
        validate_consistency(data, input_files)
    return data


def validate_consistency(data, input_files=None):
    """Check a structurally valid v2 payload. Return non-fatal warnings."""
    run = data['run']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', run['instruction_hash']):
        fail('$.run.instruction_hash', 'use sha256: followed by 64 lowercase hexadecimal digits')
    names = run['input_files']
    if not names or len(names) != len(set(names)):
        fail('$.run.input_files', 'list the included input filenames once each')
    if any('/' in name or '\\' in name or name in ('.', '..') for name in names):
        fail('$.run.input_files', 'use filenames, not paths')
    if input_files is not None and set(names) != set(input_files):
        fail('$.run.input_files', 'must match the documents actually included in this run')
    checked = {canonical_url(s['url']) for s in data['sources'] if s['status'] == 'checked'}
    warnings = []
    for ji, job in enumerate(data['jobs']):
        path = f'$.jobs[{ji}]'
        allowed = {canonical_url(job['url'])}
        for ui, url in enumerate(job['official_source_urls']):
            canonical = at(f'{path}.official_source_urls[{ui}]', canonical_url, url)
            if canonical not in checked:
                fail(f'{path}.official_source_urls[{ui}]', 'record the researched official link as checked in sources')
            allowed.add(canonical)
        for ri, req in enumerate(job['requirements']):
            rp = f'{path}.requirements[{ri}]'
            url = at(rp + '.job_evidence.source_url', canonical_url, req['job_evidence']['source_url'])
            if url not in allowed:
                fail(rp + '.job_evidence.source_url', 'use the posting URL or a checked official_source_urls entry')
            if req['assessment'] != 'unknown' and not req['profile_evidence']:
                fail(rp + '.profile_evidence', 'met, partial, and unmet need input evidence; use unknown when information is missing')
            for ei, evidence in enumerate(req['profile_evidence']):
                if evidence['file'] not in names:
                    fail(f'{rp}.profile_evidence[{ei}].file', 'reference a filename included in run.input_files')
        required = [r for r in job['requirements'] if r['importance'] == 'required']
        if job['match'] == '높음' and any(r['assessment'] == 'unmet' for r in required):
            fail(path + '.match', 'required + unmet cannot have 높음; revise the overall match')
        if required and all(r['assessment'] == 'unknown' for r in required) and job['match'] in ('높음', '보통'):
            fail(path + '.match', 'all required items are unknown; use 낮음 or 판단 보류')
        if not job['requirements'] or all(r['importance'] == 'unknown' for r in job['requirements']):
            warnings.append(path + '.requirements: 요구사항 또는 중요도 분류가 없어 매칭 평가를 검토해야 합니다.')
    return warnings


def normalize(data):
    """Copy v1 requirements to the v2 layout without fabricating provenance.

    The internal result keeps schema_version=1 and original legacy fields. It is
    not new v2 research and must not be passed through v2 consistency checks.
    """
    result = copy.deepcopy(data)
    if result.get('schema_version') == '2':
        return result
    result['schema_version'] = '1'
    labels = {'충족': 'met', '부분 충족': 'partial', '미충족': 'unmet', '확인 필요': 'unknown'}
    for job in result['jobs']:
        job['official_source_urls'] = []
        for req in job['requirements']:
            original = dict(req)
            req.clear()
            req.update(requirement=original['requirement'], importance='unknown',
                       assessment=labels.get(original['assessment'], original['assessment']),
                       job_evidence={'source_url': original['source_url'], 'detail': ''},
                       profile_evidence=[], rationale=original['evidence'], legacy=original)
    return result
