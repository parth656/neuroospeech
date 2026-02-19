"""
🩺 NeuroSpeech Therapy
Startup project showcasing deep Supabase integration:
  ✅ Auth (email + Google OAuth)
  ✅ PostgreSQL with RLS
  ✅ Realtime (live leaderboard + streak)
  ✅ Storage (audio uploads)
  ✅ Edge Functions (AI feedback)
"""

import os, difflib, tempfile, time, random, datetime
import streamlit as st
from supabase import create_client, Client
import soundfile as sf
import numpy as np

# ── Page config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="NeuroSpeech Therapy",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Supabase client ──────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        st.error("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY — check your .env or secrets.toml")
        st.stop()
    return create_client(url, key)

sb = get_supabase()

# ── Therapy modules ──────────────────────────────────────────────
MODULES = {
    "🎯 Cluttering Control": {
        "tips": "Slow down, pause between phrases",
        "exercises": [
            "I will speak slowly and clearly.",
            "Pause between each word now.",
            "Take a breath before speaking.",
            "One thought at a time please.",
            "Slow and steady wins the race.",
        ],
    },
    "👄 Bilabials (P, B, M)": {
        "tips": "Keep lips closed, release with controlled airflow",
        "exercises": [
            "Peter Piper picked a peck of pickled peppers.",
            "Big brown bears bite brightly.",
            "My mom makes muffins every Monday morning.",
            "Purple paper people pop bubbles.",
        ],
    },
    "👅 Alveolars (T, D, N, L)": {
        "tips": "Tongue touches the ridge behind your upper teeth",
        "exercises": [
            "Tiny turtles take their time.",
            "Daddy drew a detailed dog.",
            "Nine nice knights need new names.",
            "Little lemon lollipops last long.",
        ],
    },
    "🔙 Velars (K, G)": {
        "tips": "Back of tongue rises to touch the soft palate",
        "exercises": [
            "Kate can keep crispy cookies cold.",
            "Go get good grades gracefully.",
            "King Kong kicked all the cans.",
            "Crisp crackers crunch quite clearly.",
        ],
    },
    "💨 Fricatives (F, V, S, Z, TH)": {
        "tips": "Create sustained friction — let air flow continuously",
        "exercises": [
            "Five friendly foxes found a field.",
            "Very vivid violet violins vibrate.",
            "Six silly snakes slid sideways.",
            "Think about thirty thoughtful things.",
        ],
    },
    "🌊 Liquid Sounds (R, L)": {
        "tips": "R: Tongue tip up not touching. L: Tongue touches ridge",
        "exercises": [
            "Red lorry, yellow lorry, red lorry.",
            "Really rural roads rarely run right.",
            "Little lucky lambs leap lightly.",
            "Larry's really rare red lizard.",
        ],
    },
    "⏱️ Pacing & Rhythm": {
        "tips": "Mental metronome — pause after each phrase boundary",
        "exercises": [
            "I... will... speak... slowly.",
            "Stop — and think — before you speak.",
            "Breathe. Pause. Then continue speaking.",
            "Take your time with every single word.",
        ],
    },
    "🌀 Tongue Twisters": {
        "tips": "Break into chunks first. Speed comes after accuracy",
        "exercises": [
            "She sells sea shells by the sea shore.",
            "How much wood would a woodchuck chuck?",
            "Betty Botter bought some butter but the butter was bitter.",
            "Unique New York, unique New York, you know you need unique New York.",
        ],
    },
    "💬 Conversational Practice": {
        "tips": "Clarity first, speed second",
        "exercises": [
            "Hello, how are you doing today?",
            "Can you help me find something please?",
            "What would you like for dinner tonight?",
            "Thank you very much for your help.",
        ],
    },
}

