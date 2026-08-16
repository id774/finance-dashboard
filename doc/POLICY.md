# Implementation Policies

finance-dashboard is a single Python web application, so this policy is stated
directly for Python rather than separating a shared section from per-language
ones.

This document stands on its own. It is the whole implementation policy of this
repository, and no rule here is completed by a document kept somewhere else. A
subject it does not cover is a gap in this document, to be filled here rather
than looked up elsewhere.

The Invariants below decide over the rest of it.

---

## 1. General Policy

### 1.1 Purpose and Scope

- **This application is a private dashboard.** It exists so that one person can
  read their own investment analysis. It is not a public web service, not a
  product, and not a way of publishing market data. Every rule below is written
  on that assumption, and a change that would only make sense for a service with
  users other than its operator is out of scope by definition.
- **The data it displays is licensed, and the code is not the data.** The
  figures originate from the J-Quants API under terms that permit personal
  analysis and prohibit redistributing the data or providing a continuing
  analysis service to a third party. This repository is published under the GPL
  or the LGPL; that covers the source code and confers nothing whatever on the
  data put through it. The two questions are answered by two different
  documents and must never be conflated in one.
- **Consequences that are binding here.** The dashboard is not deployed to the
  open internet without access control; `/data` is protected wherever the HTML
  is; no API key is accepted, stored or read by this application; and no market
  data, holding or credential is committed to this repository, including as a
  test fixture.
- **`public/data` is a path, not a permission.** The name is inherited from the
  Sinatra application that served static files from `public/`. It carries no
  implication that the data may be published, and renaming it would change
  nothing about the terms the data came under while breaking every existing
  deployment, symbolic link and `/data` route. It stays.
- This document decides how the repository is implemented: the coding rules, the
  responsibilities of the modules and the direction of dependency between them,
  the handling of settings and credentials, the treatment of the files this
  application reads, the approach to tests and documentation, and the criteria
  by which a change is judged.
- It applies to everything committed here: the Python modules, the templates,
  the stylesheet, the JavaScript this repository wrote, the tests, the
  deployment files and the documents. It does not apply to the vendored
  third-party assets, which are not edited at all.
- What this application reads and the rules it reads by belong to
  [`DATA_CONTRACT.md`](DATA_CONTRACT.md). How it is composed and what happens
  during a request belong to [`ARCHITECTURE.md`](ARCHITECTURE.md). How it is
  installed and operated belongs to [`DEPLOYMENT.md`](DEPLOYMENT.md). This
  document does not restate them; it decides how they are carried out.

### 1.2 Invariants

These lines are not crossed by a setting or by an extension.

- **Do not write into the data directory.** This application has no code path
  that opens a generated file for writing. The pipeline owns that directory.
- **Do not compute what the pipeline computes.** No indicator is calculated
  here, no model applied, no price fetched. A number shown on a page was read
  from a file. Where a value is wanted that does not exist, it is added to the
  pipeline and to the data contract, not derived in a template.
- **Do not introduce a database, a migration or a background job.** State that
  survives a request is a signed cookie and a stamped read-through cache, and
  nothing more.
- **Do not add a build step.** No `package.json`, no bundler, no transpiler, no
  Node.js in the build or the deployment. Assets are vendored as they are
  served.
- **Do not fetch a third-party asset at page load.** Stylesheets and scripts are
  served from this repository, so that the dashboard works on a host with no
  outbound access and no third party is told who is looking at it.
- **Do not make an outbound request.** This application contacts nothing. The
  external links on a page are hrefs the reader may follow; they are never
  fetched, checked or proxied here. In particular it never calls the market
  data API the pipeline fetches from, and never holds its API key: a test
  asserts that no module here names the endpoint, the credential or an HTTP
  client.
- **Do not present delayed data as current.** The source publishes in arrears.
  Every page states the source and the last trading day the data covers, taken
  from `data_source.txt`. Where that is absent the page says the age is unknown;
  no date is ever substituted for another, and no figure is carried forward,
  interpolated or invented to fill a gap.
- **Do not fail a page over a missing or malformed data file.** The pipeline and
  the dashboard are deployed and restarted independently. A missing file is a
  warning and an empty table.

### 1.3 Design Philosophy

- Prioritize clarity, portability, and explicit control over convenience.
- Favor predictable behavior and long-term maintainability.
- Render on the server. A page arrives complete, and JavaScript is an
  enhancement of one table rather than the mechanism of the site.
- Keep presentation as data. A table is a tuple of column definitions, not
  markup repeated once per column, so a threshold is changed in one place.
- Keep the templates free of decisions. Everything a template prints was decided
  by a module above it.
