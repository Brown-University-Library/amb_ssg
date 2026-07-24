# AMB Zola site working notes

Read `README.md` before changing or rebuilding the site.

## Project rules

- This repository intentionally tracks both the Zola source and the matching
  generated `public/` site.
- Never edit `public/` by hand. Run `zola build` to regenerate it.
- Preview with the documented `zola serve --output-dir .work/serve` command so
  local output remains separate from `public/`.
- Keep legacy conversion inputs and preservation image masters outside this
  repository.
- The normalized public collection source is
  `data/collection_records.json`.
- Artwork Markdown under `content/collection/` and browser search data under
  `static/search/` are generated from that normalized source.
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

## Useful paths

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

## Before handing off changes

1. Keep all coordinated collection representations synchronized.
2. Run `zola check` with Zola 0.22.1.
3. Run `zola build`.
4. Review source and `public/` together.
