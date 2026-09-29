# Neues Studio ins Feedback aufnehmen

Gilt für jede Eröffnung, unabhängig von Stadt oder Disziplin. Code muss dafür nicht
geändert werden, außer bei Sprache und Ticker (Schritt 5).

## Was vorher vorliegen muss

| Angabe | Woher | Pflicht |
|---|---|---|
| Stadt, Standort, Disziplin | Tim | ja |
| `bsport_company_id` | bsport Backoffice, Branch der Stadt | für die Lehrer-Zuordnung |
| `bsport_venue_id` | bsport Backoffice, Einrichtung des Studios | für die Lehrer-Zuordnung |
| Google-Bewertungslink | Google Unternehmensprofil, Format `https://g.page/r/.../review` | nein |

Ohne Venue ID und Company ID wird Feedback gespeichert, aber keiner Lehrkraft
zugeordnet (`attribution_status = no_venue_mapping`). Beides lässt sich später
nachtragen, die Zuordnung gilt dann aber erst für neue Bewertungen.

Bekannte Company IDs aus dem Bestand: Köln 2562, Berlin 3984, Düsseldorf 5546,
Hamburg 5547.

## 1. Slug festlegen

Muster `stadt-standort-typ`, klein, ohne Umlaute (ae, oe, ue, ss).
Typkürzel: `ref` Reformer, `mat` Matten, `strength` Strength.

Beispiele: `koeln-suedstadt-ref`, `berlin-fhain-ref`, `koeln-belgisches-strength`.

**Der Slug steht im gedruckten QR-Code und ist danach nicht mehr änderbar.**
Immer erst von Tim bestätigen lassen.

## 2. Zeile in Supabase anlegen

Projekt `sjnrqfqjfqpdjhukgiue` (feedback loop studios). Der Name folgt dem Muster
`YTTP Stadt – Standort – Disziplin` mit Halbgeviertstrich. Das Dashboard und das
QR-Skript lesen Stadt und Standort daraus. `type` ist `reformer`, `matten` oder
`functional` (Strength läuft als `functional`).

```sql
insert into studios (slug, name, type, google_review_url, bsport_venue_id, bsport_company_id)
values ('SLUG', 'YTTP Stadt – Standort – Disziplin', 'reformer', null, null, null)
returning *;
```

Nachtragen, sobald vorhanden:

```sql
update studios set bsport_company_id = ZAHL, bsport_venue_id = ZAHL where slug = 'SLUG';
update studios set google_review_url = 'LINK' where slug = 'SLUG';
```

## 3. Formular prüfen

`https://feedback.yttp.de/?studio=SLUG` im Handy öffnen. Es muss der Studioname
erscheinen, nicht "Studio nicht gefunden". Wer eine Testbewertung abschickt, gibt
als Kommentar genau `test` ein. Das PayScale Dashboard filtert sie dann heraus.
Das Management Dashboard sieht keine Kommentare und zählt sie mit, deshalb die
Testzeile danach in Supabase löschen.

## 4. QR-Aushang erzeugen

```bash
pip install qrcode reportlab
python3 qr/make_qr.py SLUG
```

Das PDF landet in `qr/pdf/`. Das Skript bricht ab, wenn der Slug nicht in
`studios` steht. PDF ins Repo committen, dann drucken.

Nicht über ein Upload-Tool eines Chats in Google Drive laden: das hat Dateien
mehrfach still beschädigt. Aus dem Repo herunterladen oder lokal erzeugen.

## 5. Sprache und Ticker in `index.html`

Beides hängt am Slug und ist fest im Code:

- Englisch bekommen nur Slugs mit `berlin-`, alle anderen Deutsch.
- Der Banner "Opening Soon" steht in `setupTicker()` für `berlin-` und `koeln-`.
  Das beworbene Studio selbst steht in `TICKER_SELF_EXCLUDE`, damit es nicht für
  sich selbst wirbt.

Bei einer neuen Stadt oder einem neuen Opening dort anpassen.

## 6. Nachziehen

- PayScale Dashboard: die Kurzform in Tabellen verlässt sich auf das Namensmuster
  aus Schritt 2, sonst nichts zu tun.
- Management Dashboard: holt Feedback nur für Studios mit `bsport_company_id`.
