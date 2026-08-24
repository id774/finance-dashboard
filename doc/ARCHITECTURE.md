# Architecture

How this application is put together, what each module is responsible for, and
what happens during one request. For what it reads and the rules it reads by,
see [`DATA_CONTRACT.md`](DATA_CONTRACT.md). For how it is installed and run, see
[`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 1. What this application is

A read only view of a directory, for the person who owns it.

The data pipeline fetches prices from the J-Quants API and writes CSV files
and PNG charts into that directory once a day. This application parses them,
decides how they are presented, and renders HTML on the server. It computes no
indicator, trains no model, fetches no price, stores nothing and writes no file.

The provider is the pipeline's business and not this one's. Nothing here holds
an API key, names an API endpoint or imports an HTTP client, so a page view
cannot reach a data provider by any path. What the provider's delay means for
what is displayed does reach here, and is handled in one place: `data.py` reads
`data_source.txt`, `main.py` puts it in the context of every page, and
`base.html` shows the source and the last trading day so that delayed figures
are never read as live ones.

That constraint is what keeps the whole thing small. There is no database, no
migration, no background job, no cache server, no queue and no build step. State
that survives a request lives only in a signed cookie in the reader's
browser and a per process cache of parsed files that is stamped
against the filesystem and can always be thrown away.

---

## 2. Composition

```text
                     main.py
        routes, middleware, mounts, launcher
        resolves a Settings once and passes it down
                        |
        +---------------+---------------+
        |               |               |
     config.py       data.py       indicators.py
     settings        file I/O       links.py
     and auth        and cache      presentation
                        |               |
                        +-------+-------+
                                |
                          formatting.py
                        string -> number -> text
                                |
                                v
                          templates/ static/
```

Dependency points one way, and a module never imports one above it.

| Module | Responsible for | Imports from the package |
|---|---|---|
| `main.py` | routes, middleware, mounts, the launcher | everything below |
| `config.py` | resolving settings, verifying credentials | nothing |
| `data.py` | reading and caching the generated files | nothing |
| `formatting.py` | converting a field to a number and to text | nothing |
| `indicators.py` | which columns a table has, and their emphasis | `data`, `formatting` |
| `links.py` | the outbound links a page offers | nothing |
| `__init__.py` | the package version | nothing |

The following properties are worth keeping:

- **`main.py` is the only module that knows about HTTP.** No other module
  imports FastAPI, reads a request or builds a response. `data.py` takes a
  directory and a code, not a `Request`.
- **`config.py` is the only module that reads the environment.** A `Settings` is
  resolved at startup and handed down, which is what lets a test build an
  application against a temporary directory without touching the environment of
  the process it runs in.

`create_app(settings)` exists for that reason. Importing the package builds no
application, reads no configuration and binds no port; the module level `app`
that uvicorn imports is constructed lazily by a module `__getattr__` on first
access.

---

## 3. One request

A stock page, `GET /stock/7203`:

1. **Basic authentication**, when credentials are configured. The middleware
   wraps the whole application, so it runs before routing and covers `/data`
   and `/static` as well as the pages. Without credentials configured it is not
   installed at all and every request proceeds.
2. **The session cookie** is decoded by `SessionMiddleware` into the recently
   viewed codes.
3. **Routing.** The code is held to `^[0-9A-Za-z_.-]+$` by the route itself, so
   a path that could escape the data directory never reaches a handler.
4. **Loading.** `data.load_indicators(data_dir, code)` stats `ti_7203.csv`,
   returns the cached rows if the modification time and size are unchanged, and
   otherwise parses it through `csv.DictReader` and caches the result.
5. **No data?** An empty list means the file is missing or has no rows. The
   handler redirects to `/stock/7203/none` with a 303 and logs a warning. This
   is an ordinary state, not an error.
6. **Presentation.** `indicators.build_rows` walks the column tuples for this
   view, converting each field with `formatting.to_float` for the emphasis rule
   and with the column's formatter for the text. The result is a list of
   `Cell(text, emphasis)`.
7. **Remembering.** The code is pushed onto the recently viewed list in the
   session.
8. **Rendering.** `stock.html` loops over cells and links. It decides nothing:
   every value it prints was decided above it.

The index page follows the same request path but has no stock-code validation,
no placeholder redirect, and no recently-viewed update. It loads the listing
and summary files used by the index instead of a single stock indicator file.

---

## 4. The views

| Route | Template | Rows shown |
|---|---|---|
| `/` | `index.html` | the listing, screening, portfolio and Core30 |
| `/stock/{code}` | `stock.html` | `chart_CODE.png`, last 14 series rows |
| `/stock/{code}/short` | `stock.html` | `short_CODE.png`, last 14 series rows |
| `/stock/{code}/long` | `stock.html` | `long_CODE.png`, last 14 series rows |
| `/stock/{code}/detail` | `detail.html` | the whole series, newest first |
| `/stock/{code}/none` | `none.html` | nothing; the placeholder |

The standard, short, and long chart views differ only in which image they name. They share a
template, a column set and a handler, because the difference between them
belongs to the pipeline that drew the images.

`SERIES_LIMIT = 14` and `OSCILLATOR_LIMIT = 3` bound the tables on a chart page.
The detail view is unbounded and shows the file reversed, newest first.

The URL layout is the one the previous Sinatra implementation served. It is kept
so that a bookmark survives the rewrite, and it is the reason `/stock/CODE/none`
is a route rather than a rendered error.

---

## 5. Rendering on the server

Pages are rendered by Jinja2 on the server and delivered complete. There is no
client side framework, no bundler, no `package.json` and no Node.js anywhere in
the build or the deployment.

The deliberate client-side exception is the RSI14 screening table on the index page,
which is built in the browser by `static/js/screening.js`, so that it can be sorted,
searched and paged without a round trip. The template emits an empty container
and the row data as a JSON `<script>` element, and the script fills the
container from it — it fetches nothing. A `<noscript>` copy of the same table is
rendered on the server for a reader without JavaScript.

Bundled third-party assets are [Pico.css](https://picocss.com/) and
[Grid.js](https://gridjs.io/), both MIT licensed and vendored under
`finance_dashboard/static/`. They are vendored rather than fetched from a CDN so
that the dashboard works on a host with no outbound access, and so that no
third party is told who is looking at it.

---

## 6. State

**The recently viewed codes** live in a cookie signed with
`FINANCE_DASHBOARD_SECRET_KEY`, held to the most recent 15, displayed sorted,
and cleared by `/clear_recent`. Nothing about a reader is stored on the server. With no secret
key configured, one is generated per process and a warning is logged, which
means the list is lost on every restart — set the key in any real deployment.

**The parsed file cache** lives in a module level dictionary in `data.py`, keyed
by path and stamped with the modification time and size of the file. It is
guarded by a lock, is per process, and is only ever an optimization: emptying it
changes nothing but the time of the next request.

There is nothing else. No session store, no database, no user account, no
uploaded file and no writable directory.

---

## 7. Failure

The two components are deployed and restarted independently, and the pipeline
rewrites the data directory while this process keeps running. The application is
built for that, not defended against it:

- A missing file is a warning and an empty table.
- A stock without indicator data redirects to the placeholder view.
- An unparseable field becomes zero rather than an exception.
- An unknown path is a 404, and a stock code with invalid characters is rejected
  by the route.

What is *not* tolerated is a broken configuration. A YAML syntax error in
`config.yml` stops the process at startup, which is where a malformed
configuration file should surface — a service that fails to start is visible in
`systemctl status`, whereas one that silently ignored its settings is not.