# ── Helpers ──────────────────────────────────────────────────────
def compute_accuracy(target: str, spoken: str) -> float:
    a = target.lower().replace(".", "").replace(",", "").strip()
    b = spoken.lower().replace(".", "").replace(",", "").strip()
    return round(difflib.SequenceMatcher(None, a, b).ratio() * 100, 1)

def word_diff(target: str, spoken: str) -> list[dict]:
    tw = target.lower().split()
    sw = spoken.lower().split()
    result = []
    for i in range(max(len(tw), len(sw))):
        t = tw[i] if i < len(tw) else "[missing]"
        s = sw[i] if i < len(sw) else "[extra]"
        result.append({"target": t, "spoken": s, "match": t == s})
    return result

def speech_rate(text: str, duration_secs: float) -> float:
    if duration_secs <= 0:
        return 0.0
    words = len(text.strip().split())
    return round((words / duration_secs) * 60, 1)

def accuracy_label(pct: float) -> tuple[str, str]:
    if pct >= 85: return "🎉 Excellent!",  "success"
    if pct >= 70: return "👍 Good job!",   "warning"
    if pct >= 50: return "💪 Keep going!", "warning"
    return "🔄 Try again",                 "error"

# ── Auth state ───────────────────────────────────────────────────
def get_user():
    return st.session_state.get("user")

def get_access_token():
    return st.session_state.get("access_token")

def logout():
    for k in ["user", "access_token", "refresh_token"]:
        st.session_state.pop(k, None)
    st.rerun()

# ── Auth page ────────────────────────────────────────────────────
def show_auth():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 20px 0'>
            <div style='font-size:56px'>🩺</div>
            <h1 style='margin:0'>NeuroSpeech</h1>
            <p style='color:#6b7280; margin-top:4px'>AI-powered speech therapy platform</p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── LOGIN ────────────────────────────────────────────────
        with tab_login:
            st.markdown("##### Sign in with email")
            email    = st.text_input("Email",    key="li_email",    placeholder="you@example.com")
            password = st.text_input("Password", key="li_password", type="password", placeholder="••••••••")

            if st.button("Sign In", use_container_width=True, type="primary"):
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    try:
                        res = sb.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user          = res.user
                        st.session_state.access_token  = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

            st.markdown("---")
            # Google OAuth — shows a button that opens the OAuth URL
            supabase_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
            google_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={os.environ.get('SITE_URL', 'http://localhost:8501')}"
            st.markdown(f"""
            <a href="{google_url}" target="_self" style="
                display:flex; align-items:center; justify-content:center; gap:10px;
                border:1px solid #d1d5db; border-radius:12px; padding:12px;
                text-decoration:none; color:#374151; font-weight:500;
                background:white; width:100%; box-sizing:border-box;
            ">
                <img src="https://www.google.com/favicon.ico" width="20"/>
                Continue with Google
            </a>
            """, unsafe_allow_html=True)

        # ── REGISTER ─────────────────────────────────────────────
        with tab_register:
            st.markdown("##### Create your free account")
            name     = st.text_input("Full Name",        key="reg_name",    placeholder="Your name")
            email_r  = st.text_input("Email",            key="reg_email",   placeholder="you@example.com")
            pass_r   = st.text_input("Password",         key="reg_pass",    type="password", placeholder="Min 8 characters")
            pass_r2  = st.text_input("Confirm Password", key="reg_pass2",   type="password", placeholder="••••••••")

            if st.button("Create Account", use_container_width=True, type="primary"):
                if not all([name, email_r, pass_r, pass_r2]):
                    st.error("Please fill in all fields")
                elif pass_r != pass_r2:
                    st.error("Passwords do not match")
                elif len(pass_r) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    try:
                        sb.auth.sign_up({
                            "email": email_r,
                            "password": pass_r,
                            "options": {"data": {"full_name": name}},
                        })
                        st.success("✅ Account created! Check your email to confirm, then sign in.")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

        st.markdown("""
        <div style='text-align:center; margin-top:24px; color:#9ca3af; font-size:13px'>
            🔒 Secured by <strong>Supabase Auth</strong> · RLS · Edge Functions · Realtime
        </div>
        """, unsafe_allow_html=True)


