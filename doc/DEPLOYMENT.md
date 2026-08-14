# Deployment

Installing, running and operating the dashboard. For what it reads see
[`DATA_CONTRACT.md`](DATA_CONTRACT.md); for how it is put together see
[`ARCHITECTURE.md`](ARCHITECTURE.md).

The deployment this document describes is uvicorn behind Apache, managed by
systemd, published under a path prefix over HTTPS:

```text
Browser -> HTTPS -> Apache -> 127.0.0.1:3000 -> uvicorn -> FastAPI
                                                    |
                                                    v
                                          <data directory> (read only)
```

---

## What this touches, and what it does not

`deploy.sh` replaces code and restarts a service. It never writes into the data
directory, and nothing in this application ever does. The pipeline owns that
directory; this side only reads it.

Deploying the dashboard therefore cannot disturb generated data, and
regenerating data never requires a deployment.

---

## Before you begin

- Python 3.9 or later.
- Apache, or any reverse proxy, terminating TLS in front of uvicorn.
- systemd.
- A data directory the service user can read. Usually this is the `finance`
  pipeline's output directory on the same host, reached through a symlink.

The pipeline does **not** have to be installed for the dashboard to start.
Pointed at an empty or absent directory it serves empty tables, which is the
right behaviour for a host where the two are deployed independently.

---

## First install

```bash
sudo mkdir -p /var/www/finance-dashboard
sudo chown "$USER" /var/www/finance-dashboard
git clone https://github.com/id774/finance-dashboard.git /var/www/finance-dashboard
cd /var/www/finance-dashboard
python3 -m venv .venv
.venv/bin/pip install .
```

Point it at the generated data:

```bash
ln -s /var/stock/data public/data
```

Or set `FINANCE_DASHBOARD_DATA_DIR` instead, which is preferable when the data
lives somewhere the web root should not link to.

Configure it:

```bash
cp config.yml.sample config.yml
chmod 600 config.yml
```

Install the unit:

```bash
sudo cp etc/finance-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finance-dashboard
```

The unit is an example. Adjust the user, the working directory, the port and the
root path before enabling it; the comments at the top of the file say which is
which.

---

## Configure

Every setting is read from the environment first and from `config.yml` second.
The full table is in the [README](../README.md#3-configuration). Three of them
decide whether the deployment is sound:

**`FINANCE_DASHBOARD_SECRET_KEY`** signs the session cookie carrying the
recently viewed codes. Unset, a key is generated per process and a warning is
logged, so every restart empties every reader's list and two workers disagree.
Set it in any deployment that outlives one process:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**`FINANCE_DASHBOARD_USERNAME`** and a password enable Basic authentication.
Without both, **the dashboard is served to anyone who can reach it.** That is
the behaviour the previous version had with no configuration file, and it is
kept, so the check is yours to make rather than the application's to refuse.
Prefer the digest over the plain password:

```bash
printf '%s' 'your-password' | sha256sum
```

Basic authentication over plain HTTP sends the credential in reverse-encoded
plaintext on every request. Terminate TLS at Apache, and do not publish this
without it.

**`FINANCE_DASHBOARD_ROOT_PATH`** must match the path Apache proxies, and is set
twice: `--root-path` on the uvicorn command line so that generated URLs carry
the prefix, and the environment variable so that the settings loader agrees. If
links come out missing the prefix, these two have drifted apart.

Apache, publishing under `/finance-dashboard/`:

```apache
ProxyPreserveHost On
ProxyPass /finance-dashboard http://127.0.0.1:3000
ProxyPassReverse /finance-dashboard http://127.0.0.1:3000
```

---

## Verify

```bash
systemctl status finance-dashboard
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
```

`200` unauthenticated, or `401` with credentials configured. Then check that the
data is actually visible: the index page should list companies, and a stock page
should show a chart rather than the placeholder.

---

## Updating

```bash
cd /var/www/finance-dashboard && ./deploy.sh
```

It pulls the working tree, creates the virtual environment if absent,
reinstalls the package, restores ownership and permissions, and restarts the
unit. Any step that fails stops the script with a non-zero status.

`APP_ROOT`, `APP_USER` and `APP_SERVICE` override the defaults
(`/var/www/finance-dashboard`, `www-data`, `finance-dashboard`).

The script requires `git`, `python3`, `sudo` and `systemctl`, and exits 127
naming whichever is missing. It expects the application directory to exist
already: it updates a deployment, it does not create one.

---

## Routine operations

**Read the log.** The application logs to stdout, which systemd captures.

```bash
journalctl -u finance-dashboard -f
journalctl -u finance-dashboard --since today | grep -i warning
```

**After a pipeline run.** Nothing to do. Files are cached against their
modification time and size, so regenerated data appears on the next request that
needs it. There is no restart and no cache to clear.

**Add or remove a stock.** Also nothing to do here — the listing is
`stocks.txt` in the data directory, which the pipeline owns.

**Rotate the secret key.** Change it and restart. Every reader's recently viewed
list is emptied, which is the whole consequence.

**Change the password.** Change the digest and restart. Browsers cache Basic
credentials aggressively; expect to have to close the window to be re-prompted.

---

## When something fails

**The service will not start.** Check `journalctl -u finance-dashboard -n 50`
first. A YAML syntax error in `config.yml` stops the process at startup on
purpose, and the traceback names the file and the line.

**`Command not found` from `deploy.sh`.** One of `git`, `python3`, `sudo` or
`systemctl` is absent; the message names it.

**Every page is empty; tables show no rows.** The data directory is wrong or
unreadable. The log carries a warning naming each missing file. Confirm the
resolved path and that the service user can read it:

```bash
journalctl -u finance-dashboard | grep "Data file is missing"
sudo -u www-data ls -l /var/www/finance-dashboard/public/data | head
```

A broken symlink and a wrong `FINANCE_DASHBOARD_DATA_DIR` look identical from
the page; they are distinguished by the paths in the log.

**One stock shows the placeholder, the rest are fine.** Expected. That stock has
no `ti_CODE.csv` yet, or it has no rows. Either it was added to `stocks.txt`
before the pipeline first ran for it, or its fetch is failing — which is a
question for the pipeline's log, not this one.

**Charts are missing but tables render.** The PNGs are served straight from the
data directory without being parsed, so this is a file that was not drawn.
Check the pipeline's chart step.

**Values look wrong, shifted by one column.** The summary files are read
positionally. A column inserted or reordered on the producing side shifts every
later value into the wrong name without raising. See
[`DATA_CONTRACT.md`](DATA_CONTRACT.md) section 3.1; this is the failure that
document exists to prevent.

**Links lose the path prefix.** `--root-path` and
`FINANCE_DASHBOARD_ROOT_PATH` disagree, or one of them disagrees with what
Apache proxies. All three must name the same prefix.

**Everything returns 401.** Credentials are configured and the browser is not
sending them, or the digest does not match. `auth.password_sha256` is compared
lowercased and stripped; regenerate it with the `printf | sha256sum` line above
rather than typing it.

**Recently viewed empties on every page load.** No secret key is configured, so
each worker signs with its own generated key. The log says so at startup.
