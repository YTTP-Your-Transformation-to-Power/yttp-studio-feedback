# YTTP Studio Feedback

QR-Code-Feedback für die YTTP Studios. Gäste scannen nach dem Kurs einen Aushang,
bewerten auf `feedback.yttp.de` und die Bewertung wird automatisch dem Kurs und der
Lehrkraft zugeordnet, die zuletzt im Studio unterrichtet hat.

## Wie es zusammenhängt

```
QR-Aushang  ->  feedback.yttp.de/?studio=<slug>   (index.html, GitHub Pages)
                  |  liest studios, schreibt feedback (Anon Key, RLS)
                  v
            Supabase "feedback loop studios" (sjnrqfqjfqpdjhukgiue)
                  |  Edge Function attribute-teacher
                  v
            bsport: zuletzt beendeter Kurs an der Venue -> Lehrkraft

Gelesen von:  PayScale Dashboard (Service Key, inkl. Kommentare)
              Management Dashboard (export_for_management, ohne Kommentare)
```

## Inhalt

| Pfad | Was |
|---|---|
| `index.html` | Das Formular. Einzige Seite, die Gäste sehen. |
| `CNAME` | Custom Domain für GitHub Pages. Nicht löschen. |
| `qr/make_qr.py` | Erzeugt das A4-Aushang-PDF pro Studio. |
| `qr/pdf/` | Die gedruckten Aushänge, einer pro Studio. |
| `supabase/functions/attribute-teacher/` | Quelle der Edge Function zur Lehrer-Zuordnung. |
| `supabase/schema.sql` | Stand der Tabellen, Policies und Views zum Nachlesen. |
| `supabase/migrations/` | Schemaänderungen ab 29. September 2026. |
| `docs/NEUES-STUDIO.md` | **Ablauf für ein neues Studio.** |

## Betrieb

- **Deploy:** Push auf `main` veröffentlicht `index.html` über GitHub Pages
  (Legacy Build, Branch `main`, Wurzel). Kein Build-Schritt.
- **DNS:** bei IONOS. `feedback.yttp.de` ist ein CNAME auf `yttp-your-transformation-to-power.github.io`.
  `yttp.de` ist in der GitHub Organisation als Pages Domain verifiziert (TXT Eintrag
  `_github-pages-challenge-YTTP-Your-Transformation-to-Power`, seit 29. September 2026).
  Den TXT Eintrag nie löschen, sonst fällt die Verifizierung weg.
- **Edge Function:** wird nicht automatisch aus dem Repo deployt. Änderungen hier
  committen und über Supabase deployen (MCP `deploy_edge_function` oder
  `supabase functions deploy attribute-teacher`). Danach prüfen, dass Repo und
  deployte Version übereinstimmen.
- **Secrets:** `BSPORT_API_KEY` liegt nur in den Function Secrets von Supabase.

## Studios

Aktueller Bestand in der Tabelle `studios`, Stand 29. September 2026:

| Slug | bsport Company | bsport Venue |
|---|---|---|
| `berlin-bkiez-ref` | 3984 | 18751 |
| `berlin-cburg-ref` | 3984 | 16151 |
| `berlin-fhain-ref` | 3984 | 18750 |
| `berlin-rberger-ref` | 3984 | 13580 |
| `duesseldorf-bilk-ref` | 5546 | 21091 |
| `hamburg-nstadt-ref` | 5547 | 18529 |
| `koeln-belgisches-mat` | 2562 | 9160 |
| `koeln-belgisches-ref` | 2562 | 12525 |
| `koeln-belgisches-strength` | 2562 | 19028 |
| `koeln-suedstadt-ref` | 2562 | 13181 |

Maßgeblich ist immer die Tabelle, nicht diese Liste.
