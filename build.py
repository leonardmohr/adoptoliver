#!/usr/bin/env python3
"""
Builds Oliver's adoption page from src/ into two targets:

    docs/index.html          the deployable page (media by relative path)
    dist/oliver-artifact.html  one self-contained file, for publishing as an Artifact

Edit copy in src/content.json and structure in src/template.html, then run:

    python3 build.py

Placeholders understood in src/template.html:

    {{t:key}}     text position   -> <span class="en">EN</span><span class="es">ES</span>
    attr="{{a:key}}"              -> attr="EN" data-es-XXX="ES"
    {{en:key}}    English only    -> EN            (used in <head>: crawlers read
                                                    static HTML; JS localises at runtime)
    {{json:key}}  -> {"en":"…","es":"…"}           (feeds copy into the page's JS)
    {{svg:n}}     -> inlines src/scenes/0n.svg
"""
import base64, json, os, re, sys, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
def path(*p): return os.path.join(ROOT, *p)

# Attribute -> the twin the page's JS looks for. Must match the PAIRS table in
# the template's language module; verified below so the two cannot drift.
TWIN = {"alt": "data-es-alt", "aria-label": "data-es-aria",
        "data-label": "data-es-label", "data-cap": "data-es-cap",
        "href": "data-es-href"}

# keys the build itself consumes rather than placing via a placeholder
BUILD_KEYS = {"meta.artifactTitle"}

ARTIFACT_MAX = 13 * 1024 * 1024      # cap is 16 MB; leave headroom

errors, warnings = [], []
def fail(m): errors.append(m)
def warn(m): warnings.append(m)


def load():
    content = json.load(open(path("src/content.json"), encoding="utf-8"),
                        object_pairs_hook=collections.OrderedDict)
    for k, v in content.items():
        for lang in ("en", "es"):
            if not v.get(lang, "").strip():
                fail("content.json: %s is missing a non-empty '%s'" % (k, lang))
    template = open(path("src/template.html"), encoding="utf-8").read()
    scenes = {n: open(path("src/scenes/%02d.svg" % n), encoding="utf-8").read()
              for n in range(1, 9)}
    return content, template, scenes


def render(template, content, scenes):
    """Expand every placeholder. Output is the dual-language markup the page's
    CSS toggle and language module already expect."""
    used = set()

    def get(key, where):
        used.add(key)
        if key not in content:
            fail("%s refers to missing key: %s" % (where, key))
            return {"en": "", "es": ""}
        return content[key]

    # attributes first, so their {{a:}} tokens aren't caught by the text pass
    def sub_attr(m):
        attr, key = m.group(1), m.group(2)
        v = get(key, "attribute %s" % attr)
        if attr not in TWIN:
            fail("no translation twin defined for attribute '%s' (key %s)" % (attr, key))
            return m.group(0)
        if '"' in v["en"] or '"' in v["es"]:
            fail("%s contains a double quote and cannot sit in an attribute" % key)
        return '%s="%s" %s="%s"' % (attr, v["en"], TWIN[attr], v["es"])
    out = re.sub(r'([\w-]+)="\{\{a:([\w.]+)\}\}"', sub_attr, template)

    def sub_text(m):
        v = get(m.group(1), "text")
        # identical in both languages -> no need for a twin the CSS would toggle
        if v["en"] == v["es"]:
            return v["en"]
        return '<span class="en">%s</span><span class="es">%s</span>' % (v["en"], v["es"])
    out = re.sub(r'\{\{t:([\w.]+)\}\}', sub_text, out)
    out = re.sub(r'\{\{en:([\w.]+)\}\}',
                 lambda m: get(m.group(1), "english-only")["en"], out)
    out = re.sub(r'\{\{json:([\w.]+)\}\}',
                 lambda m: json.dumps(dict(get(m.group(1), "json")), ensure_ascii=False), out)
    out = re.sub(r'\{\{svg:(\d)\}\}', lambda m: scenes[int(m.group(1))], out)

    leftover = re.findall(r'\{\{[a-z]+:[\w.]+\}\}', out)
    if leftover:
        fail("unexpanded placeholders: %s" % sorted(set(leftover)))
    for k in content:
        if k not in used and k not in BUILD_KEYS:
            warn("content.json key never used: %s" % k)

    # the emitted twins must be the ones the runtime looks for
    pairs = re.search(r'var PAIRS = \[(.*?)\];', out, re.S)
    if pairs:
        known = set(re.findall(r"\['([\w-]+)',", pairs.group(1)))
        for attr in TWIN:
            if attr not in known:
                fail("template's PAIRS table does not handle '%s'" % attr)
    else:
        warn("could not find the PAIRS table to cross-check attribute twins")
    return out


