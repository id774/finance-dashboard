# Finance Dashboard

## Overview

**finance-dashboard** is a **private dashboard**: one person's view of their own investment analysis, on their own machine or behind their own access control. It renders CSV files and chart images produced by an external data pipeline, and holds no database of its own.

It is not a public web service, and it is not a way of publishing market data. See [Purpose and Scope](#1-purpose-and-scope) before deploying it anywhere a stranger can reach.

The application is written in Python with FastAPI and Jinja2. Pages are rendered on the server, and the only client side dependency is a small table component, so no Node.js toolchain or build step is required.

It only reads. The data pipeline fetches the prices, computes the indicators, trains the models, draws the charts and writes a directory of files; this application parses that directory and displays it. The two components share no code and no process — they share a directory, and the format of those files is the whole of the interface between them.

```text
J-Quants API (Free plan, delayed)
     |
     v
data pipeline  (batch, cron, 18:10 on weekdays)
     |
     v
<data directory>/*.csv  *.txt  *.png
     |
     v
finance-dashboard  (FastAPI, read only)
```

The arrow points one way. This repository never calls the J-Quants API, is never given its API key, and makes no outbound request of its own during a page view. Fetching market data is the pipeline's responsibility and stays there; a test asserts that no module here names the endpoint, the credential or an HTTP client.

The application starts and serves without the pipeline installed; pointed at an empty directory it renders empty tables. See [Data Files](#3-data-files) and [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md).

## Features

- **A private view of your own analysis, not a service for anyone else**
- **A delayed-data notice on every page, with the last trading day shown**
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

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Data Source and Delay](#2-data-source-and-delay)
3. [Data Files](#3-data-files)
4. [Installation](#4-installation)
5. [Configuration](#5-configuration)
6. [Access Control](#6-access-control)
7. [Running](#7-running)
8. [Deployment](#8-deployment)
9. [Testing](#9-testing)
10. [Directory Structure](#10-directory-structure)
11. [Documents](#11-documents)
12. [Contribution](#12-contribution)
13. [License](#13-license)

---

## 1. Purpose and Scope

This is software for looking at your own investment analysis. It is written for one reader — the person who runs the pipeline that fills its data directory — and everything about it assumes that reader.

These are design premises, not preferences, and the code and the tests are arranged around them:

- **Private use.** The dashboard exists so that its operator can read their own analysis. It is not a product, a service, or a publication.
- **No redistribution of market data.** The figures on these pages come from a market data provider under terms that permit personal analysis and forbid redistribution. Serving them to a third party — as a page, as a download, as an API — is redistribution.
- **No continuous analysis service for others.** Providing an ongoing feed of analysis derived from that data to anyone else is equally out of scope, whether it is paid for or not.
- **Not a public web service.** It is not intended to be published on the open internet without authentication. Run it on localhost, or behind a reverse proxy with Basic authentication, a VPN, or an IP restriction. See [Access Control](#6-access-control).
- **`public/data` is a path, not a permission.** The directory is named that because the previous Sinatra application served its static files from `public/`. It does not mean the data in it may be made public, and renaming it changes nothing about the terms the data came under. It is kept because the deployment, the symbolic link and the `/data` route are all built on it, and a rename would break existing installations for no gain.
- **Open source code, licensed data.** This repository is published under the GPL or the LGPL. That covers the source code in it and nothing else. It says nothing whatever about the market data the dashboard displays, which is governed by the provider's terms. See [License](#13-license).
- **No credentials, no market data in the repository.** No API key, no fetched price, no real portfolio is committed here. Every fixture in `test/` is invented.

---

## 2. Data Source and Delay

Everything shown here originates from the **J-Quants API**, the market data service JPX Market Innovation & Research operates for individual investors, on its **Free plan**. The pipeline fetches it; this repository only reads what the pipeline wrote.

**The figures are not live.** The Free plan publishes in arrears — at the time of writing, twelve weeks behind the present — and keeps a bounded history behind that point. A price on these pages is therefore weeks old, and the most recent weeks of the market are not represented at all.

Because a delayed figure that looks current is worse than no figure, every page carries a notice naming the source and the **last trading day** the data covers, beside the day the pipeline generated it. Those come from `data_source.txt`, which the data pipeline writes; when it is absent the notice says the age is unknown rather than assuming it is today.

The exact length of the delay is deliberately **not** repeated through this repository. It is a published property of a subscription plan that can change, and the pipeline configures it in one place. What is shown here is the last trading day itself, which is the fact a reader needs and cannot go stale.

---

## 3. Data Files

The dashboard only reads data. Files are generated outside this repository and placed in a single directory, which defaults to `public/data`.

| File | Format | Content |
|---|---|---|
| `stocks.txt` | `code,name` | Full stock listing shown on the index page |
| `data_source.txt` | Tab separated key and value | Where the data came from and its last trading day |
| `topix_core30.csv` | Tab separated with a `Code` header | TOPIX Core30 summary |
| `portfolio.csv` | Tab separated with a `Code` header | Portfolio summary |
| `screening_rsi14.csv` | Tab separated with a `Code` header | RSI14 screening result |
| `ti_CODE.csv` | Comma separated with a named header | Technical indicators of one stock |
| `stock_CODE.csv` | Comma separated | Prices, linked from the stock pages |
| `chart_CODE.png`, `short_CODE.png`, `long_CODE.png` | PNG | Pre generated charts |

Link the generated directory into the repository, or point the application at it with `FINANCE_DASHBOARD_DATA_DIR`.

```bash
ln -s /var/stock/data public/data
```

Three details are load bearing and easy to lose:

- The three summary files are **tab** separated and are read **positionally**. A column inserted or reordered on the producing side does not fail here; it shifts every later value into the wrong name. `ti_CODE.csv` is the only file read by header name.
- A missing file is a warning and an empty table, never an error. The pipeline and the dashboard are deployed and restarted independently, and a file that has not been generated yet is an ordinary state.
- Nothing is invented to fill a gap. A stock with no data renders as an empty table, and an unrecorded last trading day renders as unknown. No page ever shows a stale figure as though it were current, or today's date for data that does not reach it.

`ref_index.csv` was linked from the index page by earlier versions and was never produced by the data pipeline. The link is gone; the reference indices behind it came from a data source this project no longer uses, and the J-Quants Free plan does not carry index values. See [section 9 of the data contract](doc/DATA_CONTRACT.md).

[`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) is the full description of what is read and the rules it is read by.

---

## 4. Installation

```bash
git clone https://github.com/id774/finance-dashboard.git
cd finance-dashboard
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Install without `[dev]` for production, which omits the test and lint tools.

---

## 5. Configuration

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

No J-Quants API key appears in this table, and none is accepted. This application does not fetch market data and has no use for the credential that does; it belongs to the pipeline and stays on the host that runs it.

Generate a digest for `password_sha256` as follows.

```bash
printf '%s' 'your-password' | sha256sum
```

---

## 6. Access Control

Authentication is enabled only when a user name and either a password or its SHA-256 digest are configured. **Without them the dashboard is served to anyone who can reach it.** That is the behaviour the previous Sinatra version had without a configuration file, and it is safe only because of where you run it.

Pick whichever of these suits the host. Any one of them is enough; none of them is optional if the port is reachable from outside:

| Approach | When it fits |
|---|---|
| Bind to `127.0.0.1` | A single machine. The default host is already localhost |
| Basic authentication | Reachable on a LAN, or proxied. Configure `auth.username` and `auth.password_sha256` |
| Reverse proxy with its own authentication | Apache or nginx already terminates TLS and holds credentials |
| VPN or IP restriction | The dashboard is reached from a fixed set of addresses |

When Basic authentication is enabled it wraps **the whole site, including `/data`**. The generated files are the same information the pages show, and protecting only the HTML would leave the CSVs and charts open. Serving those files to someone else is redistributing market data obtained for personal use; see [Purpose and Scope](#1-purpose-and-scope).

Set `FINANCE_DASHBOARD_SECRET_KEY` in any deployment that outlives one process, or every restart empties each reader's recently viewed list.

---

## 7. Running

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

## 8. Deployment

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

Authentication is off unless credentials are configured, so an unconfigured dashboard is served to anyone who can reach it. Decide how it is protected before it listens on anything but localhost; [Access Control](#6-access-control) has the options.

The dashboard needs read access to the generated directory and nothing else. It is not installed on the pipeline host's behalf and is not given the J-Quants API key.

The whole procedure, the routine operations and what to check when something fails are in [`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md).

---

## 9. Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

32 tests over the routes, the loaders and the indicator tables. Each builds its own data directory under a temporary path, so the real data files are never touched, `config.yml` is never read, and the suite runs on a host where the pipeline has never run. No test reaches the network, and one of them asserts that no module in the application could: none names an API endpoint, an API key, or an HTTP client.

The fixtures in `test/conftest.py` are the data contract written down on this side: the summary columns in the order they are read positionally, all 38 columns of a `ti_CODE.csv`, and the three keys of `data_source.txt`. A change to a generated format changes them in the same commit.

**All test data is invented.** No real holding, price or portfolio appears in this repository, and nothing obtained from the J-Quants API may be added as a fixture. The stock codes and names are well known issuers used as labels; every figure beside them was made up.

---

## 10. Directory Structure

```
.
├── finance_dashboard/
│   ├── main.py          # FastAPI application and development launcher
│   ├── config.py        # Settings from the environment and config.yml
│   ├── data.py          # CSV loaders, provenance, and file cache
│   ├── formatting.py    # Value conversion and display helpers
│   ├── indicators.py    # Indicator table definitions
│   ├── links.py         # External link definitions (hrefs only, never fetched)
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

## 11. Documents

| Document | Contents |
|---|---|
| [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) | Module composition, one request end to end, the views, state |
| [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) | What is read, how it is parsed, and what is tolerated |
| [`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) | Installing, configuring, operating, and diagnosing |
| [`doc/POLICY.md`](doc/POLICY.md) | Implementation rules a change is judged against |
| [`doc/VERSIONS`](doc/VERSIONS) | Release history of the repository |
| [`doc/LICENSE.md`](doc/LICENSE.md) | The license, with the full texts beside it |

This README is the entrance and `doc/` holds the detail. This repository's
[`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) is the normative description of
the files the application reads.

---

## 12. Contribution

Contributions are welcome. You can help by:
- Reporting bugs or feature requests
- Improving the views or the deployment scripts
- Adding tests for uncovered behavior

Please follow the style used in this repository: English comments and documents, the module header each file carries, and documentation updated together with the code. [`doc/POLICY.md`](doc/POLICY.md) states the rules a change is judged by.

---

## 13. License

**The source code** in this repository is dual licensed under the [GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html) or the [LGPL version 3](https://www.gnu.org/licenses/lgpl-3.0.html), at your option.
For full details, please refer to [`doc/LICENSE.md`](doc/LICENSE.md). See also [`doc/COPYING`](doc/COPYING) and [`doc/COPYING.LESSER`](doc/COPYING.LESSER) for the complete license texts.

**The market data this dashboard displays is not covered by that license and never becomes free to use because of it.** The prices, the indicators derived from them and the charts drawn from them originate from the J-Quants API and remain governed by that provider's terms of service, which permit personal analysis and prohibit redistributing the data or providing a continuing analysis service to third parties. Two separate questions: what you may do with this code, and what you may do with the data you put through it. The first is answered here; the second is answered by the provider.

The bundled third party assets keep their own MIT licenses, as noted above.

Thank you for using and contributing to this repository!
