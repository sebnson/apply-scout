import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from apply_scout.core import END, START, canonical_url, job_id, render, validate
from apply_scout.__main__ import build_prompt, main, research
from unittest.mock import patch
from subprocess import CompletedProcess, TimeoutExpired

ROOT = Path(__file__).resolve().parent.parent


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "output"
        self.data = json.loads((ROOT / "examples/research.json").read_text(encoding="utf-8"))
        self.today = date(2026, 9, 15)

    def render(self, data=None):
        return render(data or self.data, self.output, self.today)

    def test_deadline_order_and_links(self):
        content = self.render().read_text(encoding="utf-8")
        self.assertLess(content.index("가상회사 A"), content.index("가상회사 B"))
        self.assertIn("2026-09-18", content)
        for job in self.data["jobs"]:
            self.assertTrue((self.output / "jobs" / f"{job_id(job['url'])}.md").is_file())

    def test_user_status_and_notes_survive_rerun(self):
        path = self.render()
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace("검토 전 |  |", "지원 완료 | 직접 쓴 메모 |", 1).replace(
            START + "\n\n" + END, START + "\n전체 메모\n" + END), encoding="utf-8")
        detail = self.output / "jobs" / f"{job_id(self.data['jobs'][0]['url'])}.md"
        detail.write_text(detail.read_text(encoding="utf-8").replace(START + "\n\n" + END,
            START + "\n면접 준비\n" + END), encoding="utf-8")
        content = self.render().read_text(encoding="utf-8")
        self.assertIn("지원 완료 | 직접 쓴 메모", content)
        self.assertIn("전체 메모", content)
        self.assertIn("면접 준비", detail.read_text(encoding="utf-8"))
        plan = content.split("## 지원 준비 계획")[1].split("## 조사 기록")[0]
        self.assertNotIn("가상회사 A", plan)

    def test_missing_jobs_are_retained_but_not_planned(self):
        self.render()
        self.data["jobs"] = []
        content = self.render().read_text(encoding="utf-8")
        stale = content.split("## 이번 조사에서 재확인하지 못한 공고")[1]
        self.assertIn("가상회사 A", stale)
        self.assertIn("현재 준비할 공고가 없습니다", content)

    def test_expired_jobs_are_not_planned(self):
        content = render(self.data, self.output, date(2026, 10, 1)).read_text(encoding="utf-8")
        self.assertIn("가상회사 A", content.split("## 마감된 공고")[1])

    def test_unknown_deadline_does_not_invent_date(self):
        self.data["jobs"][0].update(deadline=None, deadline_kind="unknown")
        self.assertIn("확인 불가", self.render().read_text(encoding="utf-8"))

    def test_today_deadline_stays_today(self):
        self.data["jobs"][0]["deadline"] = "2026-09-15"
        content = self.render().read_text(encoding="utf-8")
        self.assertIn("2026-09-15 | 높음 | 2026-09-15", content)

    def test_canonical_dedup_keeps_distinct_job_ids_and_hash_routes(self):
        self.assertEqual(job_id("https://example.com/jobs?id=1&utm_source=x"), job_id("https://example.com/jobs?id=1"))
        self.assertNotEqual(job_id("https://example.com/jobs?id=1"), job_id("https://example.com/jobs?id=2"))
        self.assertNotEqual(job_id("https://example.com/#/job/1"), job_id("https://example.com/#/job/2"))
        self.data["jobs"].append(copy.deepcopy(self.data["jobs"][0]))
        with self.assertRaises(ValueError):
            validate(self.data)

    def test_invalid_payload_leaves_existing_report_unchanged(self):
        path = self.render()
        before = path.read_bytes()
        self.data["jobs"][0]["deadline"] = "not-a-date"
        with self.assertRaises(ValueError):
            self.render()
        self.assertEqual(before, path.read_bytes())

    def test_broken_notes_stop_before_writes(self):
        path = self.render()
        path.write_text(path.read_text(encoding="utf-8").replace(END, ""), encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            self.render()
        self.assertEqual(path.read_bytes(), before)

    def test_markdown_text_is_escaped(self):
        self.data["jobs"][0]["company"] = "A | [link](bad) <script>"
        path = self.render()
        self.assertIn("&#124;", path.read_text(encoding="utf-8"))
        self.render()  # Escaped pipes must not break parsing on the next run.

    def test_invalid_links_are_rejected(self):
        for url in ("javascript:alert(1)", "file:///etc/passwd", "https://user:secret@example.com"):
            with self.assertRaises(ValueError):
                canonical_url(url)

    def test_init_does_not_overwrite_profile(self):
        target = Path(self.temp.name) / "inputs"
        main(["init", "--inputs", str(target)])
        (target / "profile.md").write_text("내 경력", encoding="utf-8")
        main(["init", "--inputs", str(target)])
        self.assertEqual((target / "profile.md").read_text(encoding="utf-8"), "내 경력")
        self.assertIn("내 경력", build_prompt(target))

    @patch("apply_scout.__main__.shutil.which", return_value="/bin/fake")
    @patch("apply_scout.__main__.subprocess.run")
    def test_claude_structured_result(self, run, which):
        run.return_value = CompletedProcess([], 0, json.dumps({"structured_output": self.data}))
        self.assertEqual(research("claude", "test"), self.data)
        self.assertNotIn("--dangerously-skip-permissions", run.call_args.args[0])

    @patch("apply_scout.__main__.shutil.which", return_value="/bin/fake")
    @patch("apply_scout.__main__.subprocess.run")
    def test_codex_structured_result(self, run, which):
        def fake(command, **kwargs):
            Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(self.data), encoding="utf-8")
            return CompletedProcess(command, 0, "")
        run.side_effect = fake
        self.assertEqual(research("codex", "test"), self.data)
        self.assertIn("read-only", run.call_args.args[0])

    @patch("apply_scout.__main__.shutil.which", return_value="/bin/fake")
    @patch("apply_scout.__main__.subprocess.run")
    def test_provider_failure_does_not_render(self, run, which):
        run.return_value = CompletedProcess([], 0, json.dumps({"is_error": True, "result": "auth failed"}))
        with self.assertRaises(ValueError):
            research("claude", "test")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
