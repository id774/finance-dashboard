#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# app_test.py: Route tests for Finance Dashboard
#
#  Description:
#  Validate the routes kept from the previous implementation, the
#  fallback for stocks without data, the recently viewed list stored in
#  the session, and Basic authentication.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      pytest test/app_test.py
#
#  Requirements:
#  - Python Version: 3.9 or later
#
#  Test Cases:
#    - Serve the index page as UTF-8 HTML
#    - Serve the chart, long, short, and detail pages of a stock
#    - Redirect to the empty view when a stock has no data
#    - Reject an unknown path with 404
#    - Reject a stock code with invalid characters
#    - Record and clear the recently viewed codes
#    - Require Basic authentication when credentials are configured
#    - Serve data files only to authenticated clients
#    - Show the data source and the last trading day on every page
#    - Say so plainly when the provenance has not been recorded
#    - Make no outbound request and hold no market data credential
#
#  Version History:
#  v1.1 2026-08-14
#       Cover the delayed data notice and the absence of any data
#       fetching.
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

from fastapi.testclient import TestClient

from finance_dashboard.config import Settings
from finance_dashboard.main import create_app


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "トヨタ自動車" in response.text


def test_chart_pages(client):
    for path in ("/stock/6758", "/stock/6758/long", "/stock/6758/short", "/stock/6758/detail"):
        response = client.get(path)
        assert response.status_code == 200
        assert "6758 - Finance Dashboard" in response.text


def test_chart_image_matches_the_view(client):
    assert "long_6758.png" in client.get("/stock/6758/long").text
    assert "short_6758.png" in client.get("/stock/6758/short").text
    assert "chart_6758.png" in client.get("/stock/6758").text


def test_stock_without_data_redirects(client):
    response = client.get("/stock/7203", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/stock/7203/none")


def test_none_page_is_served(client):
    response = client.get("/stock/7203/none")
    assert response.status_code == 200
    assert "No Data." in response.text


def test_unknown_path_returns_404(client):
    assert client.get("/404").status_code == 404


def test_invalid_code_is_rejected(client):
    assert client.get("/stock/6758 X").status_code == 422
    assert client.get("/stock/6758/unknown").status_code == 422


def recent_navigation(client):
    """Extract the recently viewed list of the navigation bar."""
    body = client.get("/").text
    start = body.index('<ul class="recent">')
    return body[start : body.index("</ul>", start)]


def test_recent_codes(client):
    client.get("/stock/6758")
    assert "/stock/6758" in recent_navigation(client)
    client.get("/clear_recent")
    assert "/stock/6758" not in recent_navigation(client)


def test_basic_authentication(settings):
    settings.username = "user"
    settings.password = "pass"
    client = TestClient(create_app(settings))
    assert client.get("/").status_code == 401
    assert client.get("/", auth=("user", "wrong")).status_code == 401
    assert client.get("/", auth=("user", "pass")).status_code == 200


def test_hashed_password(data_dir):
    digest = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    settings = Settings(
        data_dir=data_dir, username="user", password_sha256=digest, secret_key="test-secret"
    )
    client = TestClient(create_app(settings))
    assert client.get("/", auth=("user", "password")).status_code == 200
    assert client.get("/", auth=("user", "pass")).status_code == 401


def test_data_files_require_authentication(settings):
    settings.username = "user"
    settings.password = "pass"
    client = TestClient(create_app(settings))
    assert client.get("/data/stocks.txt").status_code == 401
    response = client.get("/data/stocks.txt", auth=("user", "pass"))
    assert response.status_code == 200
    assert "6758" in response.text


# --------------------------------------------------------------------
# Provenance of the data
# --------------------------------------------------------------------


def test_every_page_states_the_source_and_the_last_trading_day(client):
    for path in ("/", "/stock/6758", "/stock/6758/detail", "/stock/6758/none"):
        text = client.get(path).text
        assert "J-Quants API (Free plan, delayed)" in text
        assert "2026-04-24" in text
        assert "リアルタイムではありません" in text


def test_an_unrecorded_provenance_is_said_to_be_unknown(tmp_path):
    from finance_dashboard import data

    empty = tmp_path / "empty"
    empty.mkdir()
    data.clear_cache()
    client = TestClient(create_app(Settings(data_dir=str(empty), secret_key="test-secret")))

    text = client.get("/").text
    assert "不明" in text
    assert "リアルタイムではありません" in text


def test_the_dashboard_makes_no_outbound_request():
    """
    Fetching market data is the pipeline's responsibility, not this one's.

    The dashboard reads a directory. It holds no API key, names no API
    endpoint, and imports no HTTP client, so there is no path by which
    a page view could reach a data provider.
    """
    import os

    package = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "finance_dashboard")
    forbidden = ("JQUANTS_API_KEY", "api.jquants.com", "import requests", "import httpx",
                 "urllib.request", "yfinance")
    for root, _, files in os.walk(package):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            for term in forbidden:
                assert term not in source, "{} names {}".format(path, term)
