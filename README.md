# Finance Dashboard

## Overview

**finance-dashboard** is a lightweight web dashboard for finance data. It renders the CSV files and chart images produced by an external data pipeline, without holding any database of its own.

The application is written in Python with FastAPI and Jinja2. Pages are rendered on the server, and the only client side dependency is a small table component, so no Node.js toolchain or build step is required.

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
8. [Contribution](#8-contribution)
9. [License](#9-license)

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

Update an existing deployment with `deploy.sh`, which pulls the latest revision, refreshes the virtual environment, and restarts the service.

```bash
./deploy.sh
```

---

## 6. Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

Tests build their own data directory, so the real data files are never touched.

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
├── test/                # pytest test suite
├── etc/                 # systemd unit sample
├── doc/                 # License texts
├── public/data          # Symbolic link to the generated data
├── deploy.sh            # Deployment script
└── pyproject.toml       # Project metadata and dependencies
```

Third party assets bundled under `finance_dashboard/static` are [Pico.css](https://picocss.com/) and [Grid.js](https://gridjs.io/), both distributed under the MIT license.

---

## 8. Contribution

Contributions are welcome. You can help by:
- Reporting bugs or feature requests
- Improving the views or the deployment scripts
- Adding tests for uncovered behavior

Please follow the style and format used in this repository, and keep comments and documentation in English.

---

## 9. License

This repository is dual licensed under the [GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html) or the [LGPL version 3](https://www.gnu.org/licenses/lgpl-3.0.html), at your option.
For full details, please refer to the [LICENSE](doc/LICENSE) file.  See also [COPYING](doc/COPYING) and [COPYING.LESSER](doc/COPYING.LESSER) for the complete license texts.

Thank you for using and contributing to this repository!
