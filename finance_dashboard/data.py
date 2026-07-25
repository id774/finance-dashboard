#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# data.py: CSV loaders for Finance Dashboard
#
#  Description:
#  Read the dashboard data files produced outside this application and
#  expose them as lists of dictionaries. Results are cached per file and
#  invalidated by modification time and size, so an external update is
#  picked up without restarting the application.
#
#  Two formats are handled. Summary files such as portfolio.csv are tab
#  separated with a leading "Code" header line, while per stock files
#  named ti_CODE.csv are comma separated with a named header row.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
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
