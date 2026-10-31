# Deploying to DigitalOcean App Platform

The app runs as one Docker container (gunicorn) on DigitalOcean App
Platform. Postgres is on Neon's free tier (DigitalOcean's $7 dev database
can't be used: its `db` user has no CREATE rights and DO exposes no admin
login to grant them). Media lives in DigitalOcean Spaces, email goes out
through Brevo. The App Platform spec is in `.do/app.yaml`.

## One-time setup

### 0. Rotate secrets that lived on Railway

Do this before anything else; Railway's October 2026 incident may have
exposed every environment variable stored there.

- **Brevo**: SMTP & API → API Keys → delete the old key, create a new one.
- **Spaces**: API → Spaces Keys → delete the old key pair, generate a new one.
- **Django SECRET_KEY**: generate a fresh one:
  `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`
- **Admin passwords**: reset any Django admin user passwords after cutover.

### 1. Authenticate doctl

```sh
doctl auth init          # paste a personal access token from cloud.digitalocean.com/account/api/tokens
doctl account get        # should print your account, not a 401
```

### 2. Connect GitHub

App Platform needs permission to read `codefordayton/artaroundtown`.
Dashboard → Apps → Create App → GitHub → install/authorize the
DigitalOcean GitHub app for that org. (Only needed once per account.)

### 3. Create the Neon database

1. Sign up at neon.tech, create a project. Pick region **AWS us-east-2
   (Ohio)**: closest to DO's nyc region and to Dayton.
2. On the project dashboard click **Connect**, choose the *direct*
   connection (not pooled), and copy the `postgresql://...?sslmode=require`
   string. That is `DATABASE_URL`.

### 4. Create the app from the spec

```sh
doctl apps spec validate .do/app.yaml
doctl apps create --spec .do/app.yaml
doctl apps list                          # grab the app ID
```

The spec creates the web service and a pre-deploy `migrate` job. Every
`"set me"` value is a placeholder: fill them in
under Apps → artaroundtown → Settings → (component) → Environment
Variables, or edit `.do/app.yaml` locally (never commit real secrets) and
run `doctl apps update <app-id> --spec .do/app.yaml`.

Required secrets: `DATABASE_URL` (on **both** the web service and the
migrate job), `SECRET_KEY` (both), `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`,
`S3_BUCKET_NAME`, `BREVO_API_KEY`. The spec references `${APP_DOMAIN}` so
the auto-generated `*.ondigitalocean.app` hostname is allowed from the
first deploy.

Spaces notes: the Space must already exist. If you enable the Spaces CDN,
set `S3_CUSTOM_DOMAIN` to `<space>.nyc3.cdn.digitaloceanspaces.com`.

### 5. Move the data

If the Railway Postgres holds data worth keeping (anything beyond what
`import_calendar` and `import_venues` can regenerate):

```sh
# Railway: service → Connect → copy the public DATABASE_URL (TCP proxy)
pg_dump --no-owner --no-acl -Fc "$RAILWAY_DATABASE_URL" -f artaroundtown.dump

# Neon: the same DATABASE_URL you put in App Platform
pg_restore --no-owner --no-acl --clean --if-exists \
  -d "$NEON_DATABASE_URL" artaroundtown.dump
```

`pg_restore` may print a handful of "does not exist" notices from `--clean`
on a fresh database; those are harmless. Run the restore *after* the first
deploy so the `migrate` job has already created the schema, or run it before
and let `migrate` no-op. Either order works.

If there is nothing to keep, skip this and re-run the importers after
deploy (step 6).

### 6. Point the domain

Apps → artaroundtown → Settings → Domains → Add Domain →
`artaroundtowndayton.org` (and `www`). DigitalOcean shows the CNAME /
A records to add at the registrar and issues the TLS certificate once DNS
resolves. Propagation is usually minutes, up to a few hours.

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in the spec already include the
real domain.

### 7. Post-deploy

```sh
doctl apps list                               # confirm ACTIVE
doctl apps logs <app-id> web --type run       # tail the app
doctl apps console <app-id> web               # shell into the container
```

From the console (or a one-off job):

```sh
python manage.py createsuperuser
python manage.py import_venues ...            # if not restoring the DB
python manage.py import_calendar ...
```

### 8. Venue cleanup (one-off, after the Oct 2026 feedback)

Duplicate venues and address fixes live in `data/venue_cleanup.yaml`.
From the app console, preview then apply:

```sh
python manage.py merge_venues data/venue_cleanup.yaml --dry-run
python manage.py merge_venues data/venue_cleanup.yaml
```

Events on an absorbed duplicate move to the kept venue, whose slug (and
URL) stays the same. Edit the YAML to change the final names/addresses
before applying; the command is safe to re-run.

## Day-to-day

- Push to `main` → App Platform builds the Dockerfile, runs the `migrate`
  job, then swaps in the new container. Failed migrations block the deploy.
- `doctl apps logs <app-id> web` for runtime logs, `--type build` for builds.
- Static files are collected at image build time and served by WhiteNoise.
- Health check is `/health/`, answered by `config.middleware.HealthCheckMiddleware`
  before host validation, so the platform's checker needs no ALLOWED_HOSTS entry.

## Cost and upgrade path

| Component | Slug / tier | Approx. monthly |
|---|---|---|
| Web container | `apps-s-1vcpu-0.5gb` | $5 |
| Postgres | Neon free tier | $0 |
| Spaces | existing | $5 (250 GB incl.) |

Neon's free tier gives 0.5 GB of storage and suspends compute after a few
minutes idle; the first request afterward takes about half a second while
it wakes. Point-in-time restore on the free tier covers only a short
window, so if the data becomes the source of truth, schedule a weekly
`pg_dump` somewhere or move to Neon's paid tier or DO managed Postgres
($15/mo).

## Local Docker check

```sh
docker build -t artaroundtown .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=sqlite://:memory: -e SECRET_KEY=dev -e ALLOWED_HOSTS=localhost \
  artaroundtown
curl -i localhost:8000/health/
```
