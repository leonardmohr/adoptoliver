#!/usr/bin/env python3
"""
Builds a printable one-page flyer, English and Spanish, from the same
src/content.json the website uses.

    python3 flyer.py   ->  dist/flyer-en.pdf, dist/flyer-es.pdf

US Letter, full colour, 300-ish dpi photography. Rendered by headless Chrome,
so no extra Python packages are needed.
"""
import base64, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
def path(*p): return os.path.join(ROOT, *p)

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
QR     = os.path.expanduser("~/Downloads/oliver-qr-pawmodules_2.png")
PHOTO  = path("docs/media/oliver-01-hello.jpg")
# first entry is the lead number, shown larger
WHATSAPP = ["(449) 548-2070", "+1-650-427-9274"]

COPY = {
 "en": {"eyebrow":"Aguascalientes, México",
        "head":"Looking for my<br><em>forever home</em>",
        "blurb":"I am a beautiful, energetic puppy. I love to run, I am learning fast, "
                "and I get along with children and other dogs.",
        "facts":"Details", "ask":"Ask about me on WhatsApp",
        "scan":"Scan for photos,<br>video and my full story",
        "fly":"I am in Aguascalientes, and can fly to California."},
 "es": {"eyebrow":"Aguascalientes, México",
        "head":"Busco mi<br><em>hogar para siempre</em>",
        "blurb":"Soy un cachorro precioso y lleno de energía. Me encanta correr, aprendo "
                "rápido, y me llevo bien con los niños y con otros perros.",
        "facts":"Mis datos", "ask":"Pregunta por mí en WhatsApp",
        "scan":"Escanea para ver fotos,<br>video y mi historia completa",
        "fly":"Estoy en Aguascalientes."},
}
FACTS = ["vital.age", "vital.size", "vital.vaccines", "vital.getsAlong"]


def uri(p):
    ext = p.rsplit(".", 1)[1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}[ext]
    with open(p, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def html(lang, content):
    t = COPY[lang]
    tels = "".join('<p class="tel%s">%s</p>' % ("" if i == 0 else " tel-alt", n)
                   for i, n in enumerate(WHATSAPP))
    rows = "".join(
        '<div class="fact"><dt>%s</dt><dd>%s</dd></div>'
        % (content[k + ".label"][lang], content[k + ".value"][lang]) for k in FACTS)
    return """<!doctype html><html lang="%s"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;1,6..72,400&family=DM+Mono:wght@400;500&display=swap">
<style>
@page{size:letter;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:8.5in;height:11in}
body{
  font-family:"Newsreader",Georgia,serif; color:#14161B; background:#F1EEE7;
  display:flex; flex-direction:column;
  -webkit-print-color-adjust:exact; print-color-adjust:exact;
}
.top{background:#2F6FCE; color:#fff; padding:.42in .5in .38in; position:relative; overflow:hidden}
.top::after{content:"";position:absolute;inset:0;
  background:radial-gradient(9in 6in at 88%% -20%%,rgba(255,214,150,.40),transparent 60%%)}
.top>*{position:relative}
.eyebrow{font-family:"DM Mono",monospace;font-size:8.5pt;letter-spacing:.18em;
  text-transform:uppercase;color:#F3F7FD}
.name{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;font-size:76pt;
  line-height:.84;letter-spacing:-.055em;margin:.06in 0 .10in}
.name .o{color:#F5A04A}
.head{font-family:"Bricolage Grotesque",sans-serif;font-weight:600;font-size:17pt;
  line-height:1.16;letter-spacing:-.02em}
.head em{font-style:italic;color:#F5A04A;font-family:"Newsreader",serif;font-weight:400}

.mid{flex:1;display:flex;gap:.34in;padding:.26in .5in .16in;align-items:center}
.photo{width:3.95in;flex:none;aspect-ratio:4/5;border-radius:.14in;overflow:hidden;background:#0C0E12}
.photo img{width:100%%;height:100%%;object-fit:cover;display:block}
.side{flex:1;display:flex;flex-direction:column;justify-content:center}
.blurb{font-size:12.5pt;line-height:1.5;color:#3E434E}
.facts-t{font-family:"DM Mono",monospace;font-size:8pt;letter-spacing:.16em;
  text-transform:uppercase;color:#A5520C;margin:.24in 0 .10in}
.facts{display:grid;grid-template-columns:1fr 1fr;gap:.13in .18in}
.fact dt{font-family:"DM Mono",monospace;font-size:7.5pt;letter-spacing:.12em;
  text-transform:uppercase;color:#6A7080;margin-bottom:.03in}
.fact dd{font-family:"Bricolage Grotesque",sans-serif;font-weight:600;font-size:12pt}
.fly{margin-top:.26in;padding-top:.19in;font-size:10.5pt;line-height:1.45;color:#3E434E;
  border-top:1px solid #DAD6CC}

.bot{background:#14161B;color:#fff;padding:.26in .5in;display:flex;
  align-items:center;gap:.34in}
.cta{flex:1}
.ask{font-family:"DM Mono",monospace;font-size:8.5pt;letter-spacing:.16em;
  text-transform:uppercase;color:#F5A04A;margin-bottom:.07in}
.tel{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;font-size:25pt;
  letter-spacing:-.02em;line-height:1.16}
.tel-alt{font-size:16.5pt;font-weight:600;color:#D9DCE2;margin-top:.05in}
.qr{display:flex;align-items:center;gap:.16in}
.qr img{width:1.58in;height:1.58in;border-radius:.09in;background:#fff;display:block}
.scan{font-family:"DM Mono",monospace;font-size:7.5pt;line-height:1.5;
  letter-spacing:.06em;color:#A7AAB4;text-align:right}
</style></head><body>
<header class="top">
  <p class="eyebrow">%s</p>
  <h1 class="name"><span class="o">O</span>liver</h1>
  <p class="head">%s</p>
</header>
<section class="mid">
  <figure class="photo"><img src="%s" alt=""></figure>
  <div class="side">
    <p class="blurb">%s</p>
    <p class="facts-t">%s</p>
    <dl class="facts">%s</dl>
    <p class="fly">%s</p>
  </div>
</section>
<footer class="bot">
  <div class="cta">
    <p class="ask">%s</p>
    %s
  </div>
  <div class="qr">
    <p class="scan">%s</p>
    <img src="%s" alt="">
  </div>
</footer>
</body></html>""" % (lang, t["eyebrow"], t["head"], uri(PHOTO), t["blurb"], t["facts"],
                     rows, t["fly"], t["ask"], tels, t["scan"], uri(QR))


def main():
    for p, what in [(CHROME, "Google Chrome"), (QR, "the QR image"), (PHOTO, "the photo")]:
        if not os.path.exists(p):
            sys.exit("missing %s: %s" % (what, p))
    content = json.load(open(path("src/content.json"), encoding="utf-8"))
    os.makedirs(path("dist"), exist_ok=True)
    tmp = tempfile.mkdtemp()
    for lang in ("en", "es"):
        src = os.path.join(tmp, "flyer-%s.html" % lang)
        open(src, "w", encoding="utf-8").write(html(lang, content))
        out = path("dist/flyer-%s.pdf" % lang)
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-first-run",
                        "--no-pdf-header-footer", "--print-to-pdf-no-header",
                        "--virtual-time-budget=12000",
                        "--print-to-pdf=" + out, "file://" + src],
                       capture_output=True)
        print("  dist/flyer-%s.pdf   %6.0f KB" % (lang, os.path.getsize(out) / 1024))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
