# Requirements: a private dashboard for one person's market analysis

## 1. Purpose of this document

This document states what the application is for, who reads it, what it accepts,
what it presents and where its responsibility ends. It is the requirements
definition of this repository.

**It does not describe how any of it is built.** The basic design — the module
composition, what each module is responsible for, what happens during one
request, the views, the state and the failure behaviour — is written in
[`ARCHITECTURE.md`](ARCHITECTURE.md). The exact format of the files this
application reads is [`DATA_CONTRACT.md`](DATA_CONTRACT.md), which is normative.
How a change is carried out and judged belongs to [`POLICY.md`](POLICY.md), and
how the application is installed and operated belongs to
[`DEPLOYMENT.md`](DEPLOYMENT.md).

This separation is deliberate. This document may be read on its own to learn
what the application is required to do; nothing in it is completed by a document
in another repository.

## 2. Name

`finance-dashboard`. The name is the role, not the technique: it is the
dashboard on top of a directory of generated files. The word "dashboard" is the
whole of the claim — it displays, and it does nothing else.

## 3. Purpose

One person follows a set of Japanese shares. A batch pipeline runs on their host
every weekday evening and leaves a directory of CSV files and PNG charts behind
it. They want to open a page and read that directory: a table ranking the set by
how it moved, their portfolio beside it, and per stock a chart with the current
values of the usual oscillators under it.

Presenting that is this repository's job. Producing it is not.

**It is software for one person's private reading of their own analysis.** That
is a design premise rather than a description of current usage, and the
following statements are binding on every change:

- The market data it displays is not redistributed to anyone.
- No continuing analysis service built on that data is provided to anyone.
- It is not published on the open internet without authentication in front of
  it.
- The terms and licence of the external market data are followed, and are a
  separate question from the licence of this source code.

Section 4 says what follows from that, section 7.2 says where the data came from
and under what conditions, and [`POLICY.md`](POLICY.md) section 1.1 states the
rules a change is judged against.

## 4. What it is not

- **Not a producer.** It computes no indicator, trains no model, fetches no
  price and draws no chart. Every number and every image on every page was
  written by the pipeline before the request arrived.
- **Not a market data service.** It displays data obtained for one person's
  personal analysis. Serving that data to a third party — as a page, as a
  download, as an API — is redistribution, and is out of scope in every form.
- **Not a public web service.** It has no sign-up, no account, no role and no
  tenant. It is one reader's view of one directory.
- **Not a database application.** It owns no schema, runs no migration and
  writes no file. Its data is a directory somebody else fills.
- **Not a trading system.** It places no order and connects to no broker.
- **Not advice.** The classifier and the regression it displays are a decoration
  the pipeline computed, and displaying them at that size is the whole of the
  requirement.
- **Not a single-page application.** See section 16.

## 5. Who uses it

One reader, who is also the operator of the pipeline that fills the data
directory and the maintainer of this repository. There are no accounts, no roles
and no multi-user concerns. Basic authentication, where it is enabled, exists to
keep strangers out rather than to tell users apart.

## 6. Where it runs

A single Linux host — Debian or Ubuntu with systemd in production — on Python
3.9 or later. It is served by Uvicorn, ordinarily behind Apache or another
reverse proxy, and ordinarily under a path prefix rather than at a domain root.
It also runs from a checkout on a laptop, bound to localhost, with nothing in
front of it.

The reader may be at a desk or on a phone; both are ordinary, and section 15.4
states what that requires.

It must run on a host with **no outbound network access at all**, and it must
start and serve on a host where the pipeline has never run.

## 7. Input

The entire input is one directory on the local filesystem, and nothing else
reaches this application from outside the request.

### 7.1 The generated files

Per stock: an indicator file, a price file, and three chart images at different
window lengths. Per list: a summary table. Once a day: a record of where the
data came from and how old it is. A full listing of the stocks names the set.

The directory defaults to `public/data` and is ordinarily a symbolic link to
wherever the pipeline writes. The name is historical — it is what the previous
Sinatra implementation served static files from — and it is **a path, not a
permission**. Renaming it would change nothing about the terms the data came
under, and would break every existing installation, so it is kept.

