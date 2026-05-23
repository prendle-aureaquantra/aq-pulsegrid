# Lightsail deploy secrets

- **lightsail-key.pem** — SSH private key (from parent repo `.env` `SSH_KEY_*` via prepare script).
- **pulsegrid.env** — optional runtime env (`POWERBI_PULSEGRID_EMBED_URL`, `OPENAI_API_KEY`).

Never commit real keys or tokens.
