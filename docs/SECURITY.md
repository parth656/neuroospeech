# NeuroSpeech Security Checklist

This application uses authentication, database policies, storage, and server-side functions. Review these controls before deploying a public instance.

## Secrets

- Never commit Supabase service-role keys, database passwords, OAuth client secrets, or AI provider keys.
- Keep service-role credentials only in trusted server-side environments.
- Use placeholder values in `.env.example`.
- Rotate any credential that has appeared in source control or logs.

## Authorization

- Enable and test Row Level Security for every table containing user data.
- Test reads and writes using two separate non-admin accounts.
- Restrict audio Storage policies so one user cannot read or overwrite another user's files.
- Keep admin authorization server-side and validate roles from trusted database state.
- Never rely on a hidden UI element as an authorization boundary.

## Audio and personal data

Obtain appropriate consent, document retention, and provide deletion behavior. Avoid logging recordings or sensitive transcripts unnecessarily.

## Deployment

Use separate development and production Supabase projects. Review schema changes, OAuth redirect URLs, Edge Function permissions, and secrets before deploying.
