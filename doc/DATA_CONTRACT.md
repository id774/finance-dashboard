# Data Contract

This document describes the files this application reads, and the rules it
reads them by. It is the consumer's half of an interface whose normative
description lives in the producing repository, at
[`finance/doc/DATA_CONTRACT.md`](https://github.com/id774/finance/blob/master/doc/DATA_CONTRACT.md).

Where the two disagree about what a file contains, that document is right and
this one is the bug. What this document is authoritative about is the other
direction: how these files are parsed here, and therefore what a change on the
producing side would break.

---

## 1. The boundary

```text
finance  (batch, cron, 18:10 on weekdays)
     |
     v
<data directory>/*.csv  *.txt  *.png
     |
     v
finance-dashboard  (FastAPI, read only)
```

The two repositories share no code, no process and no database. They share a
directory of files.

- `finance` writes the directory and never reads anything this application
  produces, because this application produces nothing.
- `finance-dashboard` reads the directory and never writes into it. There is no
  code path here that opens a file for writing.
- Neither imports the other. Neither is a dependency of the other, at runtime or
  in its tests.

This application is therefore complete without the pipeline installed. Pointed
at an empty directory it starts, serves and renders empty tables.

The directory is named by `FINANCE_DASHBOARD_DATA_DIR` or the `data.directory`
key, and defaults to `public/data`. The usual deployment is a symlink:

```bash
ln -s /var/stock/data public/data
```

---

## 2. What is read, and what is only served

Everything is read by [`finance_dashboard/data.py`](../finance_dashboard/data.py),
which is the only module here that opens a generated file.

| File | Parsed? | Used for |
|---|---|---|
| `stocks.txt` | yes, line split | the company listing on the index page |
| `screening_rsi14.csv` | yes, positional | the sortable screening table |
| `portfolio.csv` | yes, positional | the portfolio table |
| `topix_core30.csv` | yes, positional | the TOPIX Core30 table |
| `ti_CODE.csv` | yes, by header name | every table on a stock page |
| `stock_CODE.csv` | no | offered as a download |
| `ref_index.csv` | no | linked from the index page |
| `chart_CODE.png`, `short_CODE.png`, `long_CODE.png` | no | the chart images |

The unparsed files are served straight from the mounted data directory. Nothing
here inspects their contents, so their format is not this application's
business. Note that `ref_index.csv` is linked but is **not produced** by
`finance`; the link is dead unless something else on the host writes it.

---

## 3. The two parsing styles, and why the difference matters

### 3.1 Positional — the summary files

`screening_rsi14.csv`, `portfolio.csv` and `topix_core30.csv` are tab separated
with a leading header line. They are read by **position**, not by header name:
the header line is skipped by its literal first field `Code`, each remaining
line is split on tab, and the fields are zipped against a fixed tuple in
`data.py`.

```python
PORTFOLIO_COLUMNS = (code, open, high, low, close, diff, ratio, trend, predict, name)
SUMMARY_COLUMNS   = (code, open, high, low, close, diff, ratio, rsi, name)
```

`portfolio.csv` uses the ten column tuple. `topix_core30.csv` and
`screening_rsi14.csv` use the nine column one, where a single indicator column
replaces `Trend` and `Pred`. Its header names the indicator — `rsi9` in one file
and `rsi14` in the other — and this application ignores that name in favour of
the position, which is why one tuple serves both.

**This is the fragile part of the interface.** A column inserted or reordered on
the producing side does not raise here. It shifts every later value one name to
the left, and the page renders a company name where a ratio belongs, silently
and plausibly. Renaming a header is safe, because headers are ignored. Adding a
column at the end is absorbed. Anything else is a breaking change.

`finance` pins both tuples from its own side in its `test/test_contract.py`,
duplicating them into the test rather than importing them. The duplication is
the contract: two independent statements that must agree.

### 3.2 By header name — the indicator files

`ti_CODE.csv` is comma separated with a named header row, read through
`csv.DictReader`. Each header cell is lowercased and reduced to `[0-9a-z_]` by
`data._normalize`, so `Adj_Close` becomes `adj_close` and `RSI14` becomes
`rsi14`. Rows whose `date` is empty, or is the literal `Date`, are dropped.

Columns are therefore safe to reorder and unsafe to rename. A column this
application does not know about is carried through and ignored; a column it
looks for and does not find renders as an empty value rather than failing, so a
table stays displayable against an older file.

The keys the pages use are the ones named in
[`finance_dashboard/indicators.py`](../finance_dashboard/indicators.py).

### 3.3 Line split — the listing

`stocks.txt` is comma separated, one `code,name` per line. The first two fields
are taken and the rest of the line is ignored. A line with fewer than two
fields, or an empty first field, is skipped.

---

## 4. What this application tolerates

The pipeline and the dashboard are deployed and restarted independently, and the
pipeline rewrites the directory once a day while this process keeps running.
Every one of the following is an ordinary state, not an error:

- **A missing file.** Logged as a warning, read as an empty list, rendered as an
  empty table. The dashboard does not 500 because a stock list has not been
  generated yet.
- **A stock with no `ti_CODE.csv`.** The stock pages redirect to the placeholder
  view with a 303. A code can appear in `stocks.txt` before its files exist.
- **An empty, non-numeric or `NaN` field.** Converted to `0.0` by
  `formatting.to_float`, which never raises. The leading rows of `ti_CODE.csv`
  are empty by construction, because an indicator with a 25-day window has no
  value for the first 24 days.
- **A partially written file.** A short read renders a short table. The pipeline
  writes during its nightly run and this application may read mid-write; the
  next page view picks up the completed file.

The cost of the third is worth stating plainly: **a missing value and a genuine
zero are indistinguishable** once past `to_float`. Both render as `0.00`, and an
emphasis rule with a lower band marks a leading empty cell the same way it marks
a real zero.

---

## 5. How a change is noticed

Files are cached per path, stamped with modification time and size. A file the
pipeline regenerates is re-read on the next request that needs it; a file that
has not changed is not re-parsed. No restart is required after a nightly run,
and there is no polling.

The cache is per process. Running more than one worker means each holds its own
copy, which is harmless because the cache is read only and stamp checked.

`data.clear_cache()` empties it, for tests and manual reloads.

---

## 6. Changing this contract

A change to any of the three parsed formats is a change to a published
interface, and it is not this repository's to make alone.

1. The producing side changes `finance/doc/DATA_CONTRACT.md` and its
   `test/test_contract.py` in the same commit.
2. This side changes the column tuples in `data.py`, this document, and the
   fixtures in `test/conftest.py` in the same commit.
3. Both are deployed together where the change is not backward compatible. A
   column appended to the end of a summary file is the only change that is.

The fixtures in `test/conftest.py` are the contract written down on this side.
A test passing against them is evidence about the real files only because the
fixtures match them.
