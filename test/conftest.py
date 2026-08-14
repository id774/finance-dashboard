#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test/conftest.py: Shared fixtures of the Finance Dashboard test suite
#
#  Description:
#  Build the world every test in this suite runs against: a temporary data
#  directory holding sample files in the formats the finance pipeline
#  produces, and an application bound to that directory.
#
#  The sample files are the contract written down. The tab separated
#  summaries carry their leading "Code" header and the exact column order
#  data.py zips positionally, and the indicator header names all 38
#  columns of a ti_CODE.csv in the order the pipeline writes them. A test
#  that passes against these fixtures is evidence about the real files
#  only because the fixtures match them, so a change to the contract on
#  the producing side is a change to this file.
#
#  All of it is invented. No real holding, price or portfolio appears
#  here, and the stock names are well known issuers used as sample data.
#
#  Every fixture is built under pytest's tmp_path. The suite never reads
#  the configured data directory, never reads config.yml, and writes
#  nothing outside the temporary tree, so it runs on a host where the
#  pipeline has never run. data.clear_cache() is called around the
#  fixtures because the loaders cache per path, and a cached list from one
#  test's directory must not answer another test.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      This module is loaded by pytest. Run the suite from the repository
#      root:
#          pytest
#
#  Requirements:
#  - Python Version: 3.9 or later
#  - pytest, httpx (for the FastAPI test client)
#
#  Version History:
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance_dashboard import data  # noqa: E402
from finance_dashboard.config import Settings  # noqa: E402
from finance_dashboard.main import create_app  # noqa: E402

STOCKS = "N225,日経平均\n1321,日経225連動型\n7203,トヨタ自動車\n"

CORE30 = "\t".join(("Code", "Open", "High", "Low", "Close", "Diff", "Ratio", "RSI", "Name")) + "\n"
CORE30 += "7203\t2000\t2100\t1990\t2050\t50\t2.50\t65.43\tトヨタ自動車\n"
CORE30 += "6758\t1000\t1100\t990\t1050\t-20\t-1.90\t35.12\tソニーグループ\n"

PORTFOLIO = "Code\tOpen\tHigh\tLow\tClose\tDiff\tRatio\tTrend\tPredict\tName\n"
PORTFOLIO += "7203\t2000\t2100\t1990\t2050\t50\t2.50\tup\t2100\tトヨタ自動車\n"
PORTFOLIO += "9432\t3000\t3100\t2990\t3050\t-10\t-0.33\tdown\t3000\t日本電信電話\n"

SCREENING = CORE30

INDICATOR_HEADER = (
    "Date,Open,High,Low,Close,Adj_Close,Volume,EWMA5,EWMA25,EWMA50,EWMA75,EWMA200,"
    "UpperBand,LowerBand,SAR,Ret_Index,RSI9,RSI14,MFI14,ROC10,ROC25,ROC50,ROC75,ROC150,"
    "CCI14,ULTOSC,SLOWK,SLOWD,FASTK,FASTD,MACD,MACDSignal,MACDHist,WILLR14,VL,TR,ATR,NATR\n"
)

INDICATOR_ROW = (
    "{date},1000,1100,900,1050,1050.5,12345,1010,1020,1030,1040,1050,1100,900,995,1.05,"
    "72.5,68.1,85.2,1.5,-2.5,3.5,-4.5,5.5,120.5,71.2,85.1,15.2,90.3,10.4,1.5,1.2,0.3,"
    "-5.5,6.5,150,12.34,1.23\n"
)


@pytest.fixture()
def data_dir(tmp_path):
    """Create a temporary data directory with sample files."""
    directory = tmp_path / "data"
    directory.mkdir()
    (directory / "stocks.txt").write_text(STOCKS, encoding="utf-8")
    (directory / "topix_core30.csv").write_text(CORE30, encoding="utf-8")
    (directory / "portfolio.csv").write_text(PORTFOLIO, encoding="utf-8")
    (directory / "screening_rsi14.csv").write_text(SCREENING, encoding="utf-8")
    series = INDICATOR_HEADER
    for day in range(1, 21):
        series += INDICATOR_ROW.format(date="2026-07-{:02d}".format(day))
    (directory / "ti_N225.csv").write_text(series, encoding="utf-8")
    (directory / "ti_7203.csv").write_text(INDICATOR_HEADER, encoding="utf-8")
    data.clear_cache()
    yield str(directory)
    data.clear_cache()


@pytest.fixture()
def settings(data_dir):
    """Build settings pointing at the temporary data directory."""
    return Settings(data_dir=data_dir, secret_key="test-secret")


@pytest.fixture()
def client(settings):
    """Build a test client for an application without authentication."""
    from fastapi.testclient import TestClient

    return TestClient(create_app(settings))