- The measure of this application is that it renders the pipeline's output
  faithfully and stays up while the pipeline rewrites underneath it.

### 1.4 The Modules and the Direction of Dependency

```text
main.py  ->  config.py  data.py  indicators.py  links.py  ->  formatting.py
```

- A module never imports one above it. `data.py` takes a directory and a code,
  never a `Request`.
- **`main.py` is the only module that knows about HTTP.** No other module
  imports FastAPI, reads a request or builds a response.
- **`config.py` is the only module that reads the environment.** A `Settings` is
  resolved at an entry point and passed down. A module that needs a setting
  receives it.
- **`data.py` is the only module that opens a generated file.** Nothing else
  reads the data directory.
- **`formatting.py` imports nothing from the package.** It is the bottom, and
  stays testable a value at a time.
- Importing the package must have no side effect: no configuration read, no
  directory resolved, no port bound. `create_app()` builds an application; the
  module level `app` is constructed lazily.

### 1.5 The Data Files

- The formats are a published interface, not an implementation detail. See
  [`DATA_CONTRACT.md`](DATA_CONTRACT.md), and change it in the same commit as
  the code that reads differently.
- The summary files are read positionally. The column tuples in `data.py` and
  `DATA_CONTRACT.md` define the contract. Change both together so that the
  implementation and its documentation cannot disagree.
- Parsing is tolerant by design. A conversion returns a fallback rather than
  raising, because the leading rows of an indicator file are empty by
  construction. Do not "fix" that by making conversions strict.
- Every read goes through the stamped cache. Do not add a code path that opens a
  generated file directly.

### 1.6 Configuration

- Every setting has an environment variable prefixed `FINANCE_DASHBOARD_`, and
  most have a `config.yml` key. The environment wins, so that a credential can
  reach the service without being written into the deployment directory.
- A setting has a default, or a documented consequence for being unset. A new
  setting is added to `config.py`, the README table, and `DEPLOYMENT.md` where
  it affects the deployment, in the same change.
- A missing configuration file is not an error. A malformed one stops the
  process at startup rather than being silently ignored.
- Credentials are compared with `hmac.compare_digest`, never with `==`.
- No credential, key or digest is logged, rendered into a page, or written into
  an error message.

### 1.7 Logging and Output

- No module prints. Everything logs, through `logging.getLogger(__name__)`.
- Output goes to stdout and is captured by systemd. There is no log file to
  rotate.
- A missing data file logs a warning naming the path. That warning is the first
  thing an operator greps for, and it is not lowered to debug.

### 1.8 Errors

- A route validates a stock code before it reaches a file name. Path parameters
  are constrained by pattern at the route, and `data.is_valid_code` checks again
  at the boundary.
- A stock with no data is a 303 to the placeholder view, not a 404 and not a
  500. A code on the listing whose files have not been produced is an ordinary
  state.
- An unknown path is a 404. A malformed code is rejected by the route.
- No traceback, path or setting reaches the browser.

### 1.9 Judging a Change

A change is judged by whether it:

- keeps every invariant in 1.2;
- leaves the data contract intact, or changes it deliberately, on both sides, in
  the same commit;
- keeps the URL layout, or has a reason worth a broken bookmark;
- carries its documentation in the same commit;
- passes `pytest` and `ruff check .`

---

## 2. Python Policy

### 2.1 Structure

- Python 3.9 or later. The floor is set by `requires-python` in
  `pyproject.toml`; do not use syntax the floor does not have.
- Dependencies are declared in `pyproject.toml` with lower bounds, and installed
  with `pip install .`. There is no `requirements.txt`.
- A new runtime dependency needs a reason beyond convenience. The dependency
  list is short and is meant to stay so.
- Type hints on function signatures. `ruff` is configured with `E`, `F`, `I` and
  `W` at a line length of 100, and its ordering is the import order.

### 2.2 Program Structure

- `str.format()` rather than f-strings, matching this repository's house style.
- Module level constants are upper case and grouped at the top, after the
  imports.
- A helper private to a module is prefixed with an underscore.
- Prefer a named tuple over a dictionary for a fixed shape.

### 2.3 Templates and Assets

- Templates loop and print. A template that decides something is a module's
  responsibility that leaked.
- The stylesheet is hand written and served as it is. The JavaScript this
  repository wrote is one file; it is plain ES5-compatible script with no build
  step and no dependency beyond the vendored Grid.js.
- Vendored third-party assets are not edited. They are replaced wholesale by a
  newer release, and their licenses are recorded in the README.
- Japanese appears in the interface where it is the label a reader expects — a
  column caption, a link name, a company name. Code, comments and documents are
  English.

