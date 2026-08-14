#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance_dashboard/data.py: File loaders of Finance Dashboard
#
#  Description:
#  Read the files the finance pipeline writes into the data directory and
#  expose them as lists of dictionaries the templates can render. This
#  module is the whole of this application's read side: nothing else opens
#  a generated file, and nothing anywhere writes one.
#
#  It is therefore where the contract with finance
#  (https://github.com/id774/finance) is implemented, and doc/DATA_CONTRACT.md
#  describes what that contract is. Three shapes are handled:
#
#  - stocks.txt, comma separated, code and name per line. The listing.
#  - The summary files -- topix_core30.csv, screening_rsi14.csv and
#    portfolio.csv -- tab separated, with a leading "Code" header line
#    that is skipped. These are read POSITIONALLY: the fields are zipped
#    against SUMMARY_COLUMNS or PORTFOLIO_COLUMNS below, so a column
#    inserted or reordered on the producing side does not fail here, it
#    silently shifts every later value into the wrong name. Those two
#    tuples are the contract, and finance pins them from its own side in
#    test/test_contract.py.
#  - ti_CODE.csv, comma separated with a named header row, read by name
#    through csv.DictReader after each header cell is lowercased and
#    reduced to [0-9a-z_] by _normalize(). Only this shape survives a
#    reordering.
#
#  Every read goes through a cache keyed by path and stamped with the
#  modification time and size of the file. The pipeline rewrites the
#  directory once a day while this process keeps running, so a stamp that
#  differs is what makes the new data appear without a restart, and a
#  stamp that matches is what stops a page view from re-parsing a file
#  that has not changed. The cache is process local and guarded by a lock,
#  and clear_cache() empties it for tests and manual reloads.
#
#  A missing file is a warning and an empty list, never an exception. The
#  pipeline and the dashboard are deployed and run independently, so a
#  file that has not been generated yet, or a stock without history, is an
#  ordinary state and renders as an empty table rather than a 500.
#
#  A stock code reaches this module from the URL. is_valid_code() holds it
#  to [0-9A-Za-z_.-] before it is ever formatted into a file name, so that
#  no request can walk out of the data directory.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.9 or later
#  - Standard library only
#
#  Version History:
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

import csv
import logging
import os
import re
import threading
from typing import Callable, Dict, List, Optional, Sequence, Tuple

Row = Dict[str, str]

CODE_PATTERN = re.compile(r"^[0-9A-Za-z_.-]+$")

STOCKS_FILE = "stocks.txt"
CORE30_FILE = "topix_core30.csv"
PORTFOLIO_FILE = "portfolio.csv"
SCREENING_FILE = "screening_rsi14.csv"

SUMMARY_COLUMNS: Sequence[str] = (
    "code",
    "open",
    "high",
    "low",
    "close",
    "diff",
    "ratio",
    "rsi",
    "name",
)

PORTFOLIO_COLUMNS: Sequence[str] = (
    "code",
    "open",
    "high",
    "low",
    "close",
    "diff",
    "ratio",
    "trend",
    "predict",
    "name",
)

logger = logging.getLogger(__name__)

_cache: Dict[str, Tuple[Tuple[float, int], List[Row]]] = {}
_lock = threading.Lock()


def is_valid_code(code: str) -> bool:
    """Report whether a stock code is safe to embed in a file name."""
    return bool(CODE_PATTERN.match(code))


def _stamp(path: str) -> Optional[Tuple[float, int]]:
    """Return the modification time and size of a file, or None when absent."""
    try:
        status = os.stat(path)
    except OSError:
        return None
    return (status.st_mtime, status.st_size)


def _load_cached(path: str, loader: Callable[[str], List[Row]]) -> List[Row]:
    """Load a file through the cache, reloading it when the file changed."""
    stamp = _stamp(path)
    if stamp is None:
        logger.warning("Data file is missing: %s", path)
        return []
    with _lock:
        cached = _cache.get(path)
        if cached is not None and cached[0] == stamp:
            return cached[1]
    rows = loader(path)
    with _lock:
        _cache[path] = (stamp, rows)
    return rows


def clear_cache() -> None:
    """Drop every cached file, mainly for tests and manual reloads."""
    with _lock:
        _cache.clear()


def _normalize(name: str) -> str:
    """Normalize a CSV header cell into a dictionary key."""
    return re.sub(r"[^0-9a-z]+", "_", (name or "").strip().lower()).strip("_")


def _read_stocks(path: str) -> List[Row]:
    """Read the comma separated code and name listing."""
    rows: List[Row] = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            fields = line.strip().split(",")
            if len(fields) < 2 or not fields[0]:
                continue
            rows.append({"code": fields[0], "name": fields[1]})
    return rows


def _read_summary(path: str, columns: Sequence[str]) -> List[Row]:
    """Read a tab separated summary file, skipping its header line."""
    rows: List[Row] = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if not fields or not fields[0] or fields[0] == "Code":
                continue
            row = dict(zip(columns, fields))
            for column in columns:
                row.setdefault(column, "")
            rows.append(row)
    return rows


def _read_indicators(path: str) -> List[Row]:
    """Read a per stock technical indicator file keyed by its header row."""
    rows: List[Row] = []
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        for record in csv.DictReader(handle):
            row = {_normalize(key): (value or "") for key, value in record.items() if key}
            if not row.get("date") or row.get("date") == "Date":
                continue
            rows.append(row)
    return rows


def load_stocks(data_dir: str) -> List[Row]:
    """Load the full stock listing shown on the index page."""
    return _load_cached(os.path.join(data_dir, STOCKS_FILE), _read_stocks)


def load_core30(data_dir: str) -> List[Row]:
    """Load the TOPIX Core30 summary."""
    path = os.path.join(data_dir, CORE30_FILE)
    return _load_cached(path, lambda target: _read_summary(target, SUMMARY_COLUMNS))


def load_screening(data_dir: str) -> List[Row]:
    """Load the RSI14 screening summary."""
    path = os.path.join(data_dir, SCREENING_FILE)
    return _load_cached(path, lambda target: _read_summary(target, SUMMARY_COLUMNS))


def load_portfolio(data_dir: str) -> List[Row]:
    """Load the portfolio summary."""
    path = os.path.join(data_dir, PORTFOLIO_FILE)
    return _load_cached(path, lambda target: _read_summary(target, PORTFOLIO_COLUMNS))


def load_indicators(data_dir: str, code: str) -> List[Row]:
    """Load the technical indicator series of a single stock."""
    if not is_valid_code(code):
        return []
    path = os.path.join(data_dir, "ti_{}.csv".format(code))
    return _load_cached(path, _read_indicators)


def split_columns(rows: Sequence[Row]) -> Tuple[List[Row], List[Row]]:
    """Split rows into two balanced groups for the two column index layout."""
    half = (len(rows) + 1) // 2
    return list(rows[:half]), list(rows[half:])
