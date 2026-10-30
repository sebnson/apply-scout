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
