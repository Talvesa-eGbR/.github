"""Zeichnet die Grafiken des Org-Profils (profile/assets/) als SVG.

Alle Grafiken haben einen transparenten Hintergrund und liegen direkt auf der
Seite. Jede gibt es für helles und dunkles Design (-light/-dark) und, wo das
Layout umbricht, zusätzlich schmal für Handybreite (-n). Zeilenumbrüche legt
dieses Skript fest, nicht der Browser: so bricht nichts ungewollt um.

- banner      Lockup, gesperrter Claim, große Mono-Zeile, Bildmarke
- stats       Kennzahlen von der Startseite (breit 4 nebeneinander, schmal 2×2)
- leistungen, pakete, ablauf, haltung
              Abschnitt mit Kopf (gesperrte Zeile + Headline) und Spalten
- head-referenzen, head-kontakt
              nur der Kopf; der Inhalt steht als Text mit Links in der README
- btn-anfragen, btn-erstgespraech
              Buttons (gefüllt / Outline)
- mark        Bildmarke für den Fuß der README

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
from html import escape
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

FONTS = os.environ.get("TALVESA_FONTS", "../talvesa/talvesa/static/talvesa/fonts/").rstrip("/") + "/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "profile/assets"

EMBLEM = (
    "M39.154 23.238 15.259 23.238 0 0 106.715 0 91.455 23.238 67.15 23.238 "
    "105.453 81.569 91.455 102.887ZM119.451 60.337 105.453 39.02 131.076 0 159.072 0Z"
)
EMBLEM_W, EMBLEM_H = 159.072, 102.887

THEMES = {
    "light": dict(ink="#0B0B0B", soft="#444444", paper="#F5F5F5"),
    "dark": dict(ink="#F5F5F5", soft="#A3A3A3", paper="#0B0B0B"),
}

# Breite der Zeichenfläche: breit für den Desktop, schmal fürs Handy.
WIDE, NARROW = 960, 480
TOP = 64  # Abstand über jedem Abschnittskopf


class Face:
    def __init__(self, path, prefix):
        self.font = TTFont(path)
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.prefix = prefix

    def glyph(self, ch):
        name = self.cmap.get(ord(ch))
        if name is None:
            raise SystemExit(f"Glyphe fehlt: {ch!r}")
        return name

    def outline(self, name):
        """Umriss in Font-Einheiten, ganzzahlig gerundet."""
        pen = SVGPathPen(self.gs, ntos=lambda v: str(round(v)))
        self.gs[name].draw(pen)
        return pen.getCommands()

    def width(self, s, size, tracking=0.0):
        adv = sum(self.gs[self.glyph(ch)].width for ch in s) * size / self.upm
        return adv + tracking * size * max(len(s) - 1, 0)


REG = Face(FONTS + "talvesa-mono-regular.woff2", "r")
BOLD = Face(FONTS + "talvesa-mono-bold.woff2", "b")


class Canvas:
    def __init__(self, w, t):
        self.w, self.t, self.parts, self.defs = w, t, [], {}

    def text(self, s, x, y, size, color="ink", face=REG, tracking=0.0):
        """Jede Glyphe steht einmal in <defs> und wird per <use> gesetzt."""
        end = x + face.width(s, size, tracking)
        if end > self.w + 0.5:
            raise SystemExit(f"Zu breit ({end - x:.0f}): {s!r}")
        k = size / face.upm
        uses, cx = [], 0.0
        for ch in s:
            name = face.glyph(ch)
            if ch != " ":
                gid = f"{face.prefix}{list(face.gs.keys()).index(name)}"
                self.defs.setdefault(gid, (face, name))
                uses.append(f'<use href="#{gid}" x="{round(cx)}"/>')
            cx += face.gs[name].width + tracking * face.upm
        self.parts.append(
            f'<g fill="{self.t[color]}" transform="translate({x:.1f} {y:.1f}) scale({k:.5f} {-k:.5f})">'
            + "".join(uses) + "</g>"
        )
        return end

    def para(self, s, x, y, size, maxw, color="soft", face=REG, lh=1.5):
        """Umbrechen nach Wörtern, Zeilen möglichst gleich lang (keine einzelnen
        Wörter in der letzten Zeile); gibt die Grundlinie der letzten Zeile zurück."""

        def wrap(limit):
            lines, cur = [], ""
            for word in s.split():
                test = f"{cur} {word}".strip()
                if face.width(test, size) <= limit or not cur:
                    cur = test
                else:
                    lines.append(cur)
                    cur = word
            return lines + [cur]

        lines = wrap(maxw)
        limit = maxw
        while limit > 0:
            shorter = wrap(limit - size * 0.6)
            if len(shorter) != len(lines):
                break
            lines, limit = shorter, limit - size * 0.6
        for i, line in enumerate(lines):
            self.text(line, x, y + i * size * lh, size, color, face)
        return y + (len(lines) - 1) * size * lh

    def emblem(self, x, y, height, color="ink"):
        s = height / EMBLEM_H
        self.parts.append(
            f'<path fill="{self.t[color]}" transform="translate({x:.2f} {y:.2f}) scale({s:.5f})" d="{EMBLEM}"/>'
        )

    def raw(self, s):
        self.parts.append(s)

    def svg(self, h, label, scale=1.0):
        h = round(h)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{round(self.w * scale)}" height="{round(h * scale)}" '
            f'viewBox="0 0 {self.w} {h}" role="img" aria-label="{escape(label)}">\n'
            + "<defs>" + "".join(f'<path id="{gid}" d="{f.outline(n)}"/>' for gid, (f, n) in self.defs.items()) + "</defs>\n"
            + "\n".join(self.parts)
            + "\n</svg>\n"
        )


# ---------------------------------------------------------------- Bausteine

def head(c, eyebrow, title, y):
    """Abschnittskopf wie auf talvesa.de; gibt die Unterkante zurück."""
    narrow = c.w == NARROW
    c.text(eyebrow, 0, y + 14, 16, "soft", REG, 0.2)
    size = 30 if narrow else 40
    end = c.para(title, 0, y + 14 + size * 1.6, size, c.w, "ink", BOLD, 1.2)
    return end + 16


def cells(c, items, y, cols, gap_x, gap_y, draw):
    """Raster aus Zellen; `draw(c, item, x, y, w)` gibt die Unterkante zurück."""
    colw = (c.w - gap_x * (cols - 1)) / cols
    for r in range(0, len(items), cols):
        bottom = y
        for i, item in enumerate(items[r:r + cols]):
            bottom = max(bottom, draw(c, item, i * (colw + gap_x), y, colw))
        y = bottom + gap_y
    return y - gap_y


def numbered(c, item, x, y, w):
    num, title, body = item
    body_size = 18 if c.w == WIDE else 21
    c.text(num, x, y + 14, 16, "soft", BOLD, 0.1)
    end = c.para(title, x, y + 48, 22 if c.w == WIDE else 24, w, "ink", BOLD, 1.25)
    return c.para(body, x, end + body_size + 14, body_size, w, "soft")


# ---------------------------------------------------------------- Grafiken

LABEL_BANNER = "Talvesa — Websites und Apps mit Anspruch. Webdesign-Studio aus Freiburg im Breisgau."


def banner(t, w):
    c = Canvas(w, t)
    if w == WIDE:
        c.emblem(0, 12, 30)
        c.text("Talvesa", 30 * EMBLEM_W / EMBLEM_H + 16, 40, 36, tracking=0.02)
        c.text("LÖSUNGEN FÜR DAS DIGITALE MORGEN", 0, 92, 17, "soft", tracking=0.22)
        c.text("Websites und Apps", 0, 192, 58, face=BOLD)
        c.text("mit Anspruch.", 0, 260, 58, face=BOLD)
        x = c.text("WEBDESIGN-STUDIO", 0, 316, 17, tracking=0.14)
        c.text("  ·  FREIBURG IM BREISGAU", x, 316, 17, "soft", tracking=0.14)
        c.emblem(w - 200 * EMBLEM_W / EMBLEM_H, 12, 200)
        return c.svg(324, LABEL_BANNER)
    c.emblem(0, 8, 24)
    c.text("Talvesa", 24 * EMBLEM_W / EMBLEM_H + 12, 31, 28, tracking=0.02)
    c.emblem(w - 56 * EMBLEM_W / EMBLEM_H, 4, 56)
    c.text("LÖSUNGEN FÜR DAS DIGITALE MORGEN", 0, 96, 13, "soft", tracking=0.2)
    c.text("Websites und Apps", 0, 168, 44, face=BOLD)
    c.text("mit Anspruch.", 0, 222, 44, face=BOLD)
    c.text("WEBDESIGN-STUDIO", 0, 266, 14, tracking=0.12)
    c.text("FREIBURG IM BREISGAU", 0, 292, 14, "soft", tracking=0.12)
    return c.svg(300, LABEL_BANNER)


STATS = [
    ("15+", "Jahre Erfahrung", "im Team"),
    ("1:1", "Persönliche", "Betreuung"),
    ("DE", "Hosting in", "Deutschland"),
    ("0", "Monate", "Mindestlaufzeit"),
]


def stats(t, w):
    c = Canvas(w, t)
    cols = 4 if w == WIDE else 2
    num = 60 if w == WIDE else 52

    def draw(c, item, x, y, cw):
        n, a, b = item
        c.text(n, x, y + num * 0.78, num, face=BOLD)
        ls = 18 if c.w == WIDE else 21
        c.text(a, x, y + num + 12 + ls, ls, "soft")
        c.text(b, x, y + num + 12 + ls * 2.4, ls, "soft")
        return y + num + 12 + ls * 2.8

    bottom = cells(c, STATS, 48, cols, 24, 36, draw)
    label = ", ".join(" ".join(s) for s in STATS)
    return c.svg(bottom + 8, label)


LEISTUNGEN = [
    ("01", "Websites & Komplettpakete",
     "Vom One-Pager bis zum großen Auftritt, auch als Relaunch. Inhalte pflegen Sie selbst oder wir für Sie."),
    ("02", "Hosting & Betreuung",
     "Server in Deutschland, Domain, SSL und Updates. Kleine Änderungen sind inklusive."),
    ("03", "Mobile Apps",
     "iOS und Android, vom ersten Prototyp bis zur Veröffentlichung im Store."),
    ("04", "SEO & Sichtbarkeit",
     "Kurze Ladezeiten, saubere Technik und ein gepflegtes Google-Profil, damit man Sie findet."),
]

HALTUNG = [
    ("01", "Daten bleiben im Land.",
     "Hosting in deutschen Rechenzentren, Datenschutz sauber eingerichtet."),
    ("02", "Keine Ressourcen von Dritten.",
     "Schriften, Skripte und Styles liegen auf dem eigenen Server. Kein CDN, kein Tracking, das niemand bestellt hat."),
    ("03", "Barrierefreiheit geprüft.",
     "Geprüft, nicht behauptet: Unsere Seiten laufen im CI durch axe-core gegen WCAG 2.2 AA, hell und dunkel."),
    ("04", "Ladezeit mit Budget.",
     "Feste Budgets für Anfragen und Seitengewicht statt eines Scores, der mit der Tagesform schwankt."),
    ("05", "Sicherheit an der Wirkung.",
     "CSP, Cookie-Flags und Zugriffsrechte prüfen wir an der echten Antwort des Servers."),
    ("06", "Klare Konditionen.",
     "Feste Preise, faire Laufzeiten, und die Domain gehört Ihnen."),
]


def section(t, w, eyebrow, title, items, label):
    c = Canvas(w, t)
    y = head(c, eyebrow, title, TOP) + 40
    bottom = cells(c, items, y, 2 if w == WIDE else 1, 48, 44, numbered)
    return c.svg(bottom + 12, label)


def leistungen(t, w):
    label = "Leistungen: " + "; ".join(f"{a}: {b}" for _, a, b in LEISTUNGEN)
    return section(t, w, "01 / LEISTUNGEN", "Webdesign, Apps und SEO aus einer Hand.", LEISTUNGEN, label)


def haltung(t, w):
    label = "Worauf wir bestehen: " + "; ".join(f"{a} {b}" for _, a, b in HALTUNG)
    return section(t, w, "05 / HALTUNG", "Worauf wir bestehen.", HALTUNG, label)


PAKETE = [
    ("S · PRÄSENZ", False, "34,90 €", "41,53 €", "Alles Wichtige auf einer Seite.",
     ["One-Page-Website", "Kontakt & Anfahrt", "4 Änderungen pro Jahr"]),
    ("M · BUSINESS", True, "59,90 €", "71,28 €", "Der vollständige Auftritt.",
     ["Bis zu 6 Unterseiten", "Google-Profil eingerichtet", "6 Änderungen pro Jahr"]),
    ("L · PLUS", False, "89,90 €", "106,98 €", "Mehr Seiten, alles schon drin.",
     ["Bis zu 12 Unterseiten", "Online-Terminbuchung", "Inhalte selbst pflegen"]),
]


def pakete(t, w):
    c = Canvas(w, t)
    y = head(c, "03 / PAKETE", "Klare Pakete, feste Preise.", TOP) + 40

    def draw(c, item, x, y, cw):
        name, rec, net, gross, desc, feats = item
        end = c.text(name, x, y + 14, 16, "soft", BOLD, 0.1)
        if rec:
            c.text("EMPFOHLEN", end + 16, y + 14, 16, "ink", BOLD, 0.1)
        c.text(net, x, y + 66, 44, face=BOLD)
        wide = c.w == WIDE
        fs = 17 if wide else 21
        c.text("netto/Monat · brutto " + gross, x, y + 96, 15 if wide else 19, "soft")
        yy = c.para(desc, x, y + 140, 18 if wide else 22, cw, "ink")
        for i, f in enumerate(feats):
            c.text("— " + f, x, yy + fs * 2 + i * fs * 1.6, fs, "soft")
        return yy + fs * 2 + (len(feats) - 1) * fs * 1.6

    bottom = cells(c, PAKETE, y, 3 if w == WIDE else 1, 40, 48, draw)
    bottom = c.para("Hosting, Domain, SSL und Betreuung sind immer dabei. Websites gibt es auch zum Kauf.",
                    0, bottom + 52, 16 if c.w == WIDE else 20, c.w, "soft")
    label = "Pakete: " + "; ".join(f"{p[0]}: {p[2]} netto pro Monat, brutto {p[3]}" for p in PAKETE)
    return c.svg(bottom + 12, label)


ABLAUF = [
    ("01", "Gespräch", "Sie erzählen, was Sie brauchen. Wir schicken ein festes Angebot."),
    ("02", "Entwurf", "Struktur, Texte und Gestaltung. Sie sehen alles, bevor wir bauen."),
    ("03", "Umsetzung", "Zwischenstände zum Freigeben. Domain und SSL richten wir nebenbei ein."),
    ("04", "Livegang", "Online, für Suchmaschinen eingerichtet und danach von uns betreut."),
]


def ablauf(t, w):
    c = Canvas(w, t)
    y = head(c, "04 / ABLAUF", "In vier Schritten online.", TOP) + 40
    ink, soft = t["ink"], t["soft"]
    if w == WIDE:
        gap = 32
        colw = (w - 3 * gap) / 4
        c.raw(f'<path d="M0 {y + 6}H{w}" stroke="{soft}" stroke-width="1.5"/>')
        bottom = y
        for i, (n, title, body) in enumerate(ABLAUF):
            x = i * (colw + gap)
            c.raw(f'<circle cx="{x + 6}" cy="{y + 6}" r="6" fill="{ink}"/>')
            c.text(n, x, y + 52, 16, "soft", BOLD, 0.1)
            c.text(title, x, y + 86, 22, face=BOLD)
            bottom = max(bottom, c.para(body, x, y + 120, 17, colw))
    else:
        tops = []
        yy = y
        for n, title, body in ABLAUF:
            tops.append(yy)
            c.text(n + "  " + title, 36, yy + 12, 22, face=BOLD)
            bottom = c.para(body, 36, yy + 48, 21, w - 36)
            yy = bottom + 40
        c.raw(f'<path d="M6 {tops[0] + 4}V{tops[-1] + 4}" stroke="{soft}" stroke-width="1.5"/>')
        for ty in tops:
            c.raw(f'<circle cx="6" cy="{ty + 4}" r="6" fill="{ink}"/>')
    label = "Ablauf: " + "; ".join(f"{n} {a}: {b}" for n, a, b in ABLAUF)
    return c.svg(bottom + 12, label)


def head_only(eyebrow, title):
    def render(t, w):
        c = Canvas(w, t)
        bottom = head(c, eyebrow, title, TOP)
        return c.svg(bottom + 4, f"{title}")
    return render


def button(t, text, filled, h_display, size=22, pad=28):
    h = 60
    w = round(BOLD.width(text, size) + 2 * pad)
    c = Canvas(w, t)
    sw = 2
    fill = t["ink"] if filled else "none"
    c.raw(f'<rect x="{sw / 2}" y="{sw / 2}" width="{w - sw}" height="{h - sw}" rx="6" '
          f'fill="{fill}" stroke="{t["ink"]}" stroke-width="{sw}"/>')
    c.text(text, pad, h / 2 + size * 0.36, size, "paper" if filled else "ink", BOLD)
    return c.svg(h, text, h_display / h)


def mark(t):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="{64 * EMBLEM_H / EMBLEM_W:.2f}" '
        f'viewBox="0 0 {EMBLEM_W} {EMBLEM_H}" role="img" aria-label="Talvesa">'
        f'<path fill="{t["ink"]}" d="{EMBLEM}"/></svg>\n'
    )


def write(name, content):
    with open(f"{OUT}/{name}.svg", "w") as fh:
        fh.write(content)


RESPONSIVE = {
    "banner": banner,
    "stats": stats,
    "leistungen": leistungen,
    "head-referenzen": head_only("02 / REFERENZEN", "Ausgewählte Projekte."),
    "pakete": pakete,
    "ablauf": ablauf,
    "haltung": haltung,
    "head-kontakt": head_only("06 / KONTAKT", "Erzählen Sie uns, was Sie vorhaben."),
}

for theme, t in THEMES.items():
    for name, fn in RESPONSIVE.items():
        write(f"{name}-{theme}", fn(t, WIDE))
        write(f"{name}-{theme}-n", fn(t, NARROW))
    # Buttons: breit 44 px hoch; schmal kleiner und kürzer, damit beide in eine
    # Zeile passen (zusammen höchstens ~330 px).
    write(f"btn-anfragen-{theme}", button(t, "Projekt anfragen →", True, 44))
    write(f"btn-erstgespraech-{theme}", button(t, "15-Minuten-Erstgespräch", False, 44))
    write(f"btn-anfragen-{theme}-n", button(t, "Projekt anfragen →", True, 38, 22, 22))
    write(f"btn-erstgespraech-{theme}-n", button(t, "Erstgespräch", False, 38, 22, 22))
    write(f"mark-{theme}", mark(t))
print("ok")
