"""Validate research and render a persistent Markdown application tracker."""

import hashlib
import html
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, quote


MATCHES = ("높음", "보통", "낮음", "판단 보류")
DEADLINES = ("dated", "rolling", "unspecified", "unknown")
START = "<!-- user-notes:start -->"
END = "<!-- user-notes:end -->"


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


def text(value):
    """Escape untrusted text for Markdown paragraphs and table cells."""
    value = html.escape(str(value), quote=False).replace("\n", " ").replace("\r", " ")
    for char in "\\`*_[]":
        value = value.replace(char, "\\" + char)
    return value.replace("|", "&#124;")


def link(label, url):
    return f"[{text(label)}]({quote(url, safe=':/?=&%#+@;~-._')})"


def check_string(obj, field):
    if not isinstance(obj.get(field), str) or not obj[field].strip():
        raise ValueError(f"{field}: 비어 있지 않은 문자열이 필요합니다.")


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list) or not isinstance(data.get("sources"), list):
        raise ValueError("jobs와 sources 배열이 필요합니다.")
    check_string(data, "searched_at")
    searched = date.fromisoformat(data["searched_at"])
    seen = set()
    for job in data["jobs"]:
        if not isinstance(job, dict):
            raise ValueError("공고는 객체여야 합니다.")
        for field in ("company", "role", "url", "checked_at", "deadline_kind", "deadline_note", "match", "summary"):
            check_string(job, field)
        key = job_id(job["url"])
        if key in seen:
            raise ValueError("중복 공고 URL이 있습니다. 원문 공고 하나로 통합하세요.")
        seen.add(key)
        checked = date.fromisoformat(job["checked_at"])
        if checked > searched:
            raise ValueError("공고 확인일이 조사일보다 미래입니다.")
        if job["deadline_kind"] not in DEADLINES or job["match"] not in MATCHES:
            raise ValueError("마감일 유형 또는 매칭 평가가 올바르지 않습니다.")
        if job["deadline_kind"] == "dated":
            date.fromisoformat(job.get("deadline", ""))
        elif job.get("deadline") is not None:
            raise ValueError("날짜가 없는 마감 유형은 deadline=null이어야 합니다.")
        if type(job.get("closed")) is not bool:
            raise ValueError("closed는 boolean이어야 합니다.")
        for field in ("requirements", "gaps", "actions"):
            if not isinstance(job.get(field), list):
                raise ValueError(f"{field} 배열이 필요합니다.")
        if not job["requirements"]:
            raise ValueError("공고마다 최소 하나의 요구사항과 판단 근거가 필요합니다.")
        for item in job["requirements"]:
            if not isinstance(item, dict):
                raise ValueError("요구사항은 객체여야 합니다.")
            for field in ("requirement", "evidence", "assessment", "source_url"):
                check_string(item, field)
            canonical_url(item["source_url"])
        for item in job["gaps"] + job["actions"]:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("보완점과 준비 항목은 문자열이어야 합니다.")
    for source in data["sources"]:
        if not isinstance(source, dict):
            raise ValueError("출처는 객체여야 합니다.")
        for field in ("url", "status", "note"):
            check_string(source, field)
        canonical_url(source["url"])
        if source["status"] not in ("checked", "blocked", "failed"):
            raise ValueError("출처 상태는 checked, blocked, failed 중 하나여야 합니다.")
    if not data["sources"]:
        raise ValueError("조사한 출처 또는 접근 실패 기록이 필요합니다.")
    return data


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
                 "## 요구사항과 내 경험", "", "| 요구사항 | 내 경험의 근거 | 판단 | 출처 |", "|---|---|---|---|"]
        for r in job["requirements"]:
            lines.append(f"| {text(r['requirement'])} | {text(r['evidence'])} | {text(r['assessment'])} | {link('원문', r['source_url'])} |")
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
