# NeuroSpeech — AI Speech Practice Platform

NeuroSpeech is a speech-practice application that combines a Streamlit interface with Supabase services for authentication, user-specific session history, storage, realtime updates, and Edge Functions for feedback and progress summaries.

> This is a practice aid, not a clinical diagnostic system. AI feedback may be wrong and should not replace a qualified speech-language pathologist.

## Features documented by the project

| Feature | Component |
|---|---|
| Email and optional Google login | Supabase Auth |
| Per-user session history | PostgreSQL with Row Level Security (RLS) |
| Realtime progress/leaderboard updates | Supabase Realtime |
| Audio recording storage | Supabase Storage |
| Speech feedback and weekly progress | Supabase Edge Functions |
| Streak tracking | PostgreSQL function |
| Admin workflows | Role checks and database policies |

Verify each feature against the deployed version before presenting it as production-ready.

## Requirements

- Python and the version supported by `requirements.txt`
- Supabase project
- Supabase CLI for Edge Function deployment
- Optional AI provider key if enabled by the implementation

## Setup

1. Create a Supabase project.
2. Review `schema.sql` and apply it to a development project.
3. Configure Auth providers and redirect URLs.
4. Copy `.env.example` to `.env` and set the required values.
5. Install dependencies and launch the app:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Use the exact variable names from `.env.example`; never paste real credentials into source files.

## Supabase Edge Functions

The documented functions are `analyze-speech` and `progress-report`. Install and authenticate the Supabase CLI, link the development project, then deploy the functions using the commands supported by the checked-in Supabase configuration.

## Critical security guidance

- Never expose the Supabase service-role key in browser code or a public repository.
- Store service-role credentials only in trusted server-side secrets.
- Enforce RLS for every table containing user data and test cross-user access.
- Restrict Storage policies so users cannot read or overwrite another user's recordings.
- Do not make a user an admin solely by running a public client-side action.
- Keep production and development projects separate; test schema changes before applying them to production.
- Document audio retention, deletion, and consent clearly.

## Validation checklist

- [ ] Test login, logout, and OAuth redirects.
- [ ] Verify RLS and Storage isolation using two different accounts.
- [ ] Test Edge Function errors and missing AI credentials.
- [ ] Confirm data deletion and backup/restore behavior.
- [ ] Add screenshots and an architecture diagram.
- [ ] Record deployment instructions and known limitations.

## Project layout

The existing README identifies `app.py`, `schema.sql`, `requirements.txt`, `.env.example`, Streamlit configuration, and Supabase Edge Functions as key files. Check the repository tree for the current exact structure.