The names, separators, columns, column order and value meanings of these files
are specified by [`DATA_CONTRACT.md`](DATA_CONTRACT.md).

### 7.2 Provenance and delay

Everything displayed comes from files produced by the pipeline. The current
producer records J-Quants provenance in `data_source.txt`, but this application
does not own or restate the provider's current subscription terms.

The requirements here concern the properties of the produced data:

- **The figures may be delayed.** The dashboard must not assume that the newest
  figure in the files is current.
- **The available history may be bounded.** The dashboard displays the history
  present in the generated files and does not invent rows that are absent.

Because a delayed figure that looks current is worse than no figure, **every
page must name the source and the last trading day the data covers**, beside the
day the pipeline generated it. Those values are read from `data_source.txt`.
When that file is absent or a value is missing, the page must say the age is
unknown rather than assume it is today.

The length of the delay is deliberately **not** stated anywhere in this
repository. It is a published property of a subscription plan and can change;
the pipeline configures it in one place. The last trading day itself is the fact
the reader needs, and it cannot go stale.

### 7.3 What is not an input

- **No API key.** None is accepted, none is configured, and none is of any use
  here. It belongs to the pipeline and stays on that side.
- **No network.** A page view makes no outbound request of any kind. No module
  may name an API endpoint, a credential or an HTTP client, and a test asserts
  it.
- **No upload.** Nothing a reader submits becomes data. There is no form that
  writes.

## 8. What it presents

The views use the URL layout the previous Sinatra implementation served:

| View | Contents |
|---|---|
| Index | the full listing, the RSI14 screening, the portfolio, and TOPIX Core30 |
| Stock | the standard chart with the recent series and oscillator rows |
| Short | the same, with the short-window chart |
| Long | the same, with the long-window chart |
| Detail | the whole series for one stock, newest first |
| None | the placeholder for a stock with no data |

Alongside them the generated directory itself is served, so that a chart image
and a raw file can be reached from a page.

The URL layout is kept so that a bookmark survives the rewrite from Sinatra.
That is why the placeholder is a route rather than a rendered error, and the
requirement is that existing bookmarks keep working.

Each stock page also offers a fixed set of outbound links to external sites for
that code, and the index offers a fixed set of reference links. **These are
hrefs and nothing more.** The application never follows one, never fetches one
and never reports that a reader followed one.

## 9. The data contract

**This is the central requirement, and the one that constrains everything else.**

The files are written by a separate repository, `finance`, which holds no copy
of this code. The two are joined by a directory of files and by nothing else:
they share no process, no database and no module, they are deployed and
restarted independently, and neither imports the other.

- The generated formats are a published interface. They are not changed to suit
  an implementation here.
- The summary files are read **positionally**. A column inserted or reordered on
  the producing side does not fail here — it shifts every later value into the
  wrong name and corrupts the display silently. That property is why the
  contract has tests on this side rather than only a document.
- The reading side is considered before the writing side when the contract
  changes.

The fixtures in `test/conftest.py` are this contract written down on this side,
and a change to a generated format changes them in the same commit.

## 10. Tolerance

The pipeline rewrites the data directory while this process keeps running, and
the two are restarted independently. **The application is built for that, not
defended against it.**

- **A missing file is a warning and an empty table, never an error.** A file
  that has not been generated yet is an ordinary state.
- **A stock with no data gets the placeholder view**, not an error page.
- **An unparseable field becomes zero** rather than an exception.
- **Pointed at an empty directory, the application starts and renders empty
  tables.** It must not require the pipeline to be installed.
- **Regenerated data appears without a restart.** A cache may exist, but it must
  be invalidated by the state of the file on disk.

What is *not* tolerated is a broken configuration: a malformed configuration
file must stop the process at startup, where `systemctl status` will show it,
rather than being silently ignored.

## 11. Nothing is invented

No page ever shows a stale figure as though it were current, and no gap is
filled with a substitute.

- A stock with no data renders the placeholder view, not zeroes or a fabricated
  table.
- An unrecorded last trading day renders as unknown, not as today.
- A value the files do not carry is not derived, estimated or defaulted into
  existence.

The application displays what the directory says and admits what it does not
know.

## 12. State

