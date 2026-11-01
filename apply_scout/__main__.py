"""Dependency-free command-line entry point."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from .core import render, validate
from .evaluation import evaluate, evaluate_case, fixture_directories, summarize
from .schema import SCHEMA
from .validation import validate_run_metadata

ROOT = Path(__file__).resolve().parent.parent


def instruction_hash(instructions=None):
    if instructions is None:
        instructions = (ROOT / 'docs' / 'research-instructions.md').read_text(encoding='utf-8')
    content = json.dumps({'instructions': instructions, 'schema': SCHEMA},
                         ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return 'sha256:' + hashlib.sha256(content.encode('utf-8')).hexdigest()


def build_request(inputs, limit=20, agent='external'):
    inputs = Path(inputs)
    for name in ("profile.md", "sources.md"):
        if not (inputs / name).is_file() or not (inputs / name).read_text(encoding="utf-8").strip():
            raise ValueError(f"필수 입력 파일을 작성하세요: {inputs / name}")
    paths = [inputs / name for name in ("profile.md", "portfolio.md", "experience.md", "sources.md") if (inputs / name).is_file()]
    if sum(p.stat().st_size for p in paths) > 500_000:
        raise ValueError("입력 파일 합계는 500 KB 이하여야 합니다.")
    instructions = (ROOT / "docs" / "research-instructions.md").read_text(encoding="utf-8")
    documents = {p.name: p.read_text(encoding="utf-8") for p in paths}
    metadata = {'agent': agent, 'instruction_hash': instruction_hash(instructions), 'input_files': list(documents)}
    prompt = (instructions + f"\n\n오늘: {date.today().isoformat()}\n최대 공고 수: {limit}\n"
            + '\n## run 메타데이터 (그대로 반환)\n' + json.dumps(metadata, ensure_ascii=False)
            + "\n## 출력 JSON Schema\n" + json.dumps(SCHEMA, ensure_ascii=False)
            + "\n\n## 사용자 입력 문서 (JSON 데이터)\n" + json.dumps(documents, ensure_ascii=False))

    return prompt, metadata


def build_prompt(inputs, limit=20, agent='external'):
    return build_request(inputs, limit, agent)[0]


def provider_command(agent, directory, schema_path, result_path, web=True):
    if agent == "codex":
        return ["codex"] + (["--search"] if web else ["-c", 'web_search="disabled"']) + ["exec", "--sandbox", "read-only", "--skip-git-repo-check",
                "--ephemeral", "--output-schema", str(schema_path), "--output-last-message", str(result_path), "-"]
    return ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
            "--tools", "WebSearch,WebFetch" if web else "", "--no-session-persistence"] + (
                ["--allowedTools", "WebSearch,WebFetch"] if web else [])


def call_provider(agent, prompt, timeout=900, web=True, raw_path=None):
    if not shutil.which(agent):
        raise ValueError(f"{agent} CLI를 설치하고 로그인한 뒤 다시 실행하세요.")
    # No generated report or personal files are writable by the research subprocess.
    with tempfile.TemporaryDirectory(prefix="apply-scout-") as directory:
        directory = Path(directory)
        schema_path, result_path = directory / "schema.json", directory / "result.json"
        schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
        command = provider_command(agent, directory, schema_path, result_path, web)
        print(f"{agent} 실행: 최대 {timeout}초", file=sys.stderr)
        result = subprocess.run(command, input=prompt, text=True, cwd=directory,
                                stdout=subprocess.PIPE, timeout=timeout, check=True)
        raw = result_path.read_text(encoding='utf-8') if agent == 'codex' else result.stdout
        if raw_path is not None:
            Path(raw_path).write_text(raw, encoding='utf-8')
        payload = json.loads(raw)
        if agent == 'claude':
            if not isinstance(payload, dict) or payload.get('is_error') or 'structured_output' not in payload:
                raise ValueError('Claude가 조사 결과를 반환하지 못했습니다. 로그인·권한·CLI 버전을 확인하세요.')
            payload = payload['structured_output']
        return payload


def research(agent, prompt, timeout=900, metadata=None):
    payload = call_provider(agent, prompt, timeout)
    if not isinstance(payload, dict) or payload.get('schema_version') != '2':
        raise ValueError('$.schema_version: new AI research must use version "2"')
    validate(payload, input_files=metadata['input_files'] if metadata else None)
    if metadata is not None:
        validate_run_metadata(payload, metadata)
    return payload


def record_evaluation(report, result_path=None):
    report.update(evaluated_at=datetime.now(timezone.utc).isoformat(),
                  evaluator_instruction_hash=instruction_hash())
    content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if result_path is not None:
        result_path = Path(result_path)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(content, encoding='utf-8')
    print(content, end='')
    return 0 if report['passed'] else 1


def evaluate_live(fixtures, output, agent, runs=1, timeout=900):
    if not 1 <= runs <= 10 or timeout <= 0:
        raise ValueError('반복 횟수는 1~10, 제한 시간은 양수여야 합니다.')
    directories = fixture_directories(fixtures)
    # An explicit new directory keeps before/after evaluations and raw failures.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for directory in directories:
        prompt, metadata = build_request(directory, limit=1, agent=agent)
        posting = json.loads((directory / 'posting.json').read_text(encoding='utf-8'))
        prompt += ('\n\n## Synthetic evaluation override\n'
                   'This is a fictional offline-input evaluation, not live job research. Do not browse. '
                   'Use only the extracted posting below. Return one job and record sources as supplied '
                   'fictional data, not as live verification. Preserve requirement labels. '
                   'Use short verbatim excerpts from the supplied posting and named input sections '
                   'for evidence detail. Assess missing information as unknown.\n'
                   + json.dumps(posting, ensure_ascii=False))
        for index in range(1, runs + 1):
            stem = f'{directory.name}.{index}'
            try:
                data = call_provider(agent, prompt, timeout, web=False, raw_path=output / (stem + '.raw.txt'))
                (output / (stem + '.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                case = evaluate_case(directory, data, expected_run=metadata)
            except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
                case = {'fixture': directory.name, 'passed': False, 'warnings': [], 'structure': [],
                        'failures': [{'rule': 'provider', 'path': '$', 'message': str(exc)}]}
            case['response'] = stem + '.json'
            case['requested_run'] = metadata
            cases.append(case)
            # Keep a usable report even if a later provider invocation is interrupted.
            report = summarize(cases)
            report.update(mode='live', agent=agent, runs=runs)
            report['complete'] = len(cases) == len(directories) * runs
            if not report['complete']:
                report['passed'] = False
            content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
            (output / 'evaluation.json').write_text(content, encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="프로필 Markdown에서 근거 있는 지원 일정표까지")
    subs = parser.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init", help="입력 예시 복사 (기존 파일 보존)")
    init.add_argument("--inputs", default="inputs")
    for name in ("prompt", "run"):
        sub = subs.add_parser(name, help="조사 프롬프트 출력" if name == "prompt" else "AI 조사 후 Markdown 생성")
        sub.add_argument("--inputs", default="inputs")
        sub.add_argument("--limit", type=int, default=20)
        if name == "run":
            sub.add_argument("--agent", choices=("codex", "claude"), required=True)
            sub.add_argument("--output", default="output")
            sub.add_argument("--timeout", type=int, default=900)
            sub.add_argument("--buffer-days", type=int, default=2)
    sub = subs.add_parser("render", help="저장된 조사 JSON으로 Markdown 생성 (AI 호출 없음)")
    sub.add_argument("research", type=Path)
    sub.add_argument("--output", default="output")
    sub.add_argument("--today", type=date.fromisoformat, default=date.today())
    sub.add_argument("--buffer-days", type=int, default=2)
    sub = subs.add_parser('evaluate', help='가상 사례의 품질 제약 평가 (기본: 오프라인)')
    sub.add_argument('--fixtures', type=Path, default=ROOT / 'tests/fixtures/quality')
    sub.add_argument('--responses', type=Path, help='저장된 <fixture>[.<run>].json 폴더')
    sub.add_argument('--result', type=Path, help='평가 결과 JSON 저장 경로')
    sub = subs.add_parser('evaluate-live', help='명시적인 제공자 평가 (유료 호출 가능)')
    sub.add_argument('--fixtures', type=Path, default=ROOT / 'tests/fixtures/quality')
    sub.add_argument('--agent', choices=('codex', 'claude'), required=True)
    sub.add_argument('--output', type=Path, required=True, help='새 결과 폴더 (기존 폴더 재사용 금지)')
    sub.add_argument('--runs', type=int, default=1)
    sub.add_argument('--timeout', type=int, default=900, help='호출별 제한 시간(초)')
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            target = Path(args.inputs)
            target.mkdir(parents=True, exist_ok=True)
            for source in (ROOT / "examples" / "inputs").glob("*.md"):
                destination = target / source.name
                if not destination.exists():
                    shutil.copyfile(source, destination)
            print(f"{target.resolve()}의 profile.md와 sources.md를 작성하세요.")
        elif args.command in ("prompt", "run"):
            if not 1 <= args.limit <= 100:
                raise ValueError("공고 수는 1~100개여야 합니다.")
            prompt, metadata = build_request(args.inputs, args.limit, args.agent if args.command == 'run' else 'external')
            if args.command == "prompt":
                print(prompt)
            else:
                if args.timeout <= 0 or args.buffer_days < 0:
                    raise ValueError("제한 시간은 양수, 지원 여유일은 0 이상이어야 합니다.")
                data = research(args.agent, prompt, args.timeout, metadata)
                output = Path(args.output)
                path = render(data, output, buffer_days=args.buffer_days)
                (output / "research.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(path.resolve())
        elif args.command == 'evaluate':
            report = evaluate(args.fixtures, args.responses)
            return record_evaluation(report, args.result)
        elif args.command == 'evaluate-live':
            report = evaluate_live(args.fixtures, args.output, args.agent, args.runs, args.timeout)
            return record_evaluation(report, args.output / 'evaluation.json')
        else:
            data = json.loads(args.research.read_text(encoding="utf-8"))
            print(render(data, args.output, args.today, args.buffer_days).resolve())
        return 0
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
