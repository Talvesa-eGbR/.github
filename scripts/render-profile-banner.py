"""Zeichnet die Grafiken des Org-Profils (profile/assets/) als SVG.

Alle Grafiken haben einen transparenten Hintergrund und liegen direkt auf der
Seite, je eine Variante für helles und dunkles Design:

- banner-*.svg   Lockup, gesperrter Claim, große Mono-Zeile, Bildmarke rechts
- stats-*.svg    Kennzahlen von der Startseite, ohne Fläche und Trennlinien
- btn-anfragen-*.svg, btn-erstgespraech-*.svg   Buttons (gefüllt / Outline)
- mark-*.svg     Bildmarke für den Fuß der README

Text wird mit fontTools in Pfade umgewandelt, damit GitHub keine Schrift laden
muss. Die Pfade der Bildmarke stammen aus partials/logomark.html.

Schriften: talvesa-mono-regular.woff2 und talvesa-mono-bold.woff2 von
talvesa.de (/static/assets/talvesa-mono-regular-*.woff2, …-bold-*.woff2),
ohne Hash umbenannt.

    pip install fonttools brotli
    TALVESA_FONTS=pfad/zu/fonts python scripts/render-profile-banner.py
"""

import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONTS = os.environ.get("TALVESA_FONTS", "../talvesa/talvesa/static/talvesa/fonts/").rstrip("/") + "/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "profile/assets"

EMBLEM = (
    "M39.154 23.238 15.259 23.238 0 0 106.715 0 91.455 23.238 67.15 23.238 "
    "105.453 81.569 91.455 102.887ZM119.451 60.337 105.453 39.02 131.076 0 159.072 0Z"
)
EMBLEM_W, EMBLEM_H = 159.072, 102.887


class Face:
    def __init__(self, path):
        self.font = TTFont(path)
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def text(self, s, x, y, size, tracking=0.0):
        """Pfad für `s` mit Grundlinie bei y; tracking in em."""
        scale = size / self.upm
        pen = SVGPathPen(self.gs)
        cx = x
        for ch in s:
            name = self.cmap.get(ord(ch))
            if name is None:
                raise SystemExit(f"Glyphe fehlt: {ch!r}")
            g = self.gs[name]
            if ch != " ":
                g.draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
            cx += g.width * scale + tracking * size
        return pen.getCommands(), cx - tracking * size

    def width(self, s, size, tracking=0.0):
        return self.text(s, 0, 0, size, tracking)[1]


REG = Face(FONTS + "talvesa-mono-regular.woff2")
BOLD = Face(FONTS + "talvesa-mono-bold.woff2")

THEMES = {
    "light": dict(ink="#0B0B0B", soft="#444444", paper="#F5F5F5"),
    "dark": dict(ink="#F5F5F5", soft="#A3A3A3", paper="#0B0B0B"),
}


def svg_open(w, h, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'
    )


def emblem(x, y, height, fill):
    s = height / EMBLEM_H
    return f'<path fill="{fill}" transform="translate({x:.2f} {y:.2f}) scale({s:.5f})" d="{EMBLEM}"/>'


def path(face, s, x, y, size, fill, tracking=0.0):
    d, end = face.text(s, x, y, size, tracking)
    return f'<path fill="{fill}" d="{d}"/>', end


def banner(t):
    # Kein Rechteck, kein Raster: der Hintergrund kommt von GitHub. Linksbündig
    # ohne Einzug, damit das Banner auf einer Linie mit dem Text darunter steht.
    W, H = 960, 320
    parts = [svg_open(W, H, "Talvesa — Websites und Apps mit Anspruch. Webdesign-Studio aus Freiburg im Breisgau.")]
    left = 0
    parts.append(emblem(left, 14, 30, t["ink"]))
    p, _ = path(REG, "Talvesa", left + 30 * EMBLEM_W / EMBLEM_H + 18, 42, 38, t["ink"], 0.02)
    parts.append(p)
    p, _ = path(REG, "LÖSUNGEN FÜR DAS DIGITALE MORGEN", left, 88, 19, t["soft"], 0.2)
    parts.append(p)
    p, _ = path(BOLD, "Websites und Apps", left, 182, 54, t["ink"])
    parts.append(p)
    p, _ = path(BOLD, "mit Anspruch.", left, 246, 54, t["ink"])
    parts.append(p)
    p, x = path(REG, "WEBDESIGN-STUDIO", left, 304, 19, t["ink"], 0.12)
    parts.append(p)
    p, _ = path(REG, "  ·  FREIBURG IM BREISGAU", x, 304, 19, t["soft"], 0.12)
    parts.append(p)
    # Große Bildmarke rechts.
    parts.append(emblem(W - 190 * EMBLEM_W / EMBLEM_H, 14, 190, t["ink"]))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


STATS = [
    ("15+", "Jahre Erfahrung im Team"),
    ("1:1", "Persönliche Betreuung"),
    ("DE", "Hosting in Deutschland"),
    ("0", "Monate Mindestlaufzeit"),
]


def stats(t):
    # Zwei mal zwei statt vier nebeneinander: so bleiben die Beschriftungen
    # auch in Handybreite lesbar. Keine Fläche, keine Trennlinien.
    W, H = 960, 250
    col, row = 480, 130
    label = ", ".join(f"{n} {l}" for n, l in STATS)
    parts = [svg_open(W, H, label)]
    for i, (num, text) in enumerate(STATS):
        x = (i % 2) * col
        y = (i // 2) * row
        p, _ = path(BOLD, num, x, y + 66, 68, t["ink"])
        parts.append(p)
        p, _ = path(REG, text, x, y + 110, 32, t["soft"])
        parts.append(p)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def button(t, text, filled):
    size, pad_x, h = 22, 30, 60
    tw = BOLD.width(text, size)
    w = round(tw + 2 * pad_x)
    sw = 2
    fill = t["ink"] if filled else "none"
    fg = t["paper"] if filled else t["ink"]
    parts = [svg_open(w, h, text)]
    parts.append(
        f'<rect x="{sw / 2}" y="{sw / 2}" width="{w - sw}" height="{h - sw}" rx="6" '
        f'fill="{fill}" stroke="{t["ink"]}" stroke-width="{sw}"/>'
    )
    # Grundlinie optisch mittig: Versalhöhe ca. 0,7 em.
    p, _ = path(BOLD, text, pad_x, h / 2 + size * 0.36, size, fg)
    parts.append(p)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def mark(t_ink):
    """Die Bildmarke allein, für den Fuß der README."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="{64 * EMBLEM_H / EMBLEM_W:.2f}" '
        f'viewBox="0 0 {EMBLEM_W} {EMBLEM_H}" role="img" aria-label="Talvesa">'
        f'<path fill="{t_ink}" d="{EMBLEM}"/></svg>\n'
    )


def write(name, content):
    with open(f"{OUT}/{name}", "w") as fh:
        fh.write(content)


for name, t in THEMES.items():
    write(f"banner-{name}.svg", banner(t))
    write(f"stats-{name}.svg", stats(t))
    write(f"btn-anfragen-{name}.svg", button(t, "Projekt anfragen →", True))
    write(f"btn-erstgespraech-{name}.svg", button(t, "15-Minuten-Erstgespräch", False))
    write(f"mark-{name}.svg", mark(t["ink"]))
print("ok")