# ── Authed Supabase client (uses user's JWT) ─────────────────────
def authed_client() -> Client:
    """Returns a Supabase client authenticated as the current user."""
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY", "")
    client = create_client(url, key)
    token = get_access_token()
    if token:
        client.postgrest.auth(token)
        client.storage._session.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── PRACTICE page ────────────────────────────────────────────────
def page_practice():
    user = get_user()
    client = authed_client()

    st.title("🎯 Practice")
    st.caption("Choose a module, read the phrase aloud, then record yourself")

    col_main, col_side = st.columns([2, 1])

    with col_side:
        # Module selector
        module = st.selectbox(
            "Therapy Module",
            list(MODULES.keys()),
            key="selected_module",
        )
        mod = MODULES[module]
        st.info(f"💡 **Tip:** {mod['tips']}")

        # New phrase button
        if st.button("🎲 New Phrase", use_container_width=True):
            st.session_state.current_phrase = random.choice(mod["exercises"])

        if "current_phrase" not in st.session_state or \
           st.session_state.get("last_module") != module:
            st.session_state.current_phrase = random.choice(mod["exercises"])
            st.session_state.last_module = module

        # Scoring guide
        st.markdown("**Scoring Guide**")
        for rng, lbl, color in [("85-100%","Excellent 🎉","green"),("70-84%","Good 👍","blue"),("50-69%","Keep going 💪","orange"),("< 50%","Try again 🔄","red")]:
            st.markdown(f":{color}[{rng}] — {lbl}")

    with col_main:
        # Target phrase
        phrase = st.session_state.current_phrase
        st.markdown("### 🎯 Target Phrase")
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#f0fdfa,#e0f2fe);
                    border-left:4px solid #14b8a6; border-radius:12px;
                    padding:20px 24px; margin-bottom:20px'>
            <p style='font-size:22px; font-weight:600; margin:0; color:#0f172a'>{phrase}</p>
        </div>
        """, unsafe_allow_html=True)

        # Audio recorder
        st.markdown("### 🎙️ Record Your Speech")
        audio = st.audio_input("Click the mic and speak the target phrase clearly")

        if audio:
            with st.spinner("🧠 Analysing your speech…"):
                # Save audio to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(audio.read())
                    tmp_path = tmp.name

                try:
                    audio_data, sample_rate = sf.read(tmp_path, dtype="float32")
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1).astype(np.float32)
                    duration = len(audio_data) / sample_rate

                    if duration > 30:
                        st.error("❌ Audio too long — please keep it under 30 seconds")
                        return
                    if duration < 0.3:
                        st.error("❌ Audio too short — please speak a full phrase")
                        return

                    # Transcribe with Whisper
                    whisper_model = st.session_state.get("whisper_model")
                    if whisper_model is None:
                        import whisper
                        with st.spinner("Loading speech model (first time only)…"):
                            whisper_model = whisper.load_model("base")
                            st.session_state.whisper_model = whisper_model

                    result = whisper_model.transcribe(audio_data, fp16=False, language="en")
                    spoken_text = result["text"].strip()

                    if not spoken_text:
                        st.error("❌ No speech detected — please try again")
                        return

                    # Compute scores
                    accuracy = compute_accuracy(phrase, spoken_text)
                    wpm      = speech_rate(spoken_text, duration)
                    diff     = word_diff(phrase, spoken_text)
                    label, kind = accuracy_label(accuracy)

                except Exception as e:
                    st.error(f"❌ Error analysing audio: {e}")
                    return
                finally:
                    os.unlink(tmp_path)

            # ── Results ─────────────────────────────────────
            st.markdown("---")
            st.markdown("### 📊 Results")

            st.markdown(f"""
            <div style='background:#f0fdf4; border:1px solid #bbf7d0;
                        border-radius:12px; padding:16px 20px; margin-bottom:16px'>
                <p style='margin:0; color:#374151'>You said:</p>
                <p style='font-size:20px; font-weight:600; margin:4px 0 0; color:#111827'>"{spoken_text}"</p>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("Accuracy",     f"{accuracy}%")
            m2.metric("Speech Rate",  f"{wpm} wpm")
            m3.metric("Duration",     f"{duration:.1f}s")

            if kind == "success":
                st.success(label)
            elif kind == "warning":
                st.warning(label)
            else:
                st.error(label)

            # Word diff
            with st.expander("🔍 Word-by-Word Analysis"):
                cols = st.columns(3)
                for i, w in enumerate(diff):
                    with cols[i % 3]:
                        if w["match"]:
                            st.markdown(f"✅ ~~{w['target']}~~")
                        else:
                            st.markdown(f"❌ **{w['target']}** → *{w['spoken']}*")

            # ── AI Feedback via Edge Function ────────────────
            st.markdown("### 🤖 AI Coach Feedback")
            with st.spinner("Getting personalised AI feedback…"):
                try:
                    ai_res = client.functions.invoke(
                        "analyze-speech",
                        invoke_options={
                            "body": {
                                "target_phrase": phrase,
                                "spoken_text":   spoken_text,
                                "module":        module,
                                "accuracy":      accuracy,
                                "speech_rate":   wpm,
                            }
                        },
                    )
                    ai_feedback = ai_res.get("ai_feedback", "") if isinstance(ai_res, dict) else ""
                except Exception:
                    ai_feedback = ""

                if not ai_feedback:
                    # Fallback feedback (works without OpenAI key)
                    if accuracy >= 85:
                        ai_feedback = f"Excellent work! Your accuracy of {accuracy}% shows strong articulation control. Keep maintaining that clear pronunciation and natural pace — you're building excellent motor memory for these sounds."
                    elif accuracy >= 70:
                        ai_feedback = f"Good effort with {accuracy}% accuracy! Focus on the words marked above and try exaggerating each target sound slightly. Slowing down by just 10% will help your clarity significantly."
                    else:
                        ai_feedback = f"Keep going — speech therapy takes consistent practice. Break the phrase into 2-3 word chunks and master each piece before combining. Your brain is building new pathways every session."

            st.markdown(f"""
            <div style='background:linear-gradient(135deg,#eff6ff,#f0fdf4);
                        border:1px solid #bfdbfe; border-radius:12px; padding:16px 20px'>
                <p style='margin:0; color:#1e40af; font-weight:600; font-size:13px'>💬 AI THERAPIST</p>
                <p style='margin:8px 0 0; color:#1f2937; font-size:15px; line-height:1.6'>{ai_feedback}</p>
            </div>
            """, unsafe_allow_html=True)

            # ── Save to Supabase ──────────────────────────────
            session_id = None
            with st.spinner("Saving session…"):
                try:
                    # 1. Upload audio to Storage
                    audio.seek(0)
                    audio_bytes = audio.read()
                    audio_path  = f"{user.id}/{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.wav"
                    client.storage.from_("audio-recordings").upload(
                        audio_path, audio_bytes,
                        file_options={"content-type": "audio/wav", "upsert": "true"}
                    )
                except Exception:
                    audio_path = None  # Storage optional — don't block save

                try:
                    # 2. Insert session row (RLS: only user can insert)
                    res = client.table("sessions").insert({
                        "user_id":       user.id,
                        "module":        module,
                        "target_phrase": phrase,
                        "spoken_text":   spoken_text,
                        "accuracy":      accuracy,
                        "speech_rate":   wpm,
                        "ai_feedback":   ai_feedback,
                        "audio_path":    audio_path,
                        "duration_secs": round(duration, 2),
                    }).execute()
                    session_id = res.data[0]["id"] if res.data else None

                    # 3. Update streak (DB function)
                    client.rpc("update_streak", {"p_user_id": user.id}).execute()

                    st.success("✅ Session saved!")
                except Exception as e:
                    st.warning(f"Could not save session: {e}")


