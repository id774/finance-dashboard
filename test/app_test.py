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
#
#  Version History:
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
    for path in ("/stock/N225", "/stock/N225/long", "/stock/N225/short", "/stock/N225/detail"):
        response = client.get(path)
        assert response.status_code == 200
        assert "N225 - Finance Dashboard" in response.text


def test_chart_image_matches_the_view(client):
    assert "long_N225.png" in client.get("/stock/N225/long").text
    assert "short_N225.png" in client.get("/stock/N225/short").text
    assert "chart_N225.png" in client.get("/stock/N225").text


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
    assert client.get("/stock/N225 X").status_code == 422
    assert client.get("/stock/N225/unknown").status_code == 422


def recent_navigation(client):
    """Extract the recently viewed list of the navigation bar."""
    body = client.get("/").text
    start = body.index('<ul class="recent">')
    return body[start : body.index("</ul>", start)]


def test_recent_codes(client):
    client.get("/stock/N225")
    assert "/stock/N225" in recent_navigation(client)
    client.get("/clear_recent")
    assert "/stock/N225" not in recent_navigation(client)


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
    assert "N225" in response.text
