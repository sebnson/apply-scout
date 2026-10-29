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

## Validation and compatibility

`met`, `partial`, and `unmet` require profile evidence. Missing information uses `unknown`, with a
question or explanation in `rationale`. Evidence filenames must occur in `run.input_files`; live callers
also supply the actual filenames to prevent a fabricated manifest. Offline rendering trusts the saved
manifest and does not read local personal files. Linked job evidence must use the posting URL or a
checked official link declared on that job.

A required `unmet` item forbids `높음`. When every required item is `unknown`, both `높음` and `보통`
are rejected. Empty requirements or entirely unknown importance classifications produce warnings.
Errors include a JSON path and a correction. These checks do not score semantic fit or hiring probability.

Unversioned and explicit `"1"` results retain their original assessments and evidence. The in-memory
converter uses the v2 requirement layout but keeps `schema_version="1"` and the original `legacy` fields;
it does not manufacture file/section references, posting quotations, metadata, or importance. Known Korean
assessment labels map to their equivalent enum; custom legacy labels stay unchanged. This internal view
is not exported as new v2 research. Removing v1 reading requires a separate major-version decision.
