"""Validate research and render a persistent Markdown application tracker."""

import html
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from .schema import MATCHES
from .validation import canonical_url, job_id, normalize, validate, validate_consistency

START = "<!-- user-notes:start -->"
END = "<!-- user-notes:end -->"


def text(value):
    """Escape untrusted text for Markdown paragraphs and table cells."""
    value = html.escape(str(value), quote=False).replace("\n", " ").replace("\r", " ")
    for char in "\\`*_[]":
        value = value.replace(char, "\\" + char)
    return value.replace("|", "&#124;")


def link(label, url):
    return f"[{text(label)}]({quote(url, safe=':/?=&%#+@;~-._')})"


def user_notes(path):
    if not path.exists():
        return "\n\n"
    content = path.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError(f"메모 경계가 변경되어 덮어쓰기를 중단합니다: {path}")
    before, after = content.split(START)
    notes, _ = after.split(END)
    return notes


def tracker_edits(path):
    edits = {}
    if not path.exists():
        return edits
    for row in path.read_text(encoding="utf-8").splitlines():
        if not row.lstrip().startswith("|"):
            continue
        match = re.search(r"\]\(jobs/([a-f0-9]{16})\.md\)", row)
        if not match:
            continue
        cells = [x.strip() for x in row.strip().strip("|").split("|")]
        if len(cells) != 9:
            raise ValueError("지원표의 열 수가 바뀌었습니다. 메모 안의 |는 &#124;로 적어 주세요.")
        # These cells are already Markdown. Keep their exact contents on re-render.
        edits[match[1]] = {"status": cells[-2], "note": cells[-1]}
    return edits


def deadline_label(job):
    return job["deadline"] if job["deadline_kind"] == "dated" else {
        "rolling": "상시채용", "unspecified": "미기재", "unknown": "확인 불가"
    }[job["deadline_kind"]]


def is_closed(job, today):
    return job["closed"] or (job["deadline_kind"] == "dated" and date.fromisoformat(job["deadline"]) < today)


