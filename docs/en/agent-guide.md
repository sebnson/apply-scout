# Agent guide

**English** · [한국어](../ko/agent-guide.md)

`AGENTS.md` and `CLAUDE.md` at the repository root are the entry points discovered by Codex and Claude Code.
This document explains the same workflow for contributors and users.

## Development

Use Python 3.10 or later and the standard library. After behavioral changes, run:

```sh
python3 -m unittest discover -s tests -v
```

## Job research

When asked to research jobs, follow [the shared research instructions](research-instructions.md).
Read `inputs/profile.md`, `inputs/sources.md`, and optional portfolio and experience files.

```sh
# Inspect the complete prompt and schema
python3 -m apply_scout prompt
# Render after saving valid research to output/research.json
python3 -m apply_scout render output/research.json
```

Do not invent job postings or claim live research when browsing is unavailable.
Preserve user notes and the existing output contract. Never commit personal inputs or generated
research from the default private folders.
