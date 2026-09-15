# Architecture and roadmap

**English** · [한국어](../ko/architecture.md)

## Data flow

1. `__main__.py` validates the required Markdown inputs, reads optional documents, and builds the shared research prompt.
2. Codex or Claude CLI researches the web and responds using the same JSON contract in `schema.py`.
3. `core.py` validates the response, normalizes URLs, merges previous state, sorts deadlines, and renders Markdown.
4. The user edits status and notes in the tracker and the personal notes section in each analysis.
5. Subsequent runs preserve those edits and retain openings that were not rechecked in a separate section.

The project uses only the Python standard library. Run it from a cloned repository; package distribution
is not available yet. Each CLI uses the user's configured model. Profile content is passed through stdin.
The renderer writes validated results; the research agent is not asked to edit reports.

## v0.1 scope

- Markdown inputs and outputs, with Codex and Claude CLI integration
- Evidence-based assessment contract, deadline ordering, and target dates with a preparation buffer
- Preservation of application status, notes, and previously discovered openings
- Per-source research failure records
- Offline examples and regression tests

## Next steps

- Integration checks for both providers against real public recruiting sites
- A local interface with file uploads and a Run button
- A review step for the essential requirements extracted from the profile
- Scheduling based on weekly application capacity and estimated preparation time
- Applicant tracking system (ATS) adapters that retain job identity when a posting URL changes
- Stronger evidence checks and reliable site-specific collectors
- Cancellation, progress reporting, concurrent-run locks, and transactions covering multiple output files
- Multilingual generated reports; English and Korean documentation and translated examples are available

## Known limitations

Each file is written to a temporary file before being replaced. The entire set of files is not updated in
one transaction, so a disk error or forced termination can leave a partially updated output folder.
Do not run multiple processes against the same output folder.

The program detects duplicate URLs after removing tracking parameters. The AI handles duplicates across
different recruiting platforms. Weekly application limits are not scheduled automatically. Time zone
information remains in the source notes; sorting uses calendar dates.
