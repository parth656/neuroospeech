-- ================================================================
-- NeuroSpeech Therapy — Supabase Schema
-- Paste this entire file into Supabase → SQL Editor → Run
-- ================================================================

-- ── PROFILES (auto-created on sign-up) ──────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id              UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email           TEXT        NOT NULL,
  full_name       TEXT,
  role            TEXT        NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  total_sessions  INTEGER     NOT NULL DEFAULT 0,
  streak_days     INTEGER     NOT NULL DEFAULT 0,
  last_practice   DATE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-create profile when user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email,'@',1))
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ── SESSIONS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.sessions (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  module         TEXT        NOT NULL,
  target_phrase  TEXT        NOT NULL,
  spoken_text    TEXT        NOT NULL,
  accuracy       REAL        NOT NULL CHECK (accuracy BETWEEN 0 AND 100),
  speech_rate    REAL,
  ai_feedback    TEXT,
  audio_path     TEXT,
  duration_secs  REAL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON public.sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_module ON public.sessions(module);


-- ── STREAKS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.streaks (
  user_id        UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  current_streak INTEGER     NOT NULL DEFAULT 0,
  longest_streak INTEGER     NOT NULL DEFAULT 0,
  last_activity  DATE,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Realtime on streaks (live leaderboard)
ALTER PUBLICATION supabase_realtime ADD TABLE public.streaks;
ALTER PUBLICATION supabase_realtime ADD TABLE public.sessions;


-- ── ROW LEVEL SECURITY ──────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.streaks   ENABLE ROW LEVEL SECURITY;

-- Helper function
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN LANGUAGE sql SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

-- profiles
CREATE POLICY "own profile"         ON public.profiles FOR ALL    USING (auth.uid() = id);
CREATE POLICY "admin read profiles" ON public.profiles FOR SELECT USING (public.is_admin());

-- sessions
CREATE POLICY "own sessions"        ON public.sessions FOR ALL    USING (auth.uid() = user_id);
CREATE POLICY "admin read sessions" ON public.sessions FOR SELECT USING (public.is_admin());

-- streaks (public for leaderboard read)
CREATE POLICY "own streaks"         ON public.streaks  FOR ALL    USING (auth.uid() = user_id);
CREATE POLICY "public read streaks" ON public.streaks  FOR SELECT USING (TRUE);


-- ── STORAGE BUCKET ──────────────────────────────────────────────
INSERT INTO storage.buckets (id, name, public)
VALUES ('audio-recordings', 'audio-recordings', false)
ON CONFLICT DO NOTHING;

CREATE POLICY "users upload own audio"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'audio-recordings'
    AND auth.uid()::text = split_part(name, '/', 1));

CREATE POLICY "users read own audio"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'audio-recordings'
    AND auth.uid()::text = split_part(name, '/', 1));


-- ── STREAK UPDATE FUNCTION ───────────────────────────────────────
CREATE OR REPLACE FUNCTION public.update_streak(p_user_id UUID)
RETURNS INTEGER LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_today  DATE := CURRENT_DATE;
  v_last   DATE;
  v_cur    INTEGER;
  v_long   INTEGER;
BEGIN
  SELECT last_activity, current_streak, longest_streak
    INTO v_last, v_cur, v_long
    FROM public.streaks WHERE user_id = p_user_id;

  IF NOT FOUND THEN
    INSERT INTO public.streaks(user_id, current_streak, longest_streak, last_activity)
    VALUES (p_user_id, 1, 1, v_today);
    v_cur := 1;
  ELSIF v_last = v_today THEN
    NULL; -- already practiced today
  ELSIF v_last = v_today - 1 THEN
    v_cur  := v_cur + 1;
    v_long := GREATEST(v_long, v_cur);
    UPDATE public.streaks
      SET current_streak = v_cur, longest_streak = v_long,
          last_activity = v_today, updated_at = NOW()
      WHERE user_id = p_user_id;
  ELSE
    v_cur := 1;
    UPDATE public.streaks
      SET current_streak = 1, last_activity = v_today, updated_at = NOW()
      WHERE user_id = p_user_id;
  END IF;

  UPDATE public.profiles
    SET total_sessions = total_sessions + 1,
        streak_days    = v_cur,
        last_practice  = v_today
    WHERE id = p_user_id;

  RETURN v_cur;
END;
$$;


-- ── LEADERBOARD VIEW ────────────────────────────────────────────
CREATE OR REPLACE VIEW public.leaderboard AS
SELECT
  p.full_name,
  s.current_streak,
  s.longest_streak,
  p.total_sessions
FROM public.profiles p
JOIN public.streaks   s ON s.user_id = p.id
ORDER BY s.current_streak DESC, p.total_sessions DESC
LIMIT 20;

GRANT SELECT ON public.leaderboard TO anon, authenticated;
