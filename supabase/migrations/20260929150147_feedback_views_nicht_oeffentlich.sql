-- Die Views liefen mit den Rechten ihres Besitzers (postgres) und umgingen damit
-- RLS auf feedback. Mit dem oeffentlichen Anon Key waren alle Bewertungen samt
-- Kommentaren lesbar. Kein Code nutzt die Views ueber anon oder authenticated.
alter view public.feedback_by_studio set (security_invoker = true);
alter view public.feedback_summary set (security_invoker = true);
revoke all on public.feedback_by_studio from anon, authenticated;
revoke all on public.feedback_summary from anon, authenticated;
