# Apply Scout

For development, use Python 3.10+ and the standard library. Run
`python3 -m unittest discover -s tests -v` after behavioral changes.

When the user asks to research jobs, follow `docs/research-instructions.md`.
Read `inputs/profile.md`, `inputs/sources.md`, and optional portfolio/experience files.
Use `python3 -m apply_scout prompt` to obtain the complete prompt and schema.
Save valid research to `output/research.json`, then run
`python3 -m apply_scout render output/research.json`.
Do not invent job postings or claim live research when browsing is unavailable.
Preserve user notes and support the existing output contract.
Never commit personal inputs or generated research from the default private folders.

## Documentation

Maintain paired Markdown documentation under `docs/en/` and `docs/ko/`.
Keep translations, relative links, and language navigation in sync. The runtime
research prompt remains `docs/research-instructions.md`; align both localized guides
with it. English examples are documentation previews, not an English rendering mode.

Human-readable agent guides: [English](docs/en/agent-guide.md) · [한국어](docs/ko/agent-guide.md).
