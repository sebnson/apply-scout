# Contributing

**English** · [한국어](../ko/contributing.md)

Bug fixes, reproducible site research examples, and documentation improvements are welcome.

1. Prepare a reproducible issue or a narrowly scoped change.
2. Use Python 3.10 or later and the standard library.
3. When changing state preservation, deadlines, or URL handling, add a test for the relevant failure case.
4. Run `python3 -m unittest discover -s tests -v`.
5. Describe the problem, resulting behavior, and validation in your pull request.

Do not include real resumes, personal contact details, or credentials in examples, issues, or tests.
Clearly label fictional openings and use the example.com domain.

## Documentation languages

Maintain corresponding documents under `docs/en/` and `docs/ko/`, including the translated examples.
Preserve relative links and language-switch links. Keep commands, filenames, schema keys, status values,
and preservation markers compatible with the current implementation.

`docs/research-instructions.md` is the runtime prompt source. Keep its instructions aligned with both
translated research guides. `AGENTS.md` and `CLAUDE.md` remain the files discovered by the AI tools.
The default templates and renderer still use Korean. Do not describe a translated example as an
automatically generated English report until an English rendering mode is implemented.
