# Production deployment (Ubuntu)

The production Compose stack is isolated under project name `enbek`. It publishes
only the frontend on `127.0.0.1:3180`; PostgreSQL, Redis, SeaweedFS and Django
are reachable only within the Compose network. Do not run the development
`compose.yaml` on a shared server, because it publishes additional ports.

The application directory on the current host is `/opt/enbek/app`. Its `.env`
contains `ENBEK_DOMAIN`, `ENBEK_HTTP_PORT`, `DJANGO_SECRET_KEY`,
`POSTGRES_PASSWORD` and `S3_SECRET_KEY`; keep it mode `0600` and out of Git.
Prisoner reference images are in `/opt/enbek/app/media/prisoners/reference/`.

Start or update only this project:

```sh
cd /opt/enbek/app
docker compose -p enbek -f compose.production.yaml up -d --build
docker compose -p enbek -f compose.production.yaml ps
```

The separate Nginx vhost is `enbek.greymattergroup.org.conf`. Before public DNS and a
certificate exist, use `deploy/nginx-http.conf`: it serves ACME challenges and
returns HTTP 503 for everything else. Once `enbek.greymattergroup.org` publicly resolves
to the server, obtain a certificate without editing other virtual hosts:

```sh
certbot certonly --webroot -w /opt/enbek/acme -d enbek.greymattergroup.org \
  --cert-name enbek.greymattergroup.org --non-interactive --agree-tos \
  --deploy-hook "systemctl reload nginx"
```

Then install `deploy/nginx-https.conf` as only the Enbek vhost, run `nginx -t`,
and reload Nginx. Verify the Enbek site and existing sites afterward. Configure
Nginx reload after certificate renewal so it picks up renewed certificates.
On the shared host, the enabled link is named
`zz-enbek.greymattergroup.org.conf` so the existing LimeSurvey host remains
the default for requests without a matching TLS server name.

The biometric service is deployed separately. Public contract signing additionally
requires DNS/TLS for both domains and a real reference photo for the prisoner.

## Biometry service

The current host uses `/opt/biometry` for a separate `enbek-biometry` Compose
project. Its source is copied from the tracked Git revision into
`/opt/biometry/app`; the biometry repository itself is not edited. Deployment
files are in this repository's `deploy/biometry/` and are copied to
`/opt/biometry/compose.yaml` and `/opt/biometry/deploy/`.

```sh
cd /opt/biometry
docker compose -p enbek-biometry -f compose.yaml up -d --build
docker compose -p enbek-biometry -f compose.yaml ps
curl -fsS http://127.0.0.1:8180/ready
```

Only `127.0.0.1:8180` is published. The service joins `enbek_default` under
the alias `biometry`, so the Enbek backend uses `http://biometry:8100`.
Exactly one Uvicorn worker is required because verification sessions live in
process RAM. The VM reports an x86-64-v1 CPU; its deployment image pins NumPy
2.3.5 because the repository's NumPy 2.5.2 wheel requires x86-64-v2.

Before public DNS and TLS, `biometry.greymattergroup.org.conf` serves only ACME
challenges and returns HTTP 503. After DNS resolves, obtain a certificate with
the existing Certbot installation using webroot `/opt/biometry/acme`:

```sh
certbot certonly --webroot -w /opt/biometry/acme -d biometry.greymattergroup.org \
  --cert-name biometry.greymattergroup.org --non-interactive --agree-tos \
  --deploy-hook "systemctl reload nginx"
```

Then install `deploy/biometry/nginx-https.conf` as only the biometry vhost, test and
reload Nginx. That HTTPS vhost blocks public access to server-to-server
`/start` and `/consume`. The upstream service currently accepts only HTTP
callback configuration; the HTTPS proxy rewrites its exact callback `Location`
to `https://enbek.greymattergroup.org/biometry/callback` before it reaches the browser.
Verify this redirect and the full camera flow after both domains have TLS.
The enabled link is named `zz-biometry.greymattergroup.org.conf` for the same
default-host reason. Both certificate renewal dry-runs passed on this host.

Demo prisoner photos are placeholders. A successful face/liveness signing test
requires replacing the relevant reference photo with a real frontal image.
