#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# indicators_test.py: Unit tests for finance_dashboard.indicators
#
#  Description:
#  Validate the emphasis rules and the formatters of the indicator table
#  definitions, including the signal column that is compared with MACD.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      pytest test/indicators_test.py
#
#  Requirements:
#  - Python Version: 3.9 or later
#
#  Test Cases:
#    - Emphasize overbought and oversold values of a band rule
#    - Emphasize positive and negative values of a threshold rule
#    - Emphasize only values above a single sided threshold
#    - Compare the MACD signal with the MACD column of the same row
#    - Format integer columns with thousands separators
#    - Format decimal columns with two digits
#    - Treat empty and non numeric fields as zero
#
#  Version History:
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

from finance_dashboard import indicators
from finance_dashboard.formatting import number_with_delimiter, round2, to_float


def emphasis(columns, row, key):
    """Return the emphasis class of one column of a row."""
    cells = indicators.build_cells(row, columns)
    keys = [column.key for column in columns]
    return cells[keys.index(key)].emphasis


def test_band_rule():
    columns = indicators.OSCILLATOR_COLUMNS
    assert emphasis(columns, {"rsi14": "75"}, "rsi14") == "up"
    assert emphasis(columns, {"rsi14": "25"}, "rsi14") == "down"
    assert emphasis(columns, {"rsi14": "50"}, "rsi14") == ""
    assert emphasis(columns, {"slowk": "50"}, "slowk") == "mid"


def test_threshold_rule():
    columns = indicators.OSCILLATOR_COLUMNS
    assert emphasis(columns, {"roc10": "0.5"}, "roc10") == "up"
    assert emphasis(columns, {"roc10": "-0.5"}, "roc10") == "down"


def test_above_only_rule():
    columns = indicators.OSCILLATOR_COLUMNS
    assert emphasis(columns, {"vl": "6"}, "vl") == "up"
    assert emphasis(columns, {"vl": "1"}, "vl") == ""


def test_signal_is_compared_with_macd():
    columns = indicators.OSCILLATOR_COLUMNS
    assert emphasis(columns, {"macd": "2", "macdsignal": "1"}, "macdsignal") == "up"
    assert emphasis(columns, {"macd": "1", "macdsignal": "2"}, "macdsignal") == "down"


def test_formatters():
    assert number_with_delimiter("1234567.8") == "1,234,567"
    assert round2("1.005") == "1.00"
    assert to_float("") == 0.0
    assert to_float("nan") == 0.0
    assert number_with_delimiter("n/a") == "0"


def test_series_columns_are_rendered():
    row = {
        "date": "2026-07-25",
        "open": "1000",
        "high": "1100",
        "low": "900",
        "adj_close": "1050",
        "volume": "12345",
    }
    cells = indicators.build_cells(row, indicators.SERIES_COLUMNS)
    assert [cell.text for cell in cells] == [
        "2026-07-25",
        "1,000",
        "1,100",
        "900",
        "1,050",
        "12,345",
    ]
