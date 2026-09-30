-- Stand des Feedback-Schemas im Supabase-Projekt "feedback loop studios"
-- (sjnrqfqjfqpdjhukgiue), am 29. September 2026 aus der Datenbank gelesen,
-- nachgezogen am 30. September 2026 (questions entfernt).
--
-- Das ist eine Momentaufnahme zum Nachlesen, keine Migration zum Ausfuehren.
-- Die Grundtabellen wurden im Mai 2026 im Supabase-Dashboard angelegt, nicht
-- per Migration. Aenderungen seitdem stehen in supabase_migrations.schema_migrations
-- und ab jetzt als Datei unter supabase/migrations/.
--
-- Nicht Teil dieses Projekts: die Tabellen bcn_* im selben Supabase-Projekt
-- gehoeren zum Live-Tool des KI-Workshops Barcelona. Sie werden nach dem
-- Workshop (2. Oktober 2026) geloescht, siehe Teardown-Plan des Workshops.

-- Studios: eine Zeile pro QR-Code. Der Slug steht im gedruckten Code und darf
-- sich danach nie mehr aendern.
create table public.studios (
  id                uuid primary key default gen_random_uuid(),
  slug              text not null unique,   -- stadt-standort-typ, z.B. koeln-suedstadt-ref
  name              text not null,          -- 'YTTP Köln – Südstadt – Reformer'
  type              text not null,          -- reformer | matten | functional
  google_review_url text,                   -- Weiterleitung bei 5 Sternen
  bsport_venue_id   integer,                -- ohne Venue keine Lehrer-Zuordnung
  bsport_company_id integer                 -- bsport Branch der Stadt
);

create table public.feedback (
  id                          uuid primary key default gen_random_uuid(),
  created_at                  timestamptz default now(),
  studio_id                   uuid references public.studios(id),
  studio_slug                 text,
  stars                       integer check (stars >= 1 and stars <= 5),
  answer_1                    text,   -- Check-in
  answer_2                    text,   -- Sauberkeit
  answer_3                    text,   -- Kurs
  answer_4                    text,   -- ungenutzt, immer leer; bleibt, weil index.html
  answer_5                    text,   -- sie noch mit null sendet (siehe CLAUDE.md)
  comment                     text,   -- Freitext, verlaesst dieses Projekt nie
  bsport_teacher_id           integer,
  bsport_class_id             integer,
  bsport_class_started_at     timestamptz,
  attribution_status          text,   -- matched | no_venue_mapping | no_class_found | bsport_not_configured
                                      -- | auto_corrected_by_name | manually_corrected | confirmed_correct
  bsport_teacher_id_original  integer -- Zuordnung vor einer Korrektur
);

-- Token-Hashes der Systeme, die export_for_management() aufrufen duerfen.
create table public.export_clients (
  name         text primary key,
  token_sha256 text not null,
  created_at   timestamptz not null default now(),
  last_used_at timestamptz,
  note         text
);

-- RLS: der Anon Key steht oeffentlich in index.html. Er darf Studios lesen
-- und Feedback einfuegen, sonst nichts.
alter table public.studios        enable row level security;
alter table public.feedback       enable row level security;
alter table public.export_clients enable row level security;

create policy "public read studios"    on public.studios   for select using (true);
create policy "public insert feedback" on public.feedback  for insert with check (true);
-- Bewusst keine SELECT-Policy auf feedback und keine Policy auf export_clients.

-- Hoechstens 60 Bewertungen pro Studio und Stunde.
create or replace function public.check_feedback_rate_limit()
returns trigger language plpgsql security definer as $$
declare
  recent_count integer;
begin
  select count(*) into recent_count
  from feedback
  where studio_slug = new.studio_slug
    and created_at > now() - interval '1 hour';
  if recent_count >= 60 then
    raise exception 'Rate limit exceeded: too many submissions for this studio.';
  end if;
  return new;
end;
$$;

create trigger feedback_rate_limit_trigger
  before insert on public.feedback
  for each row execute function public.check_feedback_rate_limit();

-- Views fuer Auswertungen im Supabase-Dashboard. Seit 29. September 2026 mit
-- security_invoker und ohne Rechte fuer anon/authenticated, siehe
-- migrations/20260929150147_feedback_views_nicht_oeffentlich.sql.
create view public.feedback_by_studio with (security_invoker = true) as
  select s.name as studio, s.slug as studio_slug, s.type as studio_type,
         f.created_at, f.stars, f.answer_1, f.answer_2, f.answer_3,
         f.answer_4, f.answer_5, f.comment
  from feedback f join studios s on s.id = f.studio_id
  order by f.created_at desc;

create view public.feedback_summary with (security_invoker = true) as
  select s.name as studio, s.type as typ, date(f.created_at) as datum,
         round(avg(f.stars), 2) as durchschnitt_sterne, count(*) as anzahl_feedbacks
  from feedback f join studios s on f.studio_id = s.id
  group by s.name, s.type, date(f.created_at)
  order by date(f.created_at) desc;

-- Leseschnittstelle fuer das Management Dashboard (Projekt qxncnitxucqqycsvztsq):
-- public.export_for_management(p_token text, p_since timestamptz)
-- Gibt Feedback OHNE Freitext heraus, nur mit gueltigem Token. Der Klartext des
-- Tokens liegt im Vault des Management-Projekts, hier nur der SHA-256-Hash.
-- Vollstaendige Definition: Repo Management-Dashboard,
-- supabase/external/feedback-project/export_for_management.sql
