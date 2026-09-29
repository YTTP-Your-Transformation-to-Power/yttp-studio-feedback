"""Erzeugt das A4-Aushang-PDF mit QR-Code fuer ein Studio.

Aufruf aus dem Repo-Stamm:

    python3 qr/make_qr.py koeln-suedstadt-ref
    python3 qr/make_qr.py --alle

Der QR-Code enthaelt nur https://feedback.yttp.de/?studio=<slug>. Stadt,
Headline und Dateiname werden aus dem Slug abgeleitet, damit alle Aushaenge
gleich aussehen. Bevor ein PDF entsteht, prueft das Skript gegen die Tabelle
studios in Supabase, dass der Slug existiert: ein gedruckter QR-Code mit
falschem Slug fuehrt Gaeste auf "Studio nicht gefunden".

Abhaengigkeiten: pip install qrcode reportlab
"""

import io
import json
import re
import sys
import urllib.request
from pathlib import Path

import qrcode
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "qr" / "pdf"
FEEDBACK_BASE_URL = "https://feedback.yttp.de/"

PAGE_W, PAGE_H = A4

OFFWHITE = HexColor("#F3F2EE")
ANTHRAZIT = HexColor("#1C1C1C")
TAUPE = HexColor("#827B6D")
GRAY_BORDER = HexColor("#DBDBDB")


def supabase_config():
    """URL und Anon Key aus index.html, damit sie nur an einer Stelle stehen."""
    html = (REPO / "index.html").read_text(encoding="utf-8")
    url = re.search(r"SUPABASE_URL = '([^']+)'", html).group(1)
    key = re.search(r"SUPABASE_ANON_KEY = '([^']+)'", html).group(1)
    return url, key


def load_studios():
    """Slug zu Name, etwa koeln-suedstadt-ref -> 'YTTP Köln – Südstadt – Reformer'."""
    url, key = supabase_config()
    req = urllib.request.Request(
        f"{url}/rest/v1/studios?select=slug,name&order=slug.asc",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return {row["slug"]: row["name"] for row in json.load(res)}


def ascii_de(text):
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return text


def labels(slug, name):
    """Stadt und Standort kommen aus dem Namen (Schreibweise wie 'BKiez'),
    das Typkuerzel aus dem Slug ('ref', 'mat'), so wie auf den bisherigen Aushaengen."""
    name_parts = [p.strip() for p in re.split(r"\s+[–—-]\s+", name)]
    slug_parts = slug.split("-")
    if len(name_parts) != 3 or len(slug_parts) < 3:
        raise ValueError(f"'{slug}' / '{name}' folgt nicht dem Muster 'YTTP Stadt – Standort – Typ'")
    stadt = ascii_de(re.sub(r"^YTTP\s+", "", name_parts[0]))
    standort = ascii_de(name_parts[1])
    typ = "-".join(slug_parts[2:]).capitalize()
    words = [stadt, standort, typ]
    title_line = "YTTP " + " - ".join(w.upper() for w in words)
    filename = "YTTP_" + "_-_".join(words) + ".pdf"
    return stadt, title_line, filename


def make_studio_pdf(slug, city_label, title_line, out_path):
    url = f"{FEEDBACK_BASE_URL}?studio={slug}"
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    qr_reader = ImageReader(buf)

    c = canvas.Canvas(str(out_path), pagesize=A4)

    c.setFillColor(OFFWHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    top_bar_h = 78.7
    c.setFillColor(ANTHRAZIT)
    c.rect(0, PAGE_H - top_bar_h, PAGE_W, top_bar_h, fill=1, stroke=0)

    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 30)
    c.drawString(48, PAGE_H - top_bar_h / 2 - 10, "YTTP")

    c.setFont("Helvetica", 15)
    c.drawRightString(PAGE_W - 48, PAGE_H - top_bar_h / 2 - 6, city_label)

    c.setFillColor(ANTHRAZIT)
    c.setFont("Helvetica-Bold", 19)
    headline_y = 700.8
    c.drawCentredString(PAGE_W / 2, headline_y, title_line)

    c.setStrokeColor(HexColor("#D9D8D3"))
    c.setLineWidth(0.75)
    rule_y = headline_y - 21
    c.line(48, rule_y, PAGE_W - 48, rule_y)

    box_side = 300
    box_x = (PAGE_W - box_side) / 2
    box_y = 294.7
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(GRAY_BORDER)
    c.setLineWidth(1)
    c.rect(box_x, box_y, box_side, box_side, fill=1, stroke=1)

    inset = 16
    qr_side = box_side - 2 * inset
    c.drawImage(qr_reader, box_x + inset, box_y + inset, width=qr_side, height=qr_side)

    c.setFillColor(TAUPE)
    c.setFont("Helvetica", 10.5)
    c.drawCentredString(PAGE_W / 2, 268.3, url)

    c.setFillColor(ANTHRAZIT)
    c.setFont("Helvetica", 13)
    c.drawCentredString(PAGE_W / 2, 237, "Scanne den Code nach deiner Session und gib uns dein anonymes Feedback.")

    bottom_bar_h = 39.8
    c.setFillColor(ANTHRAZIT)
    c.rect(0, 0, PAGE_W, bottom_bar_h, fill=1, stroke=0)
    c.setFillColor(HexColor("#9A9A9A"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W / 2, bottom_bar_h / 2 - 3, "feedback.yttp.de")

    c.showPage()
    c.save()


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 1

    known = load_studios()
    slugs = list(known) if argv[0] == "--alle" else [argv[0]]

    for slug in slugs:
        if slug not in known:
            print(f"Slug '{slug}' steht nicht in der Tabelle studios. Erst dort anlegen, dann drucken.")
            return 1
        city_label, title_line, filename = labels(slug, known[slug])
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / filename
        make_studio_pdf(slug, city_label, title_line, out_path)
        print(f"{slug} -> {out_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
