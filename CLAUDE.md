# YTTP Studio Feedback: Anweisungen für Claude Code

## Zweck und Grenzen

QR-Code-Feedbackformular für alle YTTP Studios (`feedback.yttp.de`) plus die
Zuordnung jeder Bewertung zu Kurs und Lehrkraft. Das Projekt **sammelt nur**: es
wertet nicht aus. Auswertung passiert im PayScale Dashboard (`teacher-payscale`) und
im Management Dashboard (`Management-Dashboard`), beide lesen aus derselben Datenbank.

## Stack und Betrieb

- `index.html`: statisches HTML mit Vanilla JS, GitHub Pages, Deploy bei Push auf `main`.
- Supabase `sjnrqfqjfqpdjhukgiue` (feedback loop studios), Region Frankfurt.
- Edge Function `attribute-teacher` (Deno), Quelle in `supabase/functions/`.
  Wird **nicht** automatisch deployt.
- `qr/make_qr.py`: Python, `qrcode`, `svglib`, `opencv-python-headless`, `pymupdf`.
- Kein Railway, keine lokale Arbeitskopie nötig: das Repo ist die Quelle.

## Befehle

```bash
python3 qr/make_qr.py <slug> <Stadt_Standort>   # Aushang V1 und V2, siehe docs/NEUES-STUDIO.md
```

## Das Repo ist öffentlich

GitHub Pages im Free Plan der YTTP-Organisation geht nur mit öffentlichen Repos.
Daraus folgt:

- **Nie** Schlüssel, Tokens, Token-Hashes, Kundendaten, Kommentare oder Exporte
  committen. Der Anon Key in `index.html` ist dafür gedacht, öffentlich zu sein.
- Schutz entsteht allein über RLS und Grants in Supabase. Jede neue Tabelle, View
  oder Funktion muss vor dem Anlegen darauf geprüft werden, was der Anon Key damit
  sehen kann. Views immer mit `security_invoker = true`, sonst umgehen sie RLS
  (genau so waren bis 29. September 2026 alle Kommentare öffentlich lesbar).

## Verbote

- Einen bestehenden Slug ändern oder löschen. Er steht in gedruckten QR-Codes.
- `CNAME` löschen oder umbenennen: dann ist `feedback.yttp.de` weg.
- Die Lehrer-Zuordnung im Browser laufen lassen. bsport-Zugang bleibt in der Edge Function.
- `feedback.comment` aus dem Projekt herausgeben. Das Management Dashboard bekommt nur `has_comment`.
- Die Tabellen `bcn_*` anfassen. Sie gehören zum Workshop-Tool Barcelona und werden
  nach dem Workshop (2. Oktober 2026) nach dessen Teardown-Plan gelöscht.
- Die Spalten `answer_4`, `answer_5` löschen, solange `index.html` sie im Insert
  mitschickt: zwischengespeicherte alte Seiten würden sonst beim Absenden scheitern.

## Auslöser: wenn du X tust, lies vorher Y

Die Standards liegen nicht in diesem Repo, weil es öffentlich ist. Sie stehen im
privaten Repo `claude-fundament`, lokal unter
`~/Documents/Claude/claude-fundament/starter-kit/.claude/docs/`.

| Wenn du ... | lies vorher |
|---|---|
| ein neues Studio aufnimmst oder QR-Codes erzeugst | `docs/NEUES-STUDIO.md` |
| das Schema änderst, eine View oder Funktion anlegst | `checklists/DB-MIGRATION.md`, `architecture/DATA-MODELING.md` |
| Policies, Grants oder Schlüssel anfasst | `security/SECURITY-QUICKREF.md`, bei Tiefe `security/SECURITY-SOP.md` |
| mit Kommentaren oder anderen Kundendaten arbeitest | `compliance/DSGVO-EU-AI-ACT.md` |
| `index.html` änderst | `checklists/FRONTEND-FEATURE.md`, `process/ACCESSIBILITY.md` |
| einen Bug behebst | `checklists/BUG-FIX.md` |
| eine Änderung reviewst | `checklists/CODE-REVIEW.md` |
| `qr/make_qr.py` änderst | `stacks/PYTHON.md` |

## Konventionen

- Schemaänderungen als Migration, und dieselbe Datei unter `supabase/migrations/`
  committen, Name `<version>_<name>.sql` wie in `supabase_migrations.schema_migrations`.
- Nach einem Deploy der Edge Function prüfen, dass deployte Version und Repo gleich sind.
- Commit-Messages auf Deutsch, ein Satz, der sagt, was sich für Gäste oder Auswertung ändert.

## Bekannte offene Risiken

- **Zuordnung ist systematisch um eins daneben** (September 2026): bewertet ein Gast
  direkt nach seiner Stunde, gilt noch der Kurs davor als zuletzt beendet. Lösung
  gehört hierher: Gast wählt Kurs oder Lehrkraft, oder der laufende Kurs zählt als
  Kandidat. Das PayScale Dashboard hat nur eine Prüfliste als Netz.
- **Sprache und Ticker hängen am Slug** in `index.html`: Englisch nur für `berlin-`,
  Banner über `TICKER_BANNERS`. Bei neuen Städten oder Openings von Hand anpassen.
- **Grundtabellen ohne Migration angelegt** (Mai 2026). `supabase/schema.sql` ist
  eine Momentaufnahme, keine Wiederherstellung.