The application stores nothing about a reader on the server, and there is no
requirement that it ever should.

- **Recently viewed codes** are held in a cookie signed with a configured secret
  key, bounded to a small number of the most recent, and clearable by the
  reader. They are a convenience; losing them costs nothing.
- **A parsed-file cache** may exist per process as an optimization only.
  Emptying it must change nothing but the time of the next request.

There is no session store, no database, no user account, no uploaded file and no
writable directory.

## 13. Configuration

Operational values — which directory is read, whether authentication is
enforced and against what, the key that signs the cookie, its lifetime, and the
path prefix the application is published under — are settings, not constants in
code.

- They are read from the environment first and from an optional YAML file
  second, so that a credential can be given to the systemd unit without being
  written into a file in the deployment directory.
- They are resolved **once**, in one place, and passed down. No module below the
  entry point reaches for the environment on its own.
- Every setting has a default or a documented consequence for being unset.
- Values that are not operational stay in code. Not every constant needs to
  become a setting.

A deployment must account for the session-signing key and the path prefix.
When the service is reachable beyond the loopback interface, it must also have
the access control required by section 15.1. These conditions are named
directly rather than maintained as a fixed count because access control depends
on how the service is exposed.

## 14. Credentials

There is no market-data API key here. The application may hold an
authentication credential and a session-signing key.

- A password may be configured as a plain value or as a SHA-256 digest, and the
  digest form is the one the documents recommend.
- Comparison is constant-time, so that a wrong password costs the same as a
  right one.
- No credential and no secret key is committed to this repository in any form,
  including as a sample value.
- No credential appears in a log line, an exception message or a rendered page.

## 15. Non-functional requirements

### 15.1 Access control

**Authentication is enabled only when credentials are configured, and without
them the dashboard is served to anyone who can reach it.** That is the behaviour
the previous Sinatra version had without a configuration file, and it is safe
only because of where it is run. The requirement is therefore on the deployment
as much as on the code: bound to localhost, behind Basic authentication, behind
a proxy that holds its own credentials, or behind a VPN or an address
restriction — any one of them, and none of them optional once the port is
reachable from outside.

When Basic authentication is enabled it must wrap **the whole site, including
the generated data directory and the static assets**. The generated files are
the same information the pages show, and protecting only the HTML would leave
the CSVs and the charts open. Serving those to somebody else is redistributing
market data obtained for personal use.

A stock code taken from a URL must be constrained by the route to a character
set that cannot escape the data directory, so that a traversal attempt never
reaches a handler.

### 15.2 Availability

The application is one process serving one reader. It has no availability target
beyond starting cleanly under systemd and being restarted by it. It must survive
the data directory changing underneath it (section 10), and it must not require
the pipeline, the provider or any network to be reachable in order to serve a
page.

### 15.3 Maintainability

- Dependency points one way, and a module never imports one above it.
- One module knows about HTTP; one module reads the environment; one module
  opens a generated file. A module's responsibility is stated in its header.
- Documents are updated in the same commit as the code they describe.
- The test suite runs offline, on a host where the pipeline has never run,
  against a temporary directory it builds itself. It must never touch the real
  data directory or read the real configuration file.
- **All test data is invented.** No real holding, price or portfolio appears in
  this repository, and nothing obtained from the J-Quants API may be added as a
  fixture.

### 15.4 Usability

- The delayed-data notice is on every page, not on a page the reader must find.
- The screening table is sortable, searchable and paged without a round trip,
  and a reader with JavaScript disabled still gets the same table rendered on
  the server.
- Pages are usable on a phone as well as at a desk.
- A reader can reach a stock's other views, its raw files and its external links
  from the stock page.

### 15.5 Performance

Rendering a page must not be slower than reading the files it displays. Repeated
requests for an unchanged file should not reparse it. Beyond that there is no
throughput or latency requirement: the load is one person pressing links.

## 16. Rendering

Pages are rendered on the server and delivered complete.

**There must be no Node.js toolchain and no build step**, in development or in
deployment. A checkout plus a Python environment is the whole of the setup.

One exception is allowed and is deliberate: the screening table is built in the
browser from row data the server embedded in the page, so that it can be sorted
and searched without a round trip. It fetches nothing.

