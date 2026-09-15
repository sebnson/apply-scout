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
