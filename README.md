# arabic-l10n-qa

A small, dependency-free linter for **Arabic localization files** in JSON,
gettext PO, iOS `.strings`, Java `.properties`, CSV/TSV and YAML. It catches the
mistakes that translators and machine translation pipelines make most often:
broken placeholders, dropped HTML tags, ASCII punctuation inside Arabic prose,
embedded bidi control characters, mixed Arabic/Latin text with no space, and
key drift between the source and the Arabic file.

It runs offline, in CI, or as a pre-commit hook. No network, no API keys, and no
required external packages (YAML support uses `PyYAML` only if you install it).

## Why

Arabic is one of the highest-volume localization targets and one of the easiest
to break silently. A translation can look fine in a JSON diff and still ship with
`{name}` missing, a broken `<b>` tag, a `?` instead of `؟`, or an invisible
RTL/LTR override that scrambles the surrounding UI. This tool fails the build
before that happens.

## Install

```bash
pipx install .
# or
python -m pip install .
```

Requires Python 3.9+. There are no runtime dependencies.

## Use

Compare an Arabic file against its English source:

```bash
arabic-l10n-qa examples/ar.json --source examples/en.json
```

Output:

```text
WARNING (2)
  app.brand: [untranslated.identical] target is identical to source
  app.greeting: [punctuation.ascii] ASCII ',' found in Arabic text; prefer the Arabic comma (U+060C)

INFO (1)
  app.notfound: [typography.ellipsis] ASCII '...' found; prefer the ellipsis character

Summary: 0 error(s), 2 warning(s), 1 info
```

Lint a single Arabic file with no source:

```bash
arabic-l10n-qa examples/ar.json
```

Emit JSON for dashboards, or GitHub Actions annotations:

```bash
arabic-l10n-qa examples/ar.json -s examples/en.json -f json
arabic-l10n-qa examples/ar.json -s examples/en.json -f github
```

Fail the build on warnings too:

```bash
arabic-l10n-qa examples/ar.json -s examples/en.json --strict
```

Brand names and symbols that legitimately stay untranslated:

```bash
arabic-l10n-qa ar.json -s en.json --ignore-untranslated LocalizationHub --ignore-untranslated OK
```

Lint a gettext catalog directly — no second file needed, because the English
source is already in the `msgid`:

```bash
arabic-l10n-qa examples/ar.po
```

```text
ERROR (1)
  Read our <b>terms</b> at https://example.com/terms: [html.mismatch] html tags differ: source=[('b', 2)] target=[]

Summary: 1 error(s), 0 warning(s), 0 info
```

## Formats

| Extension | Format | Source comparison |
| --- | --- | --- |
| `.json`, `.jsonc` | JSON (nested keys are flattened to `a.b.c`) | via `--source` |
| `.po`, `.pot` | gettext | **embedded** in `msgid`, no `--source` needed |
| `.strings`, `.stringsdict` | iOS / macOS | via `--source` |
| `.properties` | Java | via `--source` |
| `.csv`, `.tsv` | two-column `key,value` | via `--source` |
| `.yaml`, `.yml` | YAML (requires `pip install PyYAML`) | via `--source` |

The format is chosen from the file extension. Passing an unsupported type exits
with code `2` and lists what is supported.

## Checks

| Code | Severity | What it finds |
| --- | --- | --- |
| `placeholder.mismatch` | error | `{name}`, `%s`, `%1$s`, `$TOTAL$` counts differ from the source |
| `html.mismatch` | error | `<b>` / `<a>` / `<br>` tags differ from the source |
| `url.mismatch` | error | URLs differ from the source |
| `email.mismatch` | error | E-mail addresses differ from the source |
| `missing.key` | error | Key in the source but not in the Arabic file |
| `missing.translation` | error | Key present but with no value |
| `empty.translation` | error | Value is empty or whitespace only |
| `type.invalid` | error | Value is not a string |
| `untranslated.identical` | warning | Arabic value is byte-identical to the source |
| `whitespace.edge` | warning | Leading/trailing whitespace differs from the source |
| `digits.missing` | warning | Source has digits, translation has none |
| `punctuation.ascii` | warning | ASCII `,` `;` `?` inside Arabic prose |
| `bidi.control_chars` | warning | Invisible U+202A–U+202E / U+2066–U+2069 / LRM / RLM |
| `script.mixed_spacing` | warning | `عربيLatin` with no separating space |
| `extra.key` | warning | Key in the Arabic file but not in the source |
| `arabic.tatweel` | info | Repeated tatweel (kashida) `ـ` characters |
| `typography.ellipsis` | info | ASCII `...` instead of `…` |

Placeholders, URLs, e-mails, and markup are stripped before the Arabic prose
checks run, so the linter does not false-positive on `%s` or on a URL.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No error-level issues (and no lower issues with `--strict`) |
| `1` | Issues found |
| `2` | Bad input, missing file, or invalid JSON |

## CI

```yaml
- name: Lint Arabic localization
  run: |
    python -m pip install .
    arabic-l10n-qa locales/ar.json -s locales/en.json -f github --strict
```

## GitHub Action

Add the linter to any workflow without a setup step:

```yaml
- uses: maybad-alr/arabic-l10n-qa@main
  with:
    target: locales/ar.json
    source: locales/en.json
    strict: "true"
```

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `target` | yes | — | Arabic localization file to lint |
| `source` | no | `""` | Source-language file to compare against |
| `strict` | no | `false` | Fail on warnings and info as well as errors |
| `format` | no | `github` | `text`, `json` or `github` |

## Status

Early, focused, and intentionally small. The rule set is the part that matters,
so contributions that add a real-world Arabic QA rule (with a test) are the most
welcome.

## License

MIT