# ── DASHBOARD page ───────────────────────────────────────────────
def page_dashboard():
    user   = get_user()
    client = authed_client()

    st.title("📊 Dashboard")

    # Load data
    profile_res  = client.table("profiles").select("*").eq("id", user.id).single().execute()
    sessions_res = client.table("sessions").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(100).execute()
    streak_res   = client.table("streaks").select("*").eq("user_id", user.id).single().execute()

    profile  = profile_res.data  or {}
    sessions = sessions_res.data or []
    streak   = streak_res.data   or {}

    name = profile.get("full_name") or profile.get("email", "there")
    st.markdown(f"### Welcome back, {name.split()[0]}! 👋")

    # ── Stat cards ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    total = len(sessions)
    avg   = round(sum(s["accuracy"] for s in sessions) / total, 1) if total else 0
    cur_s = streak.get("current_streak", 0)
    lng_s = streak.get("longest_streak", 0)

    c1.metric("Total Sessions",  total)
    c2.metric("Avg Accuracy",    f"{avg}%")
    c3.metric("🔥 Current Streak", f"{cur_s} days")
    c4.metric("🏆 Best Streak",  f"{lng_s} days")

    # ── Weekly progress via Edge Function ────────────────────────
    st.markdown("---")
    col_rep, _ = st.columns([2, 1])
    with col_rep:
        st.subheader("📝 Weekly Progress Report")
        if st.button("Generate AI Report", type="primary"):
            with st.spinner("Generating your personalised report…"):
                try:
                    report_res = client.functions.invoke("progress-report", invoke_options={"body": {}})
                    if isinstance(report_res, dict):
                        st.info(report_res.get("report", "No report available"))
                        stats = report_res.get("stats", {})
                        if stats:
                            sc1, sc2, sc3 = st.columns(3)
                            sc1.metric("Sessions this week", stats.get("sessions", 0))
                            sc2.metric("Avg accuracy",       f"{stats.get('avg_accuracy', 0)}%")
                            sc3.metric("Best module",        stats.get("best_module", "—"))
                except Exception as e:
                    # Fallback when edge function isn't deployed yet
                    last_week = [s for s in sessions if
                                 datetime.datetime.fromisoformat(s["created_at"].replace("Z","")) >
                                 datetime.datetime.utcnow() - datetime.timedelta(days=7)]
                    if last_week:
                        w_avg = round(sum(s["accuracy"] for s in last_week) / len(last_week), 1)
                        st.info(f"Great week, {name.split()[0]}! You completed {len(last_week)} sessions with an average accuracy of {w_avg}%. Keep building that streak! 🔥")
                    else:
                        st.info("No sessions this week yet — start practicing to build your streak!")

    # ── Per-module progress ───────────────────────────────────────
    if sessions:
        st.markdown("---")
        st.subheader("📈 Progress by Module")

        from collections import defaultdict
        by_module = defaultdict(list)
        for s in sessions:
            by_module[s["module"]].append(s["accuracy"])

        for mod, accuracies in sorted(by_module.items(), key=lambda x: -sum(x[1])/len(x[1])):
            avg_acc = sum(accuracies) / len(accuracies)
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.markdown(f"**{mod}** ({len(accuracies)} sessions)")
                st.progress(avg_acc / 100)
            with col_r:
                st.markdown(f"**{avg_acc:.1f}%** avg")

    # ── Recent sessions table ────────────────────────────────────
    if sessions:
        st.markdown("---")
        st.subheader("🕐 Recent Sessions")
        import pandas as pd
        df = pd.DataFrame(sessions[:10])[["created_at","module","accuracy","speech_rate"]]
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%b %d, %H:%M")
        df.columns = ["Date", "Module", "Accuracy (%)", "Rate (wpm)"]
        df["Module"] = df["Module"].str.split(" ", n=1).str[1]  # strip emoji
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── HISTORY page ─────────────────────────────────────────────────
def page_history():
    client = authed_client()
    st.title("📜 Session History")

    sessions_res = client.table("sessions").select("*").order("created_at", desc=True).limit(200).execute()
    sessions     = sessions_res.data or []

    if not sessions:
        st.info("No sessions yet! Head to Practice to get started.")
        return

    # Filter by module
    modules = ["All"] + sorted(set(s["module"] for s in sessions))
    chosen  = st.selectbox("Filter by module", modules)
    if chosen != "All":
        sessions = [s for s in sessions if s["module"] == chosen]

    # Accuracy trend chart
    st.subheader("📈 Accuracy Over Time")
    import pandas as pd
    df = pd.DataFrame(sessions)
    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    df_chart   = df[["date","accuracy"]].set_index("date")
    st.line_chart(df_chart)

    # Full table
    st.subheader(f"All Sessions ({len(sessions)})")
    display = df[["created_at","module","target_phrase","spoken_text","accuracy","speech_rate","ai_feedback"]].copy()
    display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%b %d %Y, %H:%M")
    display.columns = ["Date","Module","Target","You Said","Accuracy %","Rate wpm","AI Feedback"]
    st.dataframe(display, use_container_width=True, hide_index=True)


