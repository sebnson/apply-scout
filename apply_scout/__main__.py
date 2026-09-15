"""Dependency-free command-line entry point."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from .core import render, validate
from .schema import SCHEMA

ROOT = Path(__file__).resolve().parent.parent


def build_prompt(inputs, limit=20):
    inputs = Path(inputs)
    for name in ("profile.md", "sources.md"):
        if not (inputs / name).is_file() or not (inputs / name).read_text(encoding="utf-8").strip():
            raise ValueError(f"필수 입력 파일을 작성하세요: {inputs / name}")
    paths = [inputs / name for name in ("profile.md", "portfolio.md", "experience.md", "sources.md") if (inputs / name).is_file()]
    if sum(p.stat().st_size for p in paths) > 500_000:
        raise ValueError("입력 파일 합계는 500 KB 이하여야 합니다.")
    instructions = (ROOT / "docs" / "research-instructions.md").read_text(encoding="utf-8")
    documents = {p.name: p.read_text(encoding="utf-8") for p in paths}
    return (instructions + f"\n\n오늘: {date.today().isoformat()}\n최대 공고 수: {limit}\n"
            + "\n## 출력 JSON Schema\n" + json.dumps(SCHEMA, ensure_ascii=False)
            + "\n\n## 사용자 입력 문서 (JSON 데이터)\n" + json.dumps(documents, ensure_ascii=False))


def provider_command(agent, directory, schema_path, result_path):
    if agent == "codex":
        return ["codex", "--search", "exec", "--sandbox", "read-only", "--skip-git-repo-check",
                "--ephemeral", "--output-schema", str(schema_path), "--output-last-message", str(result_path), "-"]
    return ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
            "--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch", "--no-session-persistence"]


def research(agent, prompt, timeout=900):
    if not shutil.which(agent):
        raise ValueError(f"{agent} CLI를 설치하고 로그인한 뒤 다시 실행하세요.")
    # No generated report or personal files are writable by the research subprocess.
    with tempfile.TemporaryDirectory(prefix="apply-scout-") as directory:
        directory = Path(directory)
        schema_path, result_path = directory / "schema.json", directory / "result.json"
        schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
        command = provider_command(agent, directory, schema_path, result_path)
        print(f"{agent}로 채용 공고를 조사합니다. 최대 {timeout}초 동안 실행합니다.", file=sys.stderr)
        result = subprocess.run(command, input=prompt, text=True, cwd=directory,
                                stdout=subprocess.PIPE, timeout=timeout, check=True)
        if agent == "codex":
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        else:
            envelope = json.loads(result.stdout)
            if envelope.get("is_error") or "structured_output" not in envelope:
                raise ValueError("Claude가 조사 결과를 반환하지 못했습니다. 로그인·권한·CLI 버전을 확인하세요.")
            payload = envelope["structured_output"]
        return validate(payload)


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
            prompt = build_prompt(args.inputs, args.limit)
            if args.command == "prompt":
                print(prompt)
            else:
                if args.timeout <= 0 or args.buffer_days < 0:
                    raise ValueError("제한 시간은 양수, 지원 여유일은 0 이상이어야 합니다.")
                data = research(args.agent, prompt, args.timeout)
                output = Path(args.output)
                path = render(data, output, buffer_days=args.buffer_days)
                (output / "research.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(path.resolve())
        else:
            data = json.loads(args.research.read_text(encoding="utf-8"))
            print(render(data, args.output, args.today, args.buffer_days).resolve())
        return 0
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
