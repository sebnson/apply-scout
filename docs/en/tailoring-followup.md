# Tailoring and bounded rewriting follow-up

**English** · [한국어](../ko/tailoring-followup.md)

Status: proposed follow-up; not implemented in v0.2. The [research contract](research-contract.md) and
[quality evaluation](quality-evaluation.md) provide the prerequisite evidence structure. This plan keeps
resume editing and application submission outside the tool. Implement the steps below separately.

## 1. Selected-job contract and stable references

Add `tailor <research> --job <job-id> --inputs <directory> --resume <optional-file> --agent <provider>`.
Resolve exactly one existing job by the canonical URL-based ID before calling a provider. For v1 research,
require new structured evidence or return a review-only outline; never invent missing references.

Use requirement IDs derived from job ID, normalized requirement text, and importance. Keep a content
revision alongside each ID so changed evidence invalidates dependent suggestions. Reject duplicate
requirement identities. A suggestion ID combines job ID, linked requirement IDs, source location, and
suggestion kind. Store a separate revision digest of original/proposed text and evidence references.
These digests belong to private tailoring state, not the research instruction hash.

Read only explicitly selected resume and input documents under the supplied input directory. Resolve
paths before reading, reject traversal and escaping symlinks, and never fetch a model-supplied filename.
Evidence identifies filename, section, exact excerpt, and occurrence or line span. Ambiguous or missing
original sentences produce an outline with `original=null`, not a fabricated rewrite.

## 2. Suggestions and review state

Write `output/jobs/<job-id>-tailoring.json` and `.md` with original/proposed text, requirement IDs,
evidence references, validation messages, and `accepted`/`rejected`/`needs-review` user status.
Do not modify the resume, research, tracker, or unselected roles. Separate validation outcome from user
status: passing validation never automatically accepts a suggestion.

Preserve a user status only when the suggestion ID and revision, linked requirements, and cited source
content are unchanged. Otherwise reset to `needs-review` and show the reason. Keep the previous revision
for review. Prepare all output before replacement and preserve notes with the existing marker convention.

## 3. Validation before rewriting

Reject broken references, missing required fields, and unsupported exact source claims. Flag proposed
names, numbers, durations, technologies, responsibilities, length increases, and new quantitative language
for review when not supported by cited input. Simple lexical checks do not establish semantic truth.
Each concrete suggestion claim must reference evidence; show unresolved claims and questions in Markdown.

## 4. Bounded corrections

Correct only structural or evidence failures. Default to one rewrite, allow zero, and cap at two.
One monotonic deadline covers the initial call and all corrections; each subprocess receives only the
remaining time. Send validation errors and the minimum necessary evidence in a correction request.
Never use a model's self-score as acceptance or claim a token-cost cap without provider usage data.

Persist each returned response as raw text before parsing, plus parsed JSON when available. Exhausted
retries or time retain the last result and validation errors as `needs-review`; invalid JSON remains an
inspectable raw artifact, never a successfully validated suggestion. Do not alter previously accepted
state on a failed generation.

## Acceptance checks

Use fictional offline fixtures and mocked providers for selected-job isolation, duplicate IDs, missing or
ambiguous originals, unsupported claims, source changes, approval invalidation, unchanged-status retention,
invalid JSON, retry limits, and a shared timeout. Snapshot original input/research/tracker bytes and assert
they remain unchanged. Run the full unit suite after each implementation step and maintain both languages.
Live evaluation remains an explicit opt-in command. No tailoring CLI is available in v0.2.