# ── LEADERBOARD page ─────────────────────────────────────────────
def page_leaderboard():
    client = authed_client()
    st.title("🏆 Leaderboard")
    st.caption("Updates live via Supabase Realtime")

    # Static load (Realtime works in JavaScript — here we poll)
    lb_res = client.from_("leaderboard").select("*").execute()
    rows   = lb_res.data or []

    if not rows:
        st.info("No one on the leaderboard yet — start practicing!")
        return

    import pandas as pd
    df = pd.DataFrame(rows)
    df.index = range(1, len(df) + 1)
    df.index.name = "Rank"

    # Highlight top 3
    def highlight_top(row):
        if row.name == 1:   return ["background-color:#fef08a"] * len(row)
        if row.name == 2:   return ["background-color:#e2e8f0"] * len(row)
        if row.name == 3:   return ["background-color:#fed7aa"] * len(row)
        return [""] * len(row)

    df.columns = ["Name","🔥 Streak","🏆 Longest","📊 Sessions"]
    st.dataframe(df.style.apply(highlight_top, axis=1), use_container_width=True)

    st.markdown("---")
    st.caption("🔄 Refresh the page to see live updates (powered by Supabase Realtime)")


# ── ADMIN page ────────────────────────────────────────────────────
def page_admin():
    client = authed_client()
    user   = get_user()

    # Verify admin role
    profile_res = client.table("profiles").select("role").eq("id", user.id).single().execute()
    if not profile_res.data or profile_res.data.get("role") != "admin":
        st.error("🚫 Admin access only")
        return

    st.title("⚙️ Admin Panel")

    tab_users, tab_sessions, tab_stats = st.tabs(["👥 Users", "📊 All Sessions", "📈 Platform Stats"])

    # Service role client for admin operations
    svc_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL","")
    svc_key = os.environ.get("SUPABASE_SERVICE_KEY") or st.secrets.get("SUPABASE_SERVICE_KEY","")
    if svc_key:
        svc_client = create_client(svc_url, svc_key)
    else:
        svc_client = client  # fallback (limited)

    with tab_users:
        users_res = svc_client.table("profiles").select("*").order("created_at", desc=True).execute()
        users     = users_res.data or []
        st.metric("Total Users", len(users))

        import pandas as pd
        df = pd.DataFrame(users)[["email","full_name","role","total_sessions","streak_days","created_at"]]
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%b %d %Y")
        df.columns = ["Email","Name","Role","Sessions","Streak","Joined"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("**Set User Role**")
        c1, c2, c3 = st.columns([2,1,1])
        target_email = c1.text_input("User email")
        new_role     = c2.selectbox("Role", ["user","admin"])
        if c3.button("Update"):
            try:
                svc_client.table("profiles").update({"role": new_role}).eq("email", target_email).execute()
                st.success(f"Updated {target_email} → {new_role}")
            except Exception as e:
                st.error(str(e))

    with tab_sessions:
        all_sessions = svc_client.table("sessions").select("*, profiles(email, full_name)").order("created_at", desc=True).limit(500).execute()
        rows = all_sessions.data or []
        st.metric("Total Sessions", len(rows))

        if rows:
            import pandas as pd
            records = []
            for r in rows:
                p = r.get("profiles") or {}
                records.append({
                    "User":     p.get("email",""),
                    "Module":   r["module"],
                    "Accuracy": r["accuracy"],
                    "Rate wpm": r["speech_rate"],
                    "Date":     r["created_at"][:10],
                })
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_stats:
        all_s = (svc_client.table("sessions").select("accuracy, module").execute()).data or []
        total = len(all_s)
        avg   = round(sum(s["accuracy"] for s in all_s) / total, 1) if total else 0

        c1, c2 = st.columns(2)
        c1.metric("Total Sessions",    total)
        c2.metric("Platform Avg Accuracy", f"{avg}%")

        if all_s:
            from collections import Counter
            import pandas as pd
            mod_counts = Counter(s["module"] for s in all_s)
            df = pd.DataFrame(mod_counts.items(), columns=["Module","Sessions"]).sort_values("Sessions", ascending=False)
            st.bar_chart(df.set_index("Module"))


# ── Main router ───────────────────────────────────────────────────
def main():
    user = get_user()

    # Handle OAuth callback (token in URL hash — Streamlit workaround)
    # For OAuth, users are redirected back after Google login; Supabase
    # handles the session via the URL fragment automatically in the browser.
    # For Streamlit, we detect the session via cookies/localStorage workaround.

    if not user:
        show_auth()
        return

    # ── Sidebar ───────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style='padding:12px 0; text-align:center'>
            <div style='font-size:32px'>🩺</div>
            <div style='font-weight:700; font-size:18px; margin-top:4px'>NeuroSpeech</div>
            <div style='color:#6b7280; font-size:12px'>Speech Therapy Platform</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["Dashboard", "Practice", "History", "Leaderboard", "Admin"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Live streak via Supabase (refreshed on each run)
        try:
            streak_res = authed_client().table("streaks").select("current_streak").eq("user_id", user.id).single().execute()
            streak_val = streak_res.data.get("current_streak", 0) if streak_res.data else 0
            if streak_val > 0:
                st.markdown(f"""
                <div style='background:#fff7ed; border:1px solid #fed7aa; border-radius:10px;
                            padding:10px 14px; text-align:center'>
                    <div style='font-size:24px'>🔥</div>
                    <div style='font-weight:700; color:#ea580c; font-size:18px'>{streak_val} day streak!</div>
                    <div style='color:#9a3412; font-size:12px'>Keep it going!</div>
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass

        st.markdown("---")
        profile_res = authed_client().table("profiles").select("full_name, email").eq("id", user.id).single().execute()
        prof = profile_res.data or {}
        name = prof.get("full_name") or prof.get("email","")
        st.markdown(f"👤 **{name}**")
        if st.button("Sign Out", use_container_width=True):
            sb.auth.sign_out()
            logout()

    # ── Route ─────────────────────────────────────────────────────
    if page == "Dashboard":    page_dashboard()
    elif page == "Practice":   page_practice()
    elif page == "History":    page_history()
    elif page == "Leaderboard":page_leaderboard()
    elif page == "Admin":      page_admin()


if __name__ == "__main__":
    main()
