# 🩺 NeuroSpeech — AI Speech Therapy Platform

> **Built for the Supabase Partner Program**
> Showcases: Auth · PostgreSQL + RLS · Realtime · Storage · Edge Functions

---

## Features

| Feature | Supabase Service Used |
|---|---|
| Email + Google login | **Supabase Auth** |
| Session history per user | **PostgreSQL + RLS** (users only see their own data) |
| Live leaderboard | **Realtime** subscriptions |
| Audio recordings saved | **Supabase Storage** |
| AI therapy feedback | **Edge Functions** (Deno) |
| Weekly progress report | **Edge Functions** (Deno) |
| Admin panel | **Service Role** + RLS `is_admin()` |
| Daily streak tracking | **PostgreSQL function** |

---

## Setup — 5 Steps

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com) → New Project
2. Pick a name, set a database password, choose a region

### 2. Run the Schema
1. In Supabase: **SQL Editor** → **New Query**
2. Paste everything from `schema.sql`
3. Click **Run**

### 3. Enable Google OAuth (optional but impressive for demos)
1. Supabase → **Authentication** → **Providers** → **Google**
2. Paste your Google Client ID + Secret from [console.cloud.google.com](https://console.cloud.google.com)
3. Add your site URL to: Authentication → URL Configuration

### 4. Get Your Keys
Supabase → **Project Settings** → **API**
- Copy `SUPABASE_URL`
- Copy `anon / public` key → `SUPABASE_ANON_KEY`
- Copy `service_role` key → `SUPABASE_SERVICE_KEY`

### 5. Run Locally
```bash
# Clone / copy files
cd neurospeech

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in your Supabase values

# Run
streamlit run app.py
```

---

## Deploy Edge Functions

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to your project
supabase link --project-ref your-project-id

# Deploy both functions
supabase functions deploy analyze-speech
supabase functions deploy progress-report

# Set secrets (if using OpenAI)
supabase secrets set OPENAI_API_KEY=sk-...
```

> **Works without OpenAI** — smart fallback feedback is built in so your demo runs immediately.

---

## Deploy to Streamlit Cloud (free live demo URL)

1. Push code to a **public GitHub repo**
2. Go to [share.streamlit.io](https://share.streamlit.io) → New App
3. Select your repo + `app.py`
4. Under **Advanced → Secrets**, paste your secrets from `.streamlit/secrets.toml`
5. Click Deploy → get your live URL ✅

---

## Make Yourself Admin

In Supabase → SQL Editor:
```sql
UPDATE public.profiles
SET role = 'admin'
WHERE email = 'your@email.com';
```

---

## Supabase Partner Application Checklist

- [x] Auth integration (email + Google OAuth)
- [x] PostgreSQL with Row Level Security (users only see own data)
- [x] Realtime subscriptions (leaderboard + streak updates)
- [x] Storage (audio recordings per user)
- [x] Edge Functions (AI feedback + progress reports)
- [x] Database functions (streak tracking)
- [x] Admin panel using service role
- [x] Live demo URL (Streamlit Cloud)
- [x] Public GitHub repo

---

## File Structure

```
neurospeech/
├── app.py                          ← Main Streamlit app (all pages)
├── schema.sql                      ← Run once in Supabase SQL Editor
├── requirements.txt
├── .env.example
├── .streamlit/
│   └── secrets.toml                ← For Streamlit Cloud deploy
└── supabase/
    └── functions/
        ├── analyze-speech/
        │   └── index.ts            ← AI coaching feedback
        └── progress-report/
            └── index.ts            ← Weekly progress summary
```
# neuroospeech
