# Lightsail deploy

Publish a FastAPI **status app** (latest Chicago pulse CSV + optional Fabric embed) to the same Lightsail box as WordPress.

## Quick start (from monorepo root)

```powershell
python deploy_pulsegrid.py --from-dotenv
python enable_pulsegrid_public.py   # Route 53 + Apache vhost + pulsegrid.env (repo root)
```

Uses **SSH_HOST**, **SSH_USER**, **SSH_KEY_FILE** / **SSH_KEY_CONTENT** from the parent `.env`.

Or from `aq-pulsegrid/`:

```powershell
python tools/deploy_pulsegrid_lightsail.py --from-dotenv
```

## Public URLs

| URL | Notes |
|-----|--------|
| `http://pulse.aureaquantra.com/` | Apache vhost → FastAPI (after Route 53 A record) |
| `http://<ip>:5190/` | Direct; open TCP **5190** in Lightsail networking |

**Apache vhost is installed** on the WordPress Lightsail box. Create Route 53 **`pulse` → A → `3.151.204.177`** (or run `enable_pulsegrid_public.py` when IAM allows Route 53).

IAM user `aq-lightsail-deploy-read` is read-only today — attach **`iam-policy-lightsail-port-open.example.json`** and **`iam-policy-route53-pulse-dns.example.json`** for full automation, or use the Lightsail console for port **5190**.

## What gets deployed

| Piece | Remote path |
|-------|-------------|
| FastAPI app | `/var/aq-pulsegrid/status_app.py` |
| Sample CSVs | `/var/aq-pulsegrid/data/*.csv` |
| systemd unit | `aq-pulsegrid.service` → port **5190** |

After deploy:

- Health: `http://<lightsail-ip>:5190/health`
- UI: `http://<lightsail-ip>:5190/`

Open **TCP 5190** in Lightsail networking if the port is not reachable externally.

## Optional

- **secrets/pulsegrid.env** — `POWERBI_PULSEGRID_EMBED_URL`, `OPENAI_API_KEY` (see `secrets/pulsegrid.env.example`)
- **nginx-aq-pulsegrid.conf** — proxy `pulse.aureaquantra.com:8080` → `127.0.0.1:5190`
- **iam-policy-*.json** — IAM examples for resolving instance IP and Route53 `pulse` subdomain

## Files (gitignored)

- `deploy.config.env` — copy from `deploy.config.example.env`
- `secrets/lightsail-key.pem`
