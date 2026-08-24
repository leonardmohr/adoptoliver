# Oliver's adoption page

A bilingual single page. Visitors on a Spanish-language browser get Spanish,
everyone else gets English, and a switch in the top-right corner overrides it.

## Changing the words

**All copy lives in `src/content.json`.** Nothing else needs touching. Each entry
holds both languages together, so you can see them side by side:

```json
"scene.4.label": { "en": "He follows", "es": "Los sigue" },
```

Edit it, then run:

```bash
python3 build.py
```

That regenerates `site/index.html` and `dist/oliver-artifact.html`.

The build refuses to finish if a key is missing a language, so the two can't
quietly drift apart the way they used to.

Values may contain simple inline HTML — `<em>`, `<strong>` — and several do.

## The files

| Path | What it is |
|---|---|
| `src/content.json` | **Every word on the page**, English and Spanish |
| `src/template.html` | Structure, styling and behaviour. Carries no prose |
| `src/scenes/01..08.svg` | The eight line drawings in the scroll sequence |
| `assets/inline/` | Compressed media the Artifact embeds |
| `site/` | The deployable folder — drag it to any static host |
| `dist/oliver-artifact.html` | One self-contained file, for publishing as an Artifact |
| `build.py` | Builds both outputs |

`site/index.html` and `dist/` are **generated**. Edits there are overwritten on
the next build — change `src/` instead.

`site/media/` holds the web-sized photos and video and is not regenerated.
The camera originals (`IMG_*`) and `SVG Line Drawings/` are never touched.

## Placeholders in the template

| Placeholder | Becomes |
|---|---|
| `{{t:key}}` | Both languages, toggled by CSS |
| `attr="{{a:key}}"` | `attr="English" data-es-…="Spanish"` |
| `{{en:key}}` | English only — used in `<head>`, which crawlers read before any script runs |
| `{{json:key}}` | A `{"en":…,"es":…}` object, for feeding copy to the page's JavaScript |
| `{{svg:n}}` | Inlines `src/scenes/0n.svg` |

When a key's two languages are identical, the build emits the text once rather
than a redundant pair.

## Deploying

Drag the `site` folder onto Netlify Drop, Cloudflare Pages or GitHub Pages.
There is no server component and nothing to configure.

## Notes

- `og:title` and `og:description` stay English. Link previews in WhatsApp and
  Facebook are generated from static HTML before any script runs, so they can't
  follow the visitor's language.
- `?lang=es` forces Spanish and `?lang=en` forces English, whatever the browser
  prefers — handy for sending someone a specific version.
- The page still reads correctly with JavaScript switched off; it falls back to
  English.
# adoptoliver
