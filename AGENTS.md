# AGENTS.md — Repository Agent Instructions (Source of Truth)

This file defines the canonical coding directives for this repository.

If repository-local instruction files such as Copilot, IDE, or contributor rules conflict with this file, follow this file and treat those files as stale. This file does not supersede system, developer, or user instructions. Instructions inherited from a parent directory continue to apply except where this file gives more specific direction for this repository.

This repository is currently a Zola static-site project, not a Django application. The general Python and Django guidance below is retained for reuse, but it applies only where it fits the files and architecture actually present. The project-specific commands and rules in [Agent project index](#agent-project-index) take precedence over generic examples.


## Table of contents

- [Project basics](#project-basics)
- [How to run code](#how-to-run-code)
- [Coding directives (Python)](#coding-directives-python)
- [Django architecture conventions](#django-architecture-conventions)
- [Front-end change guidance](#front-end-change-guidance)
- [Tests](#tests)
- [Change workflow expectations](#change-workflow-expectations)
- [If instructions are missing or ambiguous](#if-instructions-are-missing-or-ambiguous)
- [Agent project index](#agent-project-index)


## Project basics

- Project type: Zola static site with Markdown content, Tera templates, CSS, browser JavaScript, and Python maintenance scripts
- Site builder: Zola 0.22.1
- Python compatibility target for new or modified code: Python 3.12 unless a future `pyproject.toml` specifies a different version; this version is not currently pinned, and existing scripts require Python 3.11 or newer
- Python execution tool: `uv`
- JavaScript test runtime: Node.js 18 or newer
- This repository currently has no `pyproject.toml`, `uv.lock`, `.python-version`, `ruff.toml`, `run_tests.py`, `manage.py`, or Django application.
- Project-root is the directory containing this file (and `.git/`, and `.gitignore`).


## How to run code

- Assume user is in the project-root directory.
- Do not invoke `python` or `python3` directly for repository scripts; run Python scripts through `uv`.
- Run a Python script via: `uv run ./path_to_script.py ARGS`
- Run the browser-search test via: `node scripts/test_search.js`
- Run Zola commands directly, as documented in `README.md`.
- The generic `uv run ./run_tests.py` and `uv run ./manage.py THE-COMMAND` conventions do not apply unless those files are deliberately added later.


## Coding directives (Python)

These directives apply when creating or modifying Python. Do not rewrite otherwise unrelated working scripts solely to make old code conform.

### Type hints and imports

- Use Python 3.12 type hints everywhere (functions and important variables). (Unless a `pyproject.toml` specifies a different version.)
- Prefer builtin generics (e.g., `list[str]`, `dict[str, int]`) over `typing.List` / `typing.Dict`.
- Prefer PEP 604 unions (e.g., `str | None`) over `Optional[str]`.
- Avoid `typing` and `annotations` imports unless strictly necessary.

### Script structure

- Structure runnable modules as:
  - `def main() -> None: ...`
  - `if __name__ == '__main__': main()`
- Keep `main()` simple: parse args / orchestrate calls only.
- Put real logic into top-level helper functions and modules (no nested function definitions).
- Rarely use more than three levels of hierarchy: main() can call helper_A() which can call helper_B() which can, if necessary, call helper_C() -- but that's it.

### Functions and control flow

- Prefer single-return functions (use local variables and a final return).
- Do not define functions inside other functions.
- Favor clarity and explicitness over cleverness.

### Logging

- When adding a log statement, when possible, format variable values as a label, followed by a comma and a space, with the value enclosed in double backticks.
- Prefer a label that matches the variable name. For example: ```log.debug(f'branch_and_commit, ``{branch_and_commit}``')```

### HTTP and networking

- If Python HTTP support and dependency metadata are deliberately introduced, use `httpx` for HTTP calls.
- Do not introduce alternate HTTP libraries (e.g., `requests`, `aiohttp`) unless the repository already depends on them and there is a documented reason.

### Docstrings

- Use triple-quoted docstrings.
- Write docstrings in present tense, with triple-quotes on their own lines.
  - Good: 
    ```
    """
    Parses ...
    """
    ```
  - Avoid: `"""Parse ..."""`
- The last line of non-test function-docstrings should be: `Called by: the_caller_function()` (or, if in another class/module, `Called by: module.Class.the_caller_function()`)
- Start test-function docstring-text with "Checks..."
- For header-comments, in functions, start the comment with two hashes (e.g., `## does this`).

### Additional coding directives

- If a repository-root `ruff.toml` is added, inspect it for additional directives such as `max-line-length` and `quote-style`.

### Markdown formatting

- Do not use hard line-breaks in markdown files; let paragraphs wrap naturally.
- When creating a Markdown file with more than three top-level `##` headings, add a table of contents near the top with links to those `##` headings.


## Django architecture conventions

This section is inactive because the repository has no Django application. Apply it only if the user explicitly introduces Django here.

### View-layer responsibilities

- `project/app/views.py` should contain **only** view functions that directly handle URL endpoints.
- Every view function in `project/app/views.py` should correspond to an entry in `project/config/urls.py`.
- Views should act as **manager/orchestrator** functions:
  - Parse request input (query params, POST body, files)
  - Perform minimal validation and shaping of inputs
  - Delegate substantive work to modules under `project/app/lib/`
  - Convert returned results into the appropriate `HttpResponse` (HTML, JSON, redirects)

### Business logic placement

- Put domain logic, integrations, and reusable operations in `project/app/lib/` (not in `views.py`).
- If multiple endpoints share logic, move that shared logic into `project/app/lib/` and keep each view thin.
- Prefer pure, testable functions in `project/app/lib/` that accept plain Python values (not Django request objects)
  unless passing the request is necessary for a narrow, well-justified reason.

### Imports and dependencies

- `views.py` should primarily import:
  - Django primitives (`HttpRequest`, `HttpResponse`, `render`, `redirect`, etc.)
  - The minimal set of functions/classes from `project/app/lib/` needed for each endpoint
- Avoid creating a secondary abstraction layer inside `views.py` (no view-helper utilities); place helpers in `project/app/lib/`.


## Front-end change guidance

- When front-end changes are required, use JavaScript only where it is truly required.
- Prefer HTML, Zola/Tera templates, and CSS for browser-facing changes. Use Python when generated source needs to change.


## Tests

- Use the standard library `unittest` framework (not pytest) for non-Django projects.
- Use Django's test framework for Django projects.
- Preserve and extend the repository's existing script-level checks where they cover the changed behavior; this project currently uses `scripts/validate.py` and `scripts/test_search.js` rather than a single test runner.
- New behavior should usually come with a focused test covering:
  - the happy path
  - at least one failure / edge case


## Change workflow expectations

When implementing a change (especially from an issue/task):

1. Read relevant surrounding code and match existing conventions.
2. Make the smallest correct change that satisfies the request.
3. Update tests and run the applicable project checks listed under [Before handing off changes](#before-handing-off-changes).
4. If you cannot run tests in your environment, still write/adjust tests and state what you would run.

### Commit messages

- Group related files into logical, focused commits; do not require a separate commit for every file.
- Keep each commit message brief, with no more than ten words.
- Write messages in the present tense so they complete the phrase "This commit..." Begin with a fitting verb such as "Adds," "Implements," or "Updates."


## If instructions are missing or ambiguous

- Do not ask questions unless absolutely necessary to proceed.
- Make reasonable assumptions, state them explicitly, then implement.
- If blocked, provide:
  - what you tried
  - what you found in the repo
  - a concrete next step (command, file to edit, or minimal decision needed)


## Agent project index

Read `README.md` before changing or rebuilding the site.

This section specializes the general directives above for the current AMB Zola repository.

### Project rules

- This repository intentionally tracks both the Zola source and the matching
  generated `public/` site.
- Never edit `public/` by hand. Run `zola build` to regenerate it.
- The experimental relative-link build changes were reverted and are not
  present. The standard production workflow is `zola build`; direct loading of
  `public/index.html` without a server is not currently implemented or
  validated. Do not reintroduce relative-link output post-processing unless
  the user explicitly requests it.
- Preview with the documented `zola serve --output-dir .work/serve` command so
  local output remains separate from `public/`.
- Keep legacy conversion inputs and preservation image masters outside this
  repository.
- The normalized public collection source is
  `data/collection_records.json`.
- Artwork Markdown under `content/collection/` and browser search data under
  `static/search/` are generated from that normalized source. After changing
  the canonical data, run `uv run ./scripts/render_collection.py`; do not edit
  the generated representations independently.
- The importer uses a strict public-field allowlist. Do not replace it with a
  full-row import followed by field deletion.
- Collection search is intentionally limited to artist, title, and
  nationality. Result-card data is stored but not registered as searchable.
- Search controls are connected by stable element IDs. Zola's HTML minimizer
  removes a submit button's redundant `type="submit"` attribute, so do not
  locate that button with a `[type="submit"]` selector. Keep the browser
  initialization coverage in `scripts/test_search.js` and the built-element
  checks in `scripts/validate.py`.
- `static/amb.css` intentionally sets the site typography to 80% of tabi's
  default sizes, mirroring tabi's 600px and 960px root-font breakpoints and
  scaling the viewport terms in AMB's responsive headings. Recheck those
  overrides if the vendored theme changes its typography breakpoints.
- Do not add absolute filesystem paths to source, documentation, content,
  templates, scripts, or generated output.
- The expected collection size is 151 records.
- The theme is the vendored `tabi` commit recorded in `THEME.md`. Keep local
  AMB work outside `themes/tabi/`.

### Useful paths

- `zola.toml` — site and theme settings.
- `content/` — narrative pages and generated artwork pages.
- `data/collection_records.json` — normalized, public collection data.
- `assets/` — source images retained for repeatable derivative generation.
- `assets/image-derivatives.json` — content-based image reproducibility
  manifest.
- `static/images/` — web-ready image derivatives.
- `templates/` — AMB-owned layouts.
- `static/js/collection-search-core.js` — testable search/index logic.
- `static/js/collection-search.js` — browser search interface.
- `scripts/test_search.js` — search-scope, substring, and ordering checks.
- `scripts/render_collection.py` — regenerates artwork pages and search data.
- `scripts/render_images.py` — regenerates web-ready images.
- `scripts/validate.py` — source or built-site checks.

### Before handing off changes

1. Keep all coordinated collection representations synchronized.
2. Run `uv run ./scripts/check_zola.py`.
3. Run `uv run ./scripts/validate.py source`.
4. Run `node scripts/test_search.js`.
5. Run `zola check`.
6. Run `zola build`.
7. Run `uv run ./scripts/validate.py build public`.
8. Review source and `public/` together.

---
