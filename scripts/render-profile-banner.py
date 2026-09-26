"""Zeichnet Banner und Bildmarke des Org-Profils (profile/assets/) als SVG.

Vorbild ist brand/og-default.png aus Talvesa-eGbR/talvesa: Raster, Lockup,
gesperrter Claim, große Mono-Zeile, rechts die angeschnittene Bildmarke.
Text wird mit fontTools in Pfade umgewandelt, damit GitHub keine Schrift laden
muss. Die Pfade der Bildmarke stammen aus partials/logomark.html.

    pip install fonttools brotli
    TALVESA_FONTS=../talvesa/talvesa/static/talvesa/fonts python scripts/render-profile-banner.py
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

W, H = 1280, 420
THEMES = {
    "light": dict(bg="#F5F5F5", ink="#0B0B0B", soft="#444444", line="rgba(11,11,11,0.07)"),
    "dark": dict(bg="#0B0B0B", ink="#F5F5F5", soft="#A3A3A3", line="rgba(245,245,245,0.07)"),
}


def emblem(x, y, height, fill):
    s = height / EMBLEM_H
    return f'<path fill="{fill}" transform="translate({x:.2f} {y:.2f}) scale({s:.5f})" d="{EMBLEM}"/>'


def banner(t):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Talvesa — Websites und Apps mit Anspruch. Softwarestudio aus Freiburg im Breisgau.">',
        f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
    ]
    # Raster wie auf dem Open-Graph-Bild: 60px, feine Linien.
    grid = []
    for gx in range(0, W + 1, 60):
        grid.append(f"M{gx} 0V{H}")
    for gy in range(0, H + 1, 60):
        grid.append(f"M0 {gy}H{W}")
    parts.append(f'<path d="{" ".join(grid)}" stroke="{t["line"]}" stroke-width="1" fill="none"/>')

    left = 84
    # Lockup: Bildmarke + Wortmarke.
    parts.append(emblem(left, 62, 34, t["ink"]))
    d, _ = REG.text("Talvesa", left + 34 * EMBLEM_W / EMBLEM_H + 22, 93, 44, 0.02)
    parts.append(f'<path fill="{t["ink"]}" d="{d}"/>')
    # Claim, gesperrt.
    d, _ = REG.text("LÖSUNGEN FÜR DAS DIGITALE MORGEN", left, 140, 15, 0.28)
    parts.append(f'<path fill="{t["soft"]}" d="{d}"/>')
    # Die große Zeile.
    d, _ = REG.text("Websites und Apps", left, 262, 52, 0)
    parts.append(f'<path fill="{t["ink"]}" d="{d}"/>')
    d, _ = REG.text("mit Anspruch.", left, 322, 52, 0)
    parts.append(f'<path fill="{t["ink"]}" d="{d}"/>')
    # Fußzeile.
    d, x = REG.text("TALVESA.DE", left, 372, 15, 0.16)
    parts.append(f'<path fill="{t["ink"]}" d="{d}"/>')
    d, _ = REG.text("  ·  WEBSITES · WEB-APPS · MOBILE APPS · SEO", x, 372, 15, 0.16)
    parts.append(f'<path fill="{t["soft"]}" d="{d}"/>')

    # Große Bildmarke rechts, am Rand angeschnitten.
    parts.append(emblem(800, 40, 340, t["ink"]))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def mark(t_ink):
    """Die Bildmarke allein, für den Fuß der README."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="{64 * EMBLEM_H / EMBLEM_W:.2f}" '
        f'viewBox="0 0 {EMBLEM_W} {EMBLEM_H}" role="img" aria-label="Talvesa">'
        f'<path fill="{t_ink}" d="{EMBLEM}"/></svg>\n'
    )


for name, t in THEMES.items():
    with open(f"{OUT}/banner-{name}.svg", "w") as fh:
        fh.write(banner(t))
    with open(f"{OUT}/mark-{name}.svg", "w") as fh:
        fh.write(mark(t["ink"]))
print("ok")