Third-party assets are **vendored, never fetched from a CDN**, for two reasons
that are both requirements: the dashboard must work on a host with no outbound
access, and no third party is to be told who is looking at it.

## 17. Basic design

**The basic design of this application is written in
[`ARCHITECTURE.md`](ARCHITECTURE.md).** This document deliberately stops at
what is required; that one states how the requirements are met.

It covers the module composition and the direction of dependency, what each
module is responsible for, one request from authentication through loading and
presentation to rendering, the views and the limits that bound their tables, the
places where state lives, and how failure is handled.

The detailed specification of the interface in section 9 is
[`DATA_CONTRACT.md`](DATA_CONTRACT.md). Together, those documents fully describe
the design of this repository, and no further design document is required.

## 18. The documents

| Document | Contents |
|---|---|
| [`../README.md`](../README.md) | the entrance: what it is, how to install, configure and run it |
| `REQUIREMENTS.md` | this document: what is required and why |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | the basic design: composition, one request, views, state |
| [`DATA_CONTRACT.md`](DATA_CONTRACT.md) | what is read, how it is parsed, and what is tolerated |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | installing, configuring, operating and diagnosing |
| [`POLICY.md`](POLICY.md) | the rules a change is judged against |
| [`VERSIONS`](VERSIONS) | the release history of this repository |
| [`LICENSE.md`](LICENSE.md) | the licence, with the full texts beside it |

README is the entrance and `doc/` holds the detail. The documents are written in
English, as the code and its comments are.

## 19. Independence

The repository is complete on its own.

- Its documents specify its behaviour without reference to another repository.
- Its tests run without another repository present.
- What it reads is defined here, not by reading the producer's source.

The producer's source was read to establish the contract. That reading is
recorded in [`DATA_CONTRACT.md`](DATA_CONTRACT.md) so that nobody has to repeat
it.

## 20. Licence

The source code in this repository is published under the GPL or the LGPL. That
covers the source code and nothing else.

**The market data the dashboard displays is not covered by that licence and does
not become free to use because of it.** It remains governed by the provider's
terms, which permit personal analysis and prohibit redistribution. These are two
separate questions — what may be done with this code, and what may be done with
the data put through it — and the documents must keep them apart.

The vendored third-party assets keep their own MIT licences.

## 21. Simplicity

The application is one person's view of one directory. It should stay the size
of that.

Not wanted: a database, a user model, a background job, a queue, a cache server,
a client-side framework, a build step, a plugin system, or an API for anybody
else to call. Each would be more machinery than the job justifies, and the job
does not justify any of them.

The constraint that it only reads is what keeps it small. A requirement that
would make it write is not a feature request; it is a proposal to make it a
different application, and belongs in the pipeline instead.

## 22. Out of scope

- Fetching market data, or holding the credential that would allow it.
- Computing an indicator, training a model or drawing a chart.
- Serving data or analysis to anybody but the operator.
- Accounts, roles, registration, or any second reader.
- Writing, editing or deleting anything in the data directory.
- Order placement, broker connectivity, or anything a trade could follow from.
- A reference index. The Free plan carries no index values, the pipeline
  produces none, and the link that once pointed at one has been removed rather
  than replaced from another source.

## 23. Acceptance conditions

The application meets its requirements when all of the following hold:

1. It starts and serves against an empty directory, on a host with no outbound
   access and no pipeline installed, and renders empty tables rather than
   failing.
2. Every page names the data source and the last trading day, and says unknown
   where the record does not say.
3. No module names an API endpoint, an API key or an HTTP client, and a test
   asserts it.
4. All six views render for a stock with data, and a stock without data reaches
   the placeholder rather than an error.
5. A file regenerated by the pipeline is reflected without restarting the
   process.
6. A missing file produces a warning and an empty table, and the rest of the
   page renders.
7. With credentials configured, an unauthenticated request is refused for the
   pages, the static assets and the generated data directory alike.
8. A stock code containing a path separator is rejected by the route.
9. The whole test suite passes offline, without reading the real configuration
   file or the real data directory.
10. Installing and running requires no Node.js and no build step.
11. No credential, no real holding and no fetched market data is present
    anywhere in the repository.