def render(data, output, today=None, buffer_days=2):
    validate(data)
    warnings = validate_consistency(data) if data.get('schema_version') == '2' else []
    data = normalize(data)
    today = today or date.today()
    if buffer_days < 0:
        raise ValueError("지원 여유일은 0 이상이어야 합니다.")
    output = Path(output)
    state_path = output / ".state.json"
    tracker_path = output / "apply-tracker.md"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"jobs": {}}
    edits = tracker_edits(tracker_path)
    for key, item in state["jobs"].items():
        item.update(edits.get(key, {}))
    current = set()
    for job in data["jobs"]:
        key = job_id(job["url"])
        current.add(key)
        old = state["jobs"].get(key, {})
        state["jobs"][key] = {"job": job, "status": old.get("status", "검토 전"), "note": old.get("note", "")}

    # Prepare every file first. Invalid research/notes never overwrite existing reports.
    files = {}
    tracker_notes = user_notes(tracker_path)
    for key in current:
        job = state["jobs"][key]["job"]
        path = output / "jobs" / f"{key}.md"
        notes = user_notes(path)
        lines = [f"# {text(job['company'])} · {text(job['role'])}", "", "[← 지원 일정표](../apply-tracker.md)", "",
                 f"- 공고: {link('원문 보기', job['url'])}", f"- 확인일: {job['checked_at']}",
                 f"- 마감일: {deadline_label(job)}", f"- 마감 안내: {text(job['deadline_note'])}",
                 f"- 매칭 평가: **{job['match']}**", "", "## 직무와 적합성 요약", "", text(job["summary"]), "",
                 "## 요구사항과 내 경험", ""]
        if data['schema_version'] == '1':
            lines += ["| 요구사항 | 내 경험의 근거 | 판단 | 출처 |", "|---|---|---|---|"]
            for r in job['requirements']:
                old = r['legacy']
                lines.append(f"| {text(r['requirement'])} | {text(old['evidence'])} | {text(old['assessment'])} | {link('원문', old['source_url'])} |")
        else:
            importance = {'required': '필수', 'preferred': '우대', 'responsibility': '담당 업무', 'unknown': '확인 필요'}
            assessment = {'met': '충족', 'partial': '부분 충족', 'unmet': '미충족', 'unknown': '확인 필요'}
            lines += ["| 요구사항 | 중요도 | 공고 근거 | 내 경험의 근거 | 판단 | 판단 이유 | 출처 |", "|---|---|---|---|---|---|---|"]
            for r in job['requirements']:
                evidence = '; '.join(f"{e['file']} / {e['section']}: {e['detail']}" for e in r['profile_evidence']) or '입력 근거 없음'
                cells = [text(r['requirement']), importance[r['importance']], text(r['job_evidence']['detail']),
                         text(evidence), assessment[r['assessment']], text(r['rationale']), link('원문', r['job_evidence']['source_url'])]
                lines.append('| ' + ' | '.join(cells) + ' |')
            index = next(i for i, item in enumerate(data['jobs']) if job_id(item['url']) == key)
            job_warnings = [warning for warning in warnings if warning.startswith(f'$.jobs[{index}].')]
            if job_warnings:
                lines += ['', '## 검증 경고', ''] + [f'- {text(w)}' for w in job_warnings]
        for title, field in (("보완점·확인할 조건", "gaps"), ("지원 준비", "actions")):
            lines += ["", f"## {title}", ""] + [f"- {text(x)}" for x in job[field]]
        lines += ["", "## 내 메모", "", START + notes + END, ""]
        files[path] = "\n".join(lines)

    groups = {"지원할 공고": [], "이번 조사에서 재확인하지 못한 공고": [], "마감된 공고": []}
    for key, item in state["jobs"].items():
        group = "마감된 공고" if is_closed(item["job"], today) else (
            "지원할 공고" if key in current else "이번 조사에서 재확인하지 못한 공고")
        groups[group].append((key, item))
    lines = ["# Apply Tracker", "", f"조사일: {data['searched_at']} · 일정 기준일: {today.isoformat()}", "",
             "상태·메모 열과 ‘내 메모’ 영역은 수정할 수 있으며 재실행해도 보존됩니다.",
             "권장 지원일은 마감일에서 여유일을 뺀 목표일입니다. 실제 마감 시각·시간대는 원문에서 확인하세요.", ""]
    if warnings:
        lines += ['## 검증 경고', ''] + [f'- {text(w)}' for w in warnings] + ['']
    plans = []
    for title, items in groups.items():
        items.sort(key=lambda pair: (pair[1]["job"].get("deadline") or "9999-12-31", MATCHES.index(pair[1]["job"]["match"]), pair[0]))
        lines += [f"## {title}", "", "| 순서 | 회사 / 분석 | 직무 | 공고 | 마감일 | 매칭 | 권장 지원일 | 상태 | 메모 |", "|---|---|---|---|---|---|---|---|---|"]
        for number, (key, item) in enumerate(items, 1):
            job = item["job"]
            target = "—"
            actionable = title == "지원할 공고" and item["status"] not in ("지원 완료", "지원 안 함", "합격", "불합격")
            if actionable:
                if job["deadline_kind"] == "dated":
                    target = max(today, date.fromisoformat(job["deadline"]) - timedelta(days=buffer_days)).isoformat()
                else:
                    target = "마감 확인 후 결정"
                plans.append(f"- **{target}** · [{text(job['company'])} / {text(job['role'])}](jobs/{key}.md): " +
                             "; ".join(text(x) for x in job["actions"]))
            cells = [str(number), f"[{text(job['company'])}](jobs/{key}.md)", text(job["role"]), link("원문", job["url"]),
                     deadline_label(job), job["match"], target, item["status"], item["note"]]
            lines.append("| " + " | ".join(cells) + " |")
        if not items:
            lines += ["", "해당 공고 없음."]
        lines += [""]
    lines += ["## 지원 준비 계획", ""] + (plans or ["현재 준비할 공고가 없습니다."])
    lines += ["", "## 조사 기록", "", "사이트 접근 실패는 ‘공고 없음’을 의미하지 않습니다.", ""]
    labels = {"checked": "확인", "blocked": "접근 제한", "failed": "조사 실패"}
    for source in data["sources"]:
        lines.append(f"- {link(source['url'], source['url'])} · {labels[source['status']]}: {text(source['note'])}")
    lines += ["", "## 내 메모", "", START + tracker_notes + END, ""]
    files[tracker_path] = "\n".join(lines)
    files[state_path] = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    return tracker_path
