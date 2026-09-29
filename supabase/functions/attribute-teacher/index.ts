import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

// Ordnet einen Feedback-Eintrag dem zuletzt beendeten Kurs (und damit dem
// tatsaechlich unterrichtenden Lehrer, auch bei Vertretung) an der jeweiligen
// bSport-Venue zu. Wird von index.html direkt nach dem Speichern eines
// Feedbacks aufgerufen. bSport-Zugangsdaten liegen ausschliesslich als
// Function-Secrets vor, nie im Client-Code.
//
// WICHTIG: GET /classes/ kennt keinen \"ordering\"-Parameter (gegen das
// offizielle Schema verifiziert -- page, page_size, period_start, period_end,
// service_id, teacher_id, venue_id sind die einzigen Filter). Die Antwort
// kommt also in einer nicht garantierten Reihenfolge zurueck. Deshalb NIE nur
// den ersten Treffer nehmen, sondern immer explizit ueber alle Seiten das
// Maximum nach starts_at selbst bestimmen.
//
// WICHTIG (CORS): Diese Funktion wird direkt aus dem Browser heraus von
// feedback.yttp.de aufgerufen (anderer Origin als supabase.co). Browser
// schicken davor automatisch einen OPTIONS-Preflight-Request mit den
// tatsaechlich genutzten Headern (apikey, authorization, content-type).
// Ohne eine explizite OPTIONS-Antwort mit den passenden
// Access-Control-Allow-*-Headern schlaegt der Preflight fehl und der Browser
// sendet den eigentlichen POST-Request gar nicht erst ab -- das fuehrt zu
// einem stillen \"Failed to fetch\" ohne Server-Log fuer den POST selbst.
// Die CORS-Header muessen ausserdem auf JEDER Antwort (auch der echten
// POST-Antwort) gesetzt sein, nicht nur auf der OPTIONS-Antwort.

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

const BSPORT_BASE = "https://public.production.bsport.io";
const MAX_PAGES = 10;

interface RequestBody {
  feedback_id?: number;
  studio_slug?: string;
  submitted_at?: string;
}

interface BsportClass {
  id: number;
  teacher_id: number;
  starts_at: string;
  duration_in_minutes: number | null;
  is_cancelled: boolean;
}

async function fetchAllClasses(
  venueId: number,
  headers: Record<string, string>,
  periodStart: string,
  periodEnd: string,
): Promise<BsportClass[]> {
  const all: BsportClass[] = [];
  let page = 1;
  while (page <= MAX_PAGES) {
    const url =
      `${BSPORT_BASE}/api/v1/management/classes/?venue_id=${venueId}` +
      `&period_start=${encodeURIComponent(periodStart)}&period_end=${encodeURIComponent(periodEnd)}` +
      `&page=${page}&page_size=100`;
    const res = await fetch(url, { headers });
    if (!res.ok) break;
    const json = await res.json();
    const results: BsportClass[] = json.results ?? [];
    all.push(...results);
    if (!json.next || results.length === 0) break;
    page++;
  }
  return all;
}

// Findet unter den (nicht stornierten, bereits beendeten) Kursen denjenigen
// mit dem spaetesten Startzeitpunkt -- explizit selbst berechnet, nicht auf
// die Reihenfolge der API-Antwort verlassen.
function pickMostRecentCompleted(classes: BsportClass[], submittedAtMs: number): BsportClass | null {
  let best: BsportClass | null = null;
  let bestStartMs = -Infinity;
  for (const cls of classes) {
    if (cls.is_cancelled) continue;
    const startMs = new Date(cls.starts_at).getTime();
    const endMs = startMs + (cls.duration_in_minutes ?? 0) * 60 * 1000;
    if (endMs <= submittedAtMs && startMs > bestStartMs) {
      best = cls;
      bestStartMs = startMs;
    }
  }
  return best;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: CORS_HEADERS });
  }

  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  let body: RequestBody;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const { feedback_id, studio_slug, submitted_at } = body;
  if (!feedback_id || !studio_slug || !submitted_at) {
    return jsonResponse({ error: "Missing feedback_id, studio_slug, or submitted_at" }, 400);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const supabase = createClient(supabaseUrl, serviceKey);

  const { data: studio, error: studioErr } = await supabase
    .from("studios")
    .select("bsport_venue_id, bsport_company_id")
    .eq("slug", studio_slug)
    .maybeSingle();

  if (studioErr || !studio?.bsport_venue_id || !studio?.bsport_company_id) {
    await supabase.from("feedback").update({ attribution_status: "no_venue_mapping" }).eq("id", feedback_id);
    return jsonResponse({ status: "no_venue_mapping" }, 200);
  }

  const apiKey = Deno.env.get("BSPORT_API_KEY");
  const clientId = Deno.env.get("BSPORT_CLIENT_ID") ?? "yttp";
  const franchisorId = Deno.env.get("BSPORT_FRANCHISOR_ID") ?? "173";

  if (!apiKey) {
    await supabase.from("feedback").update({ attribution_status: "bsport_not_configured" }).eq("id", feedback_id);
    return jsonResponse({ status: "bsport_not_configured" }, 200);
  }

  const headers = {
    "X-Api-Key": apiKey,
    "X-Client-ID": clientId,
    "X-Franchisor-ID": franchisorId,
    "X-Company-ID": String(studio.bsport_company_id),
  };

  const submittedAtMs = new Date(submitted_at).getTime();
  const periodEnd = new Date(submittedAtMs).toISOString();

  let matchedClass: BsportClass | null = null;
  for (const days of [2, 30, 180]) {
    const periodStart = new Date(submittedAtMs - days * 24 * 60 * 60 * 1000).toISOString();
    const classes = await fetchAllClasses(studio.bsport_venue_id, headers, periodStart, periodEnd);
    matchedClass = pickMostRecentCompleted(classes, submittedAtMs);
    if (matchedClass) break;
  }

  if (!matchedClass) {
    await supabase.from("feedback").update({ attribution_status: "no_class_found" }).eq("id", feedback_id);
    return jsonResponse({ status: "no_class_found" }, 200);
  }

  await supabase
    .from("feedback")
    .update({
      bsport_teacher_id: matchedClass.teacher_id,
      bsport_class_id: matchedClass.id,
      bsport_class_started_at: matchedClass.starts_at,
      attribution_status: "matched",
    })
    .eq("id", feedback_id);

  return jsonResponse(
    { status: "matched", teacher_id: matchedClass.teacher_id, class_id: matchedClass.id },
    200,
  );
});
