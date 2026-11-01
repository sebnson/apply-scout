# Quality evaluation

**English** · [한국어](../ko/quality-evaluation.md)

Run the six fictional cases without provider calls:

```sh
python3 -m apply_scout evaluate
python3 -m unittest discover -s tests -v
```

Fixtures live in `tests/fixtures/quality/`. Each contains `profile.md`, `sources.md`, extracted
`posting.json`, independent conditions in `expected.json`, and an offline `response.json`. All people,
companies, experience, and openings are fictional; URLs use `example.com`.

| Case | Constraint |
|---|---|
| required-gap | An explicit onsite conflict prevents a high match |
| missing-experience | Undocumented Kubernetes experience stays unknown |
| preferred-gap | An explicitly missing preferred skill is not a required conflict |
| partial-evidence | A prototype supports partial fulfillment, not proven production operations |
| unsupported-claims | No invented technology, numbers, or leadership responsibilities in evidence |
| unclassified | Unknown importance produces a visible warning |

The evaluator checks the v2 schema subset and runtime consistency, requirement coverage, importance,
allowed assessments and overall matches, posting excerpts, input file/section excerpts, and forbidden
claims. Fixture requirement labels identify requirements; preserve them when generating fixture responses.
Evidence details in these controlled cases must be short verbatim excerpts. This detects unsupported
additions without claiming that exact-text matching can judge arbitrary paraphrases or real-world fit.
Full responses are not golden assertions: summaries and explanations may vary. The renderer's separate
regression tests cover Markdown output, old v1 data, application status, and user notes.

Evaluate saved responses with:

```sh
python3 -m apply_scout evaluate --responses output/quality-responses
```

Use `<fixture>.json` or `<fixture>.<run>.json` names, for example `partial-evidence.1.json`.
Every case must have a response. Reports include the exact fixture, failed rule, JSON path, and message.
Exit status is 0 for a passing suite and 1 for failures. Repeated runs report distinct valid requirement
structures (labels, importance, assessment, evidence count); variation is an observation, not an automatic
quality failure. Missing or invalid JSON responses fail the evaluation.

See also the [research contract](research-contract.md). Offline tests never call a paid provider.

## Record before and after results

```sh
python3 -m apply_scout evaluate --result output/quality-before.json
# Change the runtime instructions or schema, then evaluate new saved responses:
python3 -m apply_scout evaluate --responses output/quality-after-responses --result output/quality-after.json
```

Reports record the evaluation time, `evaluator_instruction_hash`, and each valid response's `run`
metadata. The evaluator hash describes the current instructions/schema; a response may have been
produced under an earlier hash. Compare failures and structural variation in the two reports when
preparing a pull request. Rechecking bundled offline responses tests the evaluator and regressions;
it does not measure the effect of a new prompt on a model. Use newly generated responses for that.
Do not commit private `inputs/` or `output/` directories.

## Explicit live provider evaluation

```sh
python3 -m apply_scout evaluate-live --agent codex --runs 2 --output output/quality-before
python3 -m apply_scout evaluate-live --agent claude --runs 2 --output output/quality-after
```

This command may incur provider charges. It calls the selected CLI once per fixture per repetition
(six calls by default). Compare the same agent, configured model, repetition count, and fixtures when
isolating a prompt change; the two agents above illustrate alternatives. `--runs` accepts 1–10;
`--timeout` defaults to 900 seconds **per call**, not per suite. Calls run sequentially without retries.
The CLI uses its configured model, so record that model and CLI version in the pull request separately.

Only fictional documents and the extracted posting are supplied, without `expected.json` or saved
responses. Web search is disabled in the provider command, and the prompt identifies supplied fictional
data instead of claiming current job research. The output directory must be new. It contains each parsed
response, raw provider text when returned, and `evaluation.json`. Invalid JSON, contract errors, and
provider failures appear as failed cases; completed cases are saved after each call. Normal research
still validates before writing any report. Unit tests cover this path using mocks, never real paid calls.

Codex explicitly sets `web_search="disabled"` using its [configuration override](https://developers.openai.com/codex/config-reference/); Claude receives an empty built-in tool list.