def data_uri(p):
    mime = {"webp": "image/webp", "jpg": "image/jpeg", "mp4": "video/mp4"}[p.rsplit(".", 1)[1]]
    with open(p, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def to_artifact(html, content):
    """Fold the page into one file: media inlined, <head> hoisted into the body
    (the Artifact wrapper supplies its own <head>)."""
    inline = lambda f: data_uri(path("assets/inline", f))
    web    = lambda f: data_uri(path("docs/media", f))

    style = re.search(r'<style>.*?</style>', html, re.S).group(0)
    fonts = re.search(r'<link rel="stylesheet" href="https://fonts\.googleapis[^>]*>', html).group(0)
    body  = re.search(r'<body>(.*)</body>', html, re.S).group(1)

    def collapse(m):                       # <picture> -> one <img>, single payload
        img  = re.search(r'<img\b[^>]*>', m.group(0)).group(0)
        stem = re.search(r'srcset="media/([\w-]+)\.webp"', m.group(0)).group(1)
        img  = re.sub(r'src="[^"]*"', 'src="%s"' % inline(stem + ".webp"), img)
        return re.sub(r'\s(width|height)="\d+"', '', img)
    body, n_pic = re.subn(r'<picture>.*?</picture>', collapse, body, flags=re.S)

    body, n_bg = re.subn(r'url\(media/(thumb-\d+)\.jpg\)',
                         lambda m: "url(%s)" % web(m.group(1) + ".webp"), body)
    body, n_th = re.subn(r'(<img src=")media/(thumb-\d+)\.jpg(")',
                         lambda m: m.group(1) + web(m.group(2) + ".webp") + m.group(3), body)

    def video(m):
        tag, stem = m.group(0), m.group(1)
        tag = tag.replace('poster="media/%s-poster.jpg"' % stem,
                          'poster="%s"' % inline(stem + "-poster.webp"))
        tag = tag.replace(' preload="none"', ' preload="metadata"')
        return tag.replace("></video>", ' src="%s"></video>' % inline(stem + ".mp4"))
    body, n_vid = re.subn(r'<video class="media"[^>]*poster="media/(\w+)-poster\.jpg"[^>]*></video>',
                          video, body)
    # the on-demand loader has nothing left to fetch
    body = re.sub(r"var vsrc\s*=\s*\{[^}]*\};",
                  "var vsrc = {};   /* sources are inlined in this build */", body)

    if (n_pic, n_vid) != (5, 3):           # 1 hero + 4 carousel photos, 3 videos
        fail("artifact: expected 5 pictures and 3 videos, got %d and %d" % (n_pic, n_vid))
    left = sorted(set(re.findall(r"media/[\w.-]+", body)))
    if left:
        fail("artifact still references files: %s" % left)

    title = content["meta.artifactTitle"]["en"]
    return "<title>%s</title>\n%s\n%s\n%s\n" % (title, fonts, style, body.strip()), \
           (n_pic, n_bg, n_th, n_vid)


def main():
    content, template, scenes = load()
    html = render(template, content, scenes)

    artifact, counts = to_artifact(html, content)
    if len(artifact.encode()) > ARTIFACT_MAX:
        fail("artifact is %.2f MB, over the %.0f MB build limit"
             % (len(artifact.encode()) / 1048576, ARTIFACT_MAX / 1048576))

    for w in warnings: print("  warning: %s" % w)
    if errors:
        for e in errors: print("  ERROR: %s" % e, file=sys.stderr)
        sys.exit(1)

    banner = "<!-- GENERATED by build.py - edit src/content.json and src/template.html, not this file -->\n"
    html = html.replace("<!doctype html>\n", "<!doctype html>\n" + banner, 1)
    os.makedirs(path("dist"), exist_ok=True)
    open(path("docs/index.html"), "w", encoding="utf-8").write(html)
    open(path("dist/oliver-artifact.html"), "w", encoding="utf-8").write(artifact)

    print("  content.json   %d keys" % len(content))
    print("  docs/index.html          %6.1f KB" % (len(html.encode()) / 1024))
    print("  dist/oliver-artifact.html %5.2f MB   (%d photos, %d backdrops, %d thumbs, %d videos)"
          % (len(artifact.encode()) / 1048576, counts[0], counts[1], counts[2], counts[3]))


if __name__ == "__main__":
    main()
