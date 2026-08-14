# Finance Dashboard

## Overview

**finance-dashboard** is a lightweight web dashboard for Japanese and international market data. It renders the CSV files and chart images produced by the [finance](https://github.com/id774/finance) pipeline, and holds no database of its own.

The application is written in Python with FastAPI and Jinja2. Pages are rendered on the server, and the only client side dependency is a small table component, so no Node.js toolchain or build step is required.

It only reads. `finance` computes the indicators, trains the models, draws the charts and writes a directory of files; this repository parses that directory and displays it. The two share no code and no process — they share a directory, and the format of those files is the whole of the interface between them.

```text
Yahoo Finance
     |
     v
finance  (batch, cron, 18:10 on weekdays)
     |
     v
<data directory>/*.csv  *.txt  *.png
     |
     v
finance-dashboard  (FastAPI, read only)
```

Neither repository is a dependency of the other. This one starts and serves without the pipeline installed; pointed at an empty directory it renders empty tables. See [Data Files](#1-data-files) and [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md).

## Features

- **Server side rendering with FastAPI and Jinja2**
- **No build step and no Node.js dependency**
- **Sortable and searchable screening table**
- **Chart, short term, long term, and time series views per stock**
- **Recently viewed codes kept in a signed session cookie**
- **Optional Basic authentication with a plain or hashed password**
- **File cache invalidated by modification time, so regenerated data appears without a restart**

## Supported Environments

- Python 3.9 or later
- Linux (Debian, Ubuntu) with systemd for production use
- Apache or any reverse proxy in front of Uvicorn

## Contents

1. [Data Files](#1-data-files)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Running](#4-running)
5. [Deployment](#5-deployment)
6. [Testing](#6-testing)
7. [Directory Structure](#7-directory-structure)
8. [Documents](#8-documents)
9. [Contribution](#9-contribution)
10. [License](#10-license)

---

## 1. Data Files

The dashboard only reads data. Files are generated outside this repository and placed in a single directory, which defaults to `public/data`.

| File | Format | Content |
|---|---|---|
| `stocks.txt` | `code,name` | Full stock listing shown on the index page |
| `topix_core30.csv` | Tab separated with a `Code` header | TOPIX Core30 summary |
| `portfolio.csv` | Tab separated with a `Code` header | Portfolio summary |
| `screening_rsi14.csv` | Tab separated with a `Code` header | RSI14 screening result |
| `ti_CODE.csv` | Comma separated with a named header | Technical indicators of one stock |
| `stock_CODE.csv` | Comma separated | Raw prices, linked from the stock pages |
| `ref_index.csv` | Comma separated | Reference indices, linked from the index page |
| `chart_CODE.png`, `short_CODE.png`, `long_CODE.png` | PNG | Pre generated charts |

Link the generated directory into the repository, or point the application at it with `FINANCE_DASHBOARD_DATA_DIR`.

```bash
ln -s /var/stock/data public/data
```

Two details are load bearing and easy to lose:

- The three summary files are **tab** separated and are read **positionally**. A column inserted or reordered on the producing side does not fail here; it shifts every later value into the wrong name. `ti_CODE.csv` is the only file read by header name.
- A missing file is a warning and an empty table, never an error. The pipeline and the dashboard are deployed and restarted independently, and a file that has not been generated yet is an ordinary state.

`ref_index.csv` is linked from the index page but is **not produced** by `finance`; the link is dead unless something else on the host writes it.

[`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) is the full description of what is read and the rules it is read by.

---

## 2. Installation

```bash
git clone https://github.com/id774/finance-dashboard.git
cd finance-dashboard
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Install without `[dev]` for production, which omits the test and lint tools.

---

## 3. Configuration

Settings are read from environment variables first, then from `config.yml` in the repository root. Copy the sample to start.

```bash
cp config.yml.sample config.yml
```

| Environment variable | Configuration key | Default | Description |
|---|---|---|---|
| `FINANCE_DASHBOARD_CONFIG` | - | `config.yml` | Path of the configuration file |
| `FINANCE_DASHBOARD_DATA_DIR` | `data.directory` | `public/data` | Directory holding the generated files |
| `FINANCE_DASHBOARD_USERNAME` | `auth.username` | - | Basic authentication user name |
| `FINANCE_DASHBOARD_PASSWORD` | `auth.password` | - | Basic authentication password |
| `FINANCE_DASHBOARD_PASSWORD_SHA256` | `auth.password_sha256` | - | SHA-256 digest used instead of a plain password |
| `FINANCE_DASHBOARD_SECRET_KEY` | `session.secret_key` | generated | Key signing the session cookie |
| `FINANCE_DASHBOARD_SESSION_MAX_AGE` | - | `1209600` | Lifetime of the session cookie in seconds |
| `FINANCE_DASHBOARD_ROOT_PATH` | - | empty | Path prefix when served under a sub directory |

Authentication is enabled only when a user name and a password are configured. Without them the dashboard is served to anyone who can reach it, which matches the behavior of running the previous version without `.config.yml`.

Generate a digest for `password_sha256` as follows.

```bash
printf '%s' 'your-password' | sha256sum
```

---

## 4. Running

```bash
.venv/bin/python -m finance_dashboard.main --host 0.0.0.0 --port 3000 --reload
```

The same server can be started through the `Procfile` with `foreman start`, or directly with Uvicorn.

```bash
.venv/bin/uvicorn finance_dashboard.main:app --host 0.0.0.0 --port 3000
```

| Path | View |
|---|---|
| `/` | Index with screening, portfolio, and TOPIX Core30 tables |
| `/stock/CODE` | Standard chart |
| `/stock/CODE/short` | Short term chart |
| `/stock/CODE/long` | Long term chart |
| `/stock/CODE/detail` | Full time series |
| `/stock/CODE/none` | Placeholder for a stock without data |
| `/clear_recent` | Clear the recently viewed list |
| `/data/...` | Generated data files |

---

## 5. Deployment

Install the systemd unit and let Apache proxy to Uvicorn. The unit sample assumes the application is deployed in `/var/www/finance-dashboard`.

```bash
sudo cp etc/finance-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finance-dashboard
```

Apache configuration for serving the dashboard under `/finance-dashboard/`:

```apache
ProxyPreserveHost On
ProxyPass /finance-dashboard http://127.0.0.1:3000
ProxyPassReverse /finance-dashboard http://127.0.0.1:3000
```

Update an existing deployment with `deploy.sh`, which pulls the latest revision, refreshes the virtual environment, restores ownership, and restarts the service. Any step that fails stops the script with a non-zero status.

```bash
./deploy.sh
```

Two settings decide whether a deployment is sound. `FINANCE_DASHBOARD_SECRET_KEY` must be set, or every restart empties each reader's recently viewed list. `FINANCE_DASHBOARD_ROOT_PATH` must match both the `--root-path` on the Uvicorn command line and the path Apache proxies, or generated links lose the prefix.

Authentication is off unless credentials are configured, so an unconfigured dashboard is served to anyone who can reach it.

The whole procedure, the routine operations and what to check when something fails are in [`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md).

---

## 6. Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

25 tests over the routes, the loaders and the indicator tables. Each builds its own data directory under a temporary path, so the real data files are never touched, `config.yml` is never read, and the suite runs on a host where the pipeline has never run. No test reaches the network.

The fixtures in `test/conftest.py` are the data contract written down on this side: the summary columns in the order they are read positionally, and all 38 columns of a `ti_CODE.csv`. A change to a generated format changes them in the same commit.

All test data is invented. No real holding, price or portfolio appears in this repository.

---

## 7. Directory Structure

```
.
├── finance_dashboard/
│   ├── main.py          # FastAPI application and development launcher
│   ├── config.py        # Settings from the environment and config.yml
│   ├── data.py          # CSV loaders and file cache
│   ├── formatting.py    # Value conversion and display helpers
│   ├── indicators.py    # Indicator table definitions
│   ├── links.py         # External link definitions
│   ├── templates/       # Jinja2 templates
│   └── static/          # Stylesheets, scripts, favicon
├── test/                # pytest test suite and its fixtures
├── etc/                 # systemd unit sample
├── doc/                 # architecture, contract, deployment, policy, license
├── public/data          # Symbolic link to the generated data
├── deploy.sh            # Deployment script
├── config.yml.sample    # Sample configuration
└── pyproject.toml       # Project metadata and dependencies
```

Dependency points one way, and a module never imports one above it. `main.py` is the only module that knows about HTTP, `config.py` the only one that reads the environment, and `data.py` the only one that opens a generated file. [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) has the composition and what happens during a request.

Third party assets bundled under `finance_dashboard/static` are [Pico.css](https://picocss.com/) and [Grid.js](https://gridjs.io/), both distributed under the MIT license. They are vendored rather than fetched from a CDN so that the dashboard works on a host with no outbound access.

---

## 8. Documents

| Document | Contents |
|---|---|
| [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) | Module composition, one request end to end, the views, state |
| [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) | What is read, how it is parsed, and what is tolerated |
| [`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) | Installing, configuring, operating, and diagnosing |
| [`doc/POLICY.md`](doc/POLICY.md) | Implementation rules a change is judged against |
| [`doc/VERSIONS`](doc/VERSIONS) | Release history of the repository |
| [`doc/LICENSE.md`](doc/LICENSE.md) | The license, with the full texts beside it |

This README is the entrance and `doc/` holds the detail. The producing side documents itself in the same way; [`finance`](https://github.com/id774/finance) carries the normative description of every file it writes in its own `doc/DATA_CONTRACT.md`.

---

## 9. Contribution

Contributions are welcome. You can help by:
- Reporting bugs or feature requests
- Improving the views or the deployment scripts
- Adding tests for uncovered behavior

Please follow the style used in this repository: English comments and documents, the module header each file carries, and documentation updated together with the code. [`doc/POLICY.md`](doc/POLICY.md) states the rules a change is judged by.

---

## 10. License

This repository is dual licensed under the [GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html) or the [LGPL version 3](https://www.gnu.org/licenses/lgpl-3.0.html), at your option.
For full details, please refer to [`doc/LICENSE.md`](doc/LICENSE.md). See also [`doc/COPYING`](doc/COPYING) and [`doc/COPYING.LESSER`](doc/COPYING.LESSER) for the complete license texts.

The sibling repositories [`finance`](https://github.com/id774/finance) and [`reply-writer`](https://github.com/id774/reply-writer) are under the same terms. The bundled third party assets keep their own MIT licenses, as noted above.

Thank you for using and contributing to this repository!
