# Research contract v2

**English** · [한국어](../ko/research-contract.md)

The dictionary contract in `apply_scout/schema.py` shares enum constants with runtime validation.
The v2 contract is introduced before switching provider output; v1 remains supported.

- `schema_version`: `"2"`.
- `run`: `agent`, `instruction_hash` (`sha256:` plus 64 hexadecimal digits), and `input_files`
  (names of documents included in this run, not their contents).
- Requirements: `requirement`, `importance` (`required`, `preferred`, `responsibility`, `unknown`),
  `assessment` (`met`, `partial`, `unmet`, `unknown`), and a non-empty `rationale`.
- `job_evidence`: `source_url` and `detail` from the posting.
- `profile_evidence`: an array of `file`, `section`, and `detail` objects.
- Each job has `official_source_urls`: official linked pages actually researched, also recorded as
  `checked` in `sources`. Use an empty array when only the posting URL supplies evidence.
- Overall `match` retains `높음`, `보통`, `낮음`, and `판단 보류`.

The instruction hash covers only runtime instructions and the JSON Schema, never personal documents
or the complete prompt. Code checks structure and internal consistency; it cannot establish whether
an official-source claim or experience description is true. Users still need to review the evidence.
