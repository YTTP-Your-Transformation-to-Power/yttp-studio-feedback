"""Erzeugt den Aushang "RATE YOUR CLASS!" mit QR-Code fuer ein Studio.

Aufruf aus dem Repo-Stamm:

    python3 qr/make_qr.py hamburg-ottensen-ref Hamburg_Ottensen

Erstes Argument ist der Slug, zweites der Dateiname wie im Drive-Ordner
03_Studios/QR Codes (Stadt_Standort, ausgeschrieben, mit Umlauten).

Heraus kommen beide Varianten des Designs, jeweils als SVG, PDF und EPS:

    qr/druck/V1_Linksbuendig/{Vector,PDF,EPS}/QR_<Name>.*
    qr/druck/V2_Mittig/{Vector,PDF,EPS}/...

Die Vorlagen unter qr/vorlage/ sind die Illustrator-Dateien aus dem Drive, bei
denen nur der QR-Code durch einen Platzhalter ersetzt ist. Schrift liegt dort
als Pfad vor, es wird also keine Schriftdatei gebraucht. Der QR-Code wird mit
denselben Parametern erzeugt wie in den Vorlagen (Fehlerkorrektur M, kein
Rand, gleiche Flaeche), sodass alle Aushaenge gleich aussehen.

Vor dem Erzeugen prueft das Skript gegen die Tabelle studios in Supabase, dass
der Slug existiert. Danach liest es jeden erzeugten QR-Code zurueck und bricht
ab, wenn nicht exakt die erwartete Adresse drinsteht.

Abhaengigkeiten: pip install qrcode svglib opencv-python-headless pymupdf
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

import qrcode
from reportlab.graphics import renderPDF, renderPS
from svglib.svglib import svg2rlg

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "qr" / "vorlage"
OUT_DIR = REPO / "qr" / "druck"
FEEDBACK_BASE_URL = "https://feedback.yttp.de/"

# Flaeche des QR-Codes in der jeweiligen Vorlage (x, y, Kantenlaenge in pt),
# aus den Illustrator-Dateien uebernommen.
VARIANTS = {
    "V1_Linksbuendig": {"template": "V1_linksbuendig.svg", "box": (75.0993, 324.3906, 221.9389), "eps_prefix": ""},
    "V2_Mittig": {"template": "V2_mittig.svg", "box": (181.3900, 329.4292, 231.9300), "eps_prefix": "YTTP_Studios_DINA4_"},
}


def supabase_config():
    """URL und Anon Key aus index.html, damit sie nur an einer Stelle stehen."""
    html = (REPO / "index.html").read_text(encoding="utf-8")
    url = re.search(r"SUPABASE_URL = '([^']+)'", html).group(1)
    key = re.search(r"SUPABASE_ANON_KEY = '([^']+)'", html).group(1)
    return url, key


def load_slugs():
    url, key = supabase_config()
    req = urllib.request.Request(
        f"{url}/rest/v1/studios?select=slug",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return {row["slug"] for row in json.load(res)}


def qr_rects(url, box, slug):
    """QR-Code als Rechtecke, eine Zeile pro zusammenhaengendem Lauf."""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    q.add_data(url)
    q.make(fit=True)
    matrix = q.get_matrix()
    x0, y0, side = box
    mod = side / len(matrix)
    rects = []
    for r, row in enumerate(matrix):
        c = 0
        while c < len(row):
            if row[c]:
                start = c
                while c < len(row) and row[c]:
                    c += 1
                rects.append(
                    f'<rect x="{x0 + start * mod:.4f}" y="{y0 + r * mod:.4f}" '
                    f'width="{(c - start) * mod:.4f}" height="{mod:.4f}" shape-rendering="crispEdges"/>'
                )
            else:
                c += 1
    return f'<g id="QR_{slug}">\n    ' + "\n    ".join(rects) + "\n  </g>"


def verify(pdf_path, url):
    """Liest den QR-Code aus dem fertigen Druck-PDF zurueck."""
    import cv2
    import fitz
    import numpy as np

    # Zwischen den Rechteckzeilen entstehen beim Rastern feine Haarlinien, an
    # denen der Decoder je nach Aufloesung scheitert. Deshalb mehrere
    # Aufloesungen, jeweils auch leicht weichgezeichnet. Bestanden ist, wenn
    # mindestens eine exakt die Adresse liefert und keine etwas anderes.
    page = fitz.open(pdf_path)[0]
    found = set()
    for dpi in (150, 200, 300, 400):
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        for candidate in (img, cv2.GaussianBlur(img, (5, 5), 0)):
            value, _, _ = cv2.QRCodeDetector().detectAndDecode(candidate)
            if value:
                found.add(value)
    if found != {url}:
        raise SystemExit(f"{pdf_path.name}: QR-Code liefert {sorted(found) or 'nichts'}, erwartet '{url}'")


A4_PT = (595.28, 841.89)


def a4_drawing(svg_path):
    """svglib liest die Vorlage ohne width/height als Pixel und verkleinert sie
    um 0,75. Zurueck auf DIN A4 in Punkt skalieren, wie die Originale."""
    drawing = svg2rlg(str(svg_path))
    factor = A4_PT[0] / drawing.width
    drawing.scale(factor, factor)
    drawing.width, drawing.height = drawing.width * factor, drawing.height * factor
    return drawing


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    slug, name = argv

    if slug not in load_slugs():
        print(f"Slug '{slug}' steht nicht in der Tabelle studios. Erst dort anlegen, dann drucken.")
        return 1

    url = f"{FEEDBACK_BASE_URL}?studio={slug}"
    for variant, cfg in VARIANTS.items():
        template = (TEMPLATES / cfg["template"]).read_text(encoding="utf-8")
        svg = template.replace("<!--QR-->", qr_rects(url, cfg["box"], slug))

        base = OUT_DIR / variant
        for sub in ("Vector", "PDF", "EPS"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        svg_path = base / "Vector" / f"QR_{name}.svg"
        svg_path.write_text(svg, encoding="utf-8")

        drawing = a4_drawing(svg_path)
        pdf_path = base / "PDF" / f"QR_{name}.pdf"
        renderPDF.drawToFile(drawing, str(pdf_path))
        renderPS.drawToFile(drawing, str(base / "EPS" / f"{cfg['eps_prefix']}QR_{name}.eps"))

        verify(pdf_path, url)
        print(f"{variant}: QR_{name} -> {url} (geprueft)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
