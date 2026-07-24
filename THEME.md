# Theme record

- Theme: `tabi`
- Snapshot commit: `abfd890f05957543bab49dc51f0293f986b45fb1`
- Snapshot date: 2026-07-20
- Compatibility note: this revision includes tabi's Zola 0.22 configuration
  migration (`9a09df`); the older v4.1.0 release does not.
- Upstream: <https://github.com/welpo/tabi>
- License: MIT; see `themes/tabi/LICENSE`
- Vendoring date: 2026-07-24

The vendored snapshot contains the theme runtime directories and its license,
without nested Git metadata or demo content. The optional unminified
`webmention.js` development copy is omitted; the runtime minified file remains.

AMB-specific templates, styles, and scripts live outside `themes/tabi/` so a
future theme update can be reviewed as a discrete replacement.
