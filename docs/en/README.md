# Apply Scout

**English** · [한국어](../ko/README.md)

**Your experience in Markdown. Job research with AI. An application plan you can follow.**

Provide your profile and a list of recruiting sites. Codex or Claude Code researches
job openings, then Apply Scout creates a Markdown application tracker and an analysis for each role.

```text
profile.md + portfolio.md (optional) + experience.md (optional) + sources.md
                                  ↓
                           Codex / Claude Code
                                  ↓
                      apply-tracker.md → jobs/*.md
```

**Current version: v0.1.0 / CLI MVP.** A web interface with a Run button is planned.
AI handles research and fit assessment; the program validates results, sorts deadlines, and creates files.

Documentation and translated examples are available in English and Korean. CLI messages and
fixed labels in automatically generated reports are currently Korean. The English report below
is a translated documentation example, not the output of an English rendering mode.

## Preview the results

- [Example application tracker](examples/output/apply-tracker.md)
- [Example profile](examples/inputs/profile.md)
- [Example research data, with Korean text](../../examples/research.json)

All examples use fictional companies and openings. They are not real recruiting information.

## Quick start

Requires Python 3.10 or later. No additional Python packages are needed.
Automatic research requires an installed, authenticated Codex CLI or Claude Code with web search access.
Your AI provider's account usage and billing policies apply.

```sh
git clone https://github.com/sebnson/apply-scout.git
cd apply-scout
python3 -m apply_scout init
```

Write your target role, experience, skills, and preferences in `inputs/profile.md`.
Replace the placeholder URL in `inputs/sources.md` with the actual recruiting sites you want to search.
Portfolio and detailed experience files are optional.

`init` currently creates Korean templates. For English templates, copy the following files
immediately after initialization, before adding personal information:

```sh
cp docs/en/examples/inputs/*.md inputs/
```

Choose one installed and authenticated provider:

```sh
python3 -m apply_scout run --agent codex
python3 -m apply_scout run --agent claude
```

Open `output/apply-tracker.md` when the run finishes. Click a company name to read the analysis
for that opening. Different roles at the same company get separate files.

### Try the output without calling AI

```sh
python3 -m apply_scout render examples/research.json --output output/demo --today 2026-09-15
```

### Run from a Codex or Claude conversation

Open this repository in your tool and ask:

> Follow AGENTS.md and docs/research-instructions.md to research jobs using the profile and
> sites in inputs. Write output/research.json, then use apply_scout render to create the tracker.

To inspect the complete prompt, including the inputs and output schema:

```sh
python3 -m apply_scout prompt
```

## Generated files

```text
output/
  apply-tracker.md     # Openings ordered by deadline, target dates, status, notes
  jobs/<job ID>.md     # Role summary, requirements and evidence, gaps, preparation
  research.json       # Most recent AI research result
  .state.json         # Previous openings and application status
```

- Job IDs are derived from the original posting URL, with tracking parameters removed.
- Closed openings and openings not rechecked in the latest run appear in separate sections.
- Openings without a date distinguish rolling recruitment, no listed deadline, and an unknown deadline.
- The target application date is two days before the deadline by default, or today if that date has passed.
- Check the individual analysis and original posting for the exact closing time and time zone.
- Scheduling by weekly application capacity or estimated preparation time is not implemented yet.

## Keep your application history

Edit the **status and notes columns** in `apply-tracker.md`. Those edits survive subsequent runs.
The program currently recognizes these exact Korean status values when excluding a role from the plan:

| Stored status | Meaning |
|---|---|
| 지원 완료 | Applied |
| 지원 안 함 | Not applying |
| 합격 | Accepted |
| 불합격 | Rejected |

Keep the table columns and posting links intact. Write `&#124;` for a literal `|` inside a note.

The **personal notes** section in the tracker and each analysis is also preserved. Write between the
HTML comment markers. Other edits to generated sections are replaced on the next run.
Deleting `output/.state.json` removes the stored history needed to retain older openings.
Run only one process against an output folder at a time.

```sh
python3 -m apply_scout run --agent codex --limit 10 --buffer-days 3 --timeout 900
# Recalculate the plan from existing research without another AI call
python3 -m apply_scout render output/research.json
```

## Fit assessments

| Stored assessment | English meaning | Criteria |
|---|---|---|
| 높음 | High | Specific experience provides substantial evidence for the main requirements |
| 보통 | Moderate | Relevant experience exists, but some requirements need clarification or improvement |
| 낮음 | Low | Evidence shows a conflict with an explicit essential requirement |
| 판단 보류 | Undetermined | The posting or profile does not provide enough information |

Missing information is not treated as proof of missing experience. Assessments require evidence from
the original posting and the relevant profile file and section. They are AI judgments, not hiring predictions.

## Research limits and personal information

Sites that require login or CAPTCHA are recorded with the reason access was limited.
The tool does not submit applications. It does not guarantee complete coverage or correct assessments.
Your selected AI provider processes the input documents; include only information you are comfortable sharing.
The default `inputs/` and `output/` folders are excluded from Git. Exclude custom folders yourself.
The program checks structure, dates, and URLs; factual accuracy still requires checking the original sources.

Codex research uses read-only execution. Claude research is requested with WebSearch and WebFetch tools.
Availability depends on authentication and the provider environment. Command construction and response
handling are tested; full live-site research with authenticated providers has not yet been verified.

## Development

```sh
python3 -m unittest discover -s tests -v
```

- [Architecture and roadmap](architecture.md)
- [Contributing](contributing.md)
- [Shared research instructions](research-instructions.md)
- CLI references: [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive/),
  [Run Claude Code programmatically](https://code.claude.com/docs/en/headless)

## License

[MIT](../../LICENSE) © 2026 sebnson
