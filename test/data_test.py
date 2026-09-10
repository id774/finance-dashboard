#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# data_test.py: Unit tests for finance_dashboard.data
#
#  Description:
#  Validate the CSV loaders, the modification based cache, the code
#  validation used to build file names, and the column split helper of
#  the index page.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      pytest test/data_test.py
#
#  Requirements:
#  - Python Version: 3.9 or later
#
#  Test Cases:
#    - Load the stock listing as code and name pairs
#    - Skip the header line of tab separated summary files
#    - Load portfolio rows including the trend and predict columns
#    - Normalize indicator headers and skip rows without a date
#    - Return an empty list when a data file is missing
#    - Reject stock codes containing path separators
#    - Reload a file after its contents change
#    - Split rows into two balanced groups
#    - Read the provenance of the generated data
#    - Report an absent provenance file as nothing known, not as today
#    - Ignore a key data_source.txt was not meant to carry
#
#  Version History:
#  v1.2 2026-08-24
#       Expect the provenance source to name the provider and plan
#       without a publication delay claim.
#  v1.1 2026-08-14
#       Cover the provenance loader.
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

import os

from finance_dashboard import data


def test_load_stocks(data_dir):
    rows = data.load_stocks(data_dir)
    assert [row["code"] for row in rows] == ["6758", "1321", "7203"]
    assert rows[2]["name"] == "トヨタ自動車"


def test_load_core30_skips_header(data_dir):
    rows = data.load_core30(data_dir)
    assert [row["code"] for row in rows] == ["7203", "6758"]
    assert rows[0]["rsi"] == "65.43"
    assert rows[0]["name"] == "トヨタ自動車"


def test_load_portfolio_columns(data_dir):
    rows = data.load_portfolio(data_dir)
    assert rows[0]["trend"] == "up"
    assert rows[1]["ratio"] == "-0.33"


def test_load_indicators(data_dir):
    rows = data.load_indicators(data_dir, "6758")
    assert len(rows) == 20
    assert rows[0]["date"] == "2026-07-01"
    assert rows[0]["adj_close"] == "1050.5"
    assert rows[0]["macdsignal"] == "1.2"


def test_missing_file_returns_empty(data_dir):
    assert data.load_indicators(data_dir, "0000") == []


def test_invalid_code_is_rejected(data_dir):
    assert data.is_valid_code("../etc/passwd") is False
    assert data.load_indicators(data_dir, "../stocks") == []


def test_cache_is_invalidated_on_change(data_dir):
    path = os.path.join(data_dir, "stocks.txt")
    assert len(data.load_stocks(data_dir)) == 3
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("6758,ソニーグループ\n")
    os.utime(path, (0, 0))
    assert len(data.load_stocks(data_dir)) == 4


def test_split_columns():
    left, right = data.split_columns([{"code": str(index)} for index in range(5)])
    assert [row["code"] for row in left] == ["0", "1", "2"]
    assert [row["code"] for row in right] == ["3", "4"]


def test_load_data_source(data_dir):
    values = data.load_data_source(data_dir)
    assert values["source"] == "J-Quants API (Free plan)"
    assert values["generated"] == "2026-07-21"
    assert values["last_trading_day"] == "2026-04-24"


def test_the_last_trading_day_is_older_than_the_generation_date(data_dir):
    """The delay is visible in the file, which is the point of it."""
    values = data.load_data_source(data_dir)
    assert values["last_trading_day"] < values["generated"]


def test_a_missing_provenance_file_is_nothing_known(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    data.clear_cache()
    assert data.load_data_source(str(empty)) == {}


def test_an_unexpected_key_is_ignored(data_dir):
    path = os.path.join(data_dir, "data_source.txt")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("api_key\tsomething-that-must-never-be-here\n")
    os.utime(path, (0, 0))
    values = data.load_data_source(data_dir)
    assert set(values) <= set(data.DATA_SOURCE_KEYS)