### 2.4 Testing

- `pytest`, from the repository root. Test files are named `*_test.py`.
- A test builds its own data directory under `tmp_path`. No test reads the
  configured data directory, reads `config.yml`, or writes outside the temporary
  tree, so the suite runs on a host where the pipeline has never run.
- The fixtures in `test/conftest.py` are the data contract written down. A
  change to a format changes them in the same commit.
- The cache is cleared around a fixture, because the loaders cache per path.
- Test data is invented. No real holding, price or portfolio appears in this
  repository.
- New behaviour arrives with a test. A bug fix arrives with the test that would
  have caught it.

### 2.5 Documentation and Versioning

Every module carries a header block in this order: `Description`, the standard
`Author`, `Source Code`, `License`, `Contact` block, `Usage` and `Options`
(executables only), `Environment Variables` (`config.py` only), `Requirements`,
`Version History`. Test modules carry `Test Cases` after `Description`.

- The `Description` is what makes the file readable on its own. It states why
  the module exists, which responsibility it holds, what it consumes and what it
  produces, and which modules or external systems it touches. It is not a list
  of the functions below it, which the code already carries.
- Public functions carry a docstring. Self-evident code does not get a comment
  restating it; a comment explains why, where the why is not obvious.
- Documentation is updated in the same change as the behaviour it describes.
- The README is the entrance and `doc/` holds the detail. Do not answer the same
  question in both.
- Comments, docstrings and documents are in English.

#### 2.5.1 When to Bump a Module Version

- These rules apply to the `Version History` in each module header. Repository
  release versions and Git tags follow the separate rules below.
- Do not bump the version mechanically every time a file is touched. Decide
  based on the nature of the change:
  - Documentation-only, comment-only and formatting-only changes (help text,
    README/POLICY/VERSIONS wording, whitespace and layout, with no effect on
    behaviour) do not bump the version.
  - Any change that affects code behaviour (bug fixes, new options, and
    refactors that change observable behaviour) bumps the version.
  - Multiple updates on the same date are consolidated into a single version
    entry; do not increment the version multiple times on the same date.
  - Finalizing only the release date of an entry that already exists, such as
    changing `TBD` to the actual date, is not by itself a new change. Classify
    that entry as version-only or as containing real changes based on what it
    actually contains, not on the date edit.
- A `Version History` entry is written as `vX.Y YYYY-MM-DD`, newest first, and
  the date is the date of the change.

#### 2.5.2 Module Version Numbering

- Versions use a two-level `major.minor` scheme.
- When incrementing `minor` would reach `10`, roll over instead: increment
  `major` by 1 and reset `minor` to `0` (for example `v0.9` -> `v1.0`,
  `v1.9` -> `v2.0`, `v2.9` -> `v3.0`).
- Do not continue `minor` past `9` as in standard semantic versioning
  (do not use `v1.10`, `v1.11`, ...).
- Raising `major` for a reason other than the rollover is a decision the
  maintainer makes, not one this document derives from the change.
- Removing or renaming an option, changing what an existing argument means,
  changing a default so that an unchanged invocation does something else, and
  changing how a path or a configuration value is resolved are all incompatible
  changes. Say so in the `Version History` entry, so that the number the change
  is released under can be chosen knowing that.

#### 2.5.3 Repository Versioning

- Repository release versions are independent of individual module versions.
- Record repository release versions in [`VERSIONS`](VERSIONS) and use the same
  versions for Git tags.
- Repository release versions may use a three-level `major.minor.patch` scheme.
- Work that is not released yet takes no version of its own: it belongs to the
  entry already standing at the top of `doc/VERSIONS`.
- An unreleased entry carries `(Release Date: TBD)`, and its version number
  stays provisional until it ships. An entry opened as
  `v1.0.1 (Release Date: TBD)` may be released under a different number once
  what accumulated in it is known; which number it takes is decided then.
- Replacing `TBD` with the actual release date is the release itself, not a
  change to record in the entry.
- A repository that has not yet made its first release is in its initial
  construction stage, and that stage takes no entry here. Typically this is the
  state while `v1.0` is the first release and the repository still stands below
  it, or `v1.0` itself is unreleased. The changes made while building up to that
  release are not accumulated in `doc/VERSIONS` one by one: the file is the
  record of released versions, not of the construction that precedes the first
  of them, and its first entry is written when that release is made.
- A documentation-only change takes no `doc/VERSIONS` entry, unless its scale
  makes it worth one line saying so.
- The version declared in `pyproject.toml`, the one exposed as
  `finance_dashboard.__version__`, and the one `finance-dashboard --version`
  prints are the repository release version. They are one number and are changed
  together.
- File level `Version History` and the repository level `doc/VERSIONS` are kept
  apart. A release entry does not raise a module version, and a module version
  does not become a release entry unless the change is observable from outside.

#### 2.5.4 doc/VERSIONS Structure

- `doc/VERSIONS` must read as a version-level summary of overall changes, not a
  raw commit log. It tells a reader what a release changed. It is not the place
  to transcribe how that work happened to be committed.
- Each entry opens with a heading of the form `vX.Y.Z (YYYY-MM-DD)`, or
  `vX.Y.Z (Release Date: TBD)` while it is unreleased, underlined with `-`
  characters, followed by one `-` bullet per change.
- Use UTF-8.

##### 2.5.4.1 One Change per Line

- One coherent change is one bullet, written on one physical line. That is the
  rule, and the one case standing outside it closes this section. The entry is a
  list meant to be scanned, and a wrapped bullet costs it that: the eye no
  longer finds the changes by counting lines, and a diff no longer shows one
  added line per added change.
- This is a deliberate exception to the line length the other plain text
  documents follow, not an oversight in this file. Do not rewrap `doc/VERSIONS`
  to 80 columns, and do not report a long bullet here as a violation of that
  guidance.
- Aim for about 100 columns. A bullet that has to carry file names, command
  names, function names, option names or configuration names may run to about
  120 columns, or past that when the names it needs are that long.
- Those figures are a prompt to reread the bullet, not a limit to enforce. They
  ask whether the sentence has grown past what a reader of the version history
  needs. A bullet that is long because the change is long is correct.
- Bullets written before this rule are left wrapped as they stand. The rule
  applies to what is written from now on.
- `doc/VERSIONS` carries these guidelines again at its foot, and an entry
  written into it follows the reasons recorded there.
- The case standing outside the rule is a version history that has already
  settled on a width and a layout of its own. There a new bullet is wrapped to
  that width and balanced against the lines already standing, so that the
  version history stays of a piece, and that consistency comes before the one
  physical line asked for above. Wrapping to hold an established form does not
  overturn the rule; where a file has settled on no such form, one change is
  still one physical line.

##### 2.5.4.2 Shortening a Long Entry

- When a bullet runs long, the first move is to abstract it, never to break it
  across lines. Drop the implementation detail, the examples, the reason and the
  secondary effects, and state what the change is.
- Keep what a reader of the release cannot reconstruct without it: what was
  changed, what is now observably different from outside, what it does to
  compatibility, what it does to safety, and the identifiers someone would
  search for.
- A bullet that is long because it names what it must name stays long. Do not
  cut a file name, an option name or a configuration key to reach a column
  count.

##### 2.5.4.3 Grouping and Order

- When multiple changes to the same file within one version are really one
  coherent change, merge them into a single bullet instead of listing them
  separately. Changes that serve one purpose are described together even when
  they touch several files.
- Changes to one file that carry independent meaning are not forced together.
  Coherence decides, not the file name.
- When changes are independent, still place entries that touch the same file or
  the same feature near each other, so that each version's entry reads as a
  coherent, reviewable whole rather than an unordered sequence of unrelated
  lines.
- An independent change that belongs with nothing already listed is appended to
  the end of the current version's entry.
- Order within a version serves the reader, not the commit history. Do not
  preserve commit order at the cost of the entry reading as a whole.

### 2.6 Shell Scripts

- POSIX `sh`, not bash. `deploy.sh` is the only script here.
- It checks its required commands before doing anything, and exits 127 naming a
  missing one.
- Every step that can fail is followed by a non-zero exit. A deployment that
  half-succeeded reports failure.
- `-h` and `--help` print the header block, which is therefore the usage text
  and cannot drift from it.

### 2.7 License

This repository is dual licensed: GPL version 3 or LGPL version 3, at the
recipient's option. The texts are [`COPYING`](COPYING) and
[`COPYING.LESSER`](COPYING.LESSER), and [`LICENSE.md`](LICENSE.md) states the
choice.

- Every source module carries the line
  `License: The GPL version 3, or LGPL version 3 (Dual License).` in its header
  block, between `Source Code` and `Contact`.
- `pyproject.toml` carries the matching
  `license = { text = "GPL-3.0-or-later OR LGPL-3.0-or-later" }`.
- The README, `LICENSE.md` and the module headers state one thing. A change to
  the license is a change to all four places in the same commit.
- Vendored third-party assets keep their own licenses, which the README records.
  Do not vendor anything whose license is incompatible with distribution under
  the above.
