#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance_dashboard/main.py: Application entry point of Finance Dashboard
#
#  Description:
#  Build the FastAPI application that renders the dashboard, and provide
#  the launcher that serves it during development. This is the top of the
#  application: it is the only module that defines a route, mounts a
#  directory, installs middleware or parses a command line, and it is
#  where a Settings is resolved once and handed to everything below.
#
#  What the dashboard is, is a read only view of a directory, meant for
#  the person who owns it. The data pipeline
#  fetches prices from the J-Quants
#  API and writes CSV files and PNG charts there once a day; this
#  application parses them through data.py, decides their presentation
#  through indicators.py, links.py and formatting.py, and renders Jinja2
#  templates on the server. It computes no indicator, fetches no price,
#  stores nothing, holds no database and writes no file. Point it at a
#  directory the pipeline never filled and it renders empty tables rather
#  than failing.
#
#  It never reaches the data provider. No API key is read here, no
#  endpoint named, no HTTP client imported; a page view cannot make an
#  outbound request. What does reach here is the consequence of the
#  provider's delay: render() puts the contents of data_source.txt into
#  every page's context, and base.html shows the source and the last
#  trading day so that figures published weeks in arrears are not read as
#  live market information.
#
#  create_app() builds the application so that a test can bind one to a
#  temporary directory without touching the environment. It mounts the
#  bundled static assets, mounts the data directory itself so that the
#  charts and raw CSVs are downloadable, installs the session middleware
#  that carries the recently viewed codes in a signed cookie, and -- only
#  when credentials are configured -- installs the Basic authentication
#  middleware. That middleware wraps the whole site including /data,
#  because the generated files are the same information the pages show
#  and protecting only the HTML would leave them open.
#
#  If the configured data directory itself is absent, page loaders still
#  degrade to their ordinary missing-file state and direct /data requests
#  return 404. The mount checks again on later requests, so a directory
#  that appears after startup becomes servable without restarting the
#  application.
#
#  The URL layout is the one the previous Sinatra version served, kept so
#  that a bookmark survives the rewrite. A stock code arrives from the
#  path and is held to CODE_PATTERN by the route itself before any
#  handler runs, and data.is_valid_code checks it again before it is
#  formatted into a file name. Where a stock has no generated data the
#  request is redirected to the placeholder view with a 303 rather than
#  refused, because a code on the listing whose files have not been
#  produced yet is an ordinary state rather than a bad request.
#
#  Routes:
#      /                     index: screening, portfolio and Core30 tables
#      /stock/{code}         standard chart
#      /stock/{code}/short   short term chart
#      /stock/{code}/long    long term chart
#      /stock/{code}/detail  the full indicator series
#      /stock/{code}/none    placeholder for a stock without data
#      /clear_recent         clear the recently viewed list
#      /data/...             the generated files, served from the data directory
#      /static/...           the bundled stylesheets, scripts and favicon
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.9 or later
#  - FastAPI, Uvicorn, Jinja2, itsdangerous, PyYAML
#
#  Usage:
#      python -m finance_dashboard.main [--host HOST] [--port PORT] [--reload]
#      python -m finance_dashboard.main -h | --help
#      python -m finance_dashboard.main -v | --version
#
#  Options:
#  - --host HOST
#      Address to bind. Defaults to 127.0.0.1.
#  - --port PORT
#      Port to bind. Defaults to 3000.
#  - --reload
#      Restart the server when a source file changes.
#  - -h, --help
#      Display this help and exit.
#  - -v, --version
#      Display version information and exit.
#
#  Version History:
#  v1.2 2026-09-12
#       Return 404 for /data while the configured data directory is absent
#       and serve it when the directory appears without a restart.
#  v1.1 2026-08-14
#       Put the provenance of the generated data into the context of
#       every page.
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

import argparse
import base64
import binascii
import logging
import os
import sys
from typing import Dict, List, Optional, Sequence

from fastapi import FastAPI, Path, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from finance_dashboard import __version__, data, indicators, links
from finance_dashboard.config import Settings, load_settings
from finance_dashboard.formatting import number_with_delimiter, percent

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(PACKAGE_DIR, "templates")
STATIC_DIR = os.path.join(PACKAGE_DIR, "static")

CODE_PATTERN = r"^[0-9A-Za-z_.-]+$"

RECENT_LIMIT = 15
SERIES_LIMIT = 14
OSCILLATOR_LIMIT = 3

CHART_VIEWS = {"chart": "chart", "long": "long", "short": "short"}

logger = logging.getLogger(__name__)


class BasicAuthMiddleware:
    """Require Basic authentication for every request including static files."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._authorized(scope):
            await self.app(scope, receive, send)
            return
        response = Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Finance Dashboard"'},
        )
        await response(scope, receive, send)

    def _authorized(self, scope: Scope) -> bool:
        """Validate the Authorization header of a request."""
        for name, value in scope.get("headers", []):
            if name != b"authorization":
                continue
            scheme, _, encoded = value.decode("latin-1").partition(" ")
            if scheme.lower() != "basic":
                return False
            try:
                decoded = base64.b64decode(encoded).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                return False
            username, _, password = decoded.partition(":")
            return self.settings.verify_credentials(username, password)
        return False


class DataStaticFiles:
    """Serve the generated directory when present and return 404 while absent."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.files = StaticFiles(directory=directory, check_dir=False)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not os.path.isdir(self.directory):
            response = Response(status_code=404)
            await response(scope, receive, send)
            return
        await self.files(scope, receive, send)


def _recent_codes(request: Request) -> List[str]:
    """Return the recently viewed codes stored in the session."""
    recent = request.session.get("recent", [])
    return sorted(code for code in recent if isinstance(code, str))


def _remember(request: Request, code: str) -> None:
    """Append a code to the recently viewed list of the session."""
    recent = [entry for entry in request.session.get("recent", []) if entry != code]
    recent.append(code)
    request.session["recent"] = recent[-RECENT_LIMIT:]


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the application with its middleware, routes, and templates."""
    settings = settings or load_settings()
    app = FastAPI(
        title="Finance Dashboard",
        version=__version__,
        root_path=settings.root_path,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.mount("/data", DataStaticFiles(settings.data_dir), name="data")

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="finance_dashboard",
        max_age=settings.session_max_age,
        same_site="lax",
    )
    if settings.auth_required:
        app.add_middleware(BasicAuthMiddleware, settings=settings)

    templates = Jinja2Templates(directory=TEMPLATE_DIR)
    templates.env.globals.update(
        number_with_delimiter=number_with_delimiter,
        percent=percent,
        reference_links=links.REFERENCE_LINKS,
        version=__version__,
    )

    def render(request: Request, name: str, context: Dict[str, object]) -> Response:
        """Render a template with the values shared by every page."""
        context.setdefault("title", "Finance Dashboard")
        context["recent"] = _recent_codes(request)
        # On every page, not only the index. The figures are delayed
        # wherever they are shown, and a reader who arrives on a stock
        # page from a bookmark must see that as plainly as one who came
        # through the front door.
        context["data_source"] = data.load_data_source(settings.data_dir)
        return templates.TemplateResponse(request, name, context)

    def indicator_rows(code: str) -> List[data.Row]:
        """Load the indicator series of a stock from the data directory."""
        return data.load_indicators(settings.data_dir, code)

    def stock_context(request: Request, code: str) -> Dict[str, object]:
        """Build the context shared by the chart and detail pages."""
        return {
            "title": "{} - Finance Dashboard".format(code),
            "code": code,
            "stock_links": links.stock_links(code),
            "index_links": links.index_links(code),
            "series_columns": indicators.SERIES_COLUMNS,
        }

    @app.get("/", name="index")
    async def index(request: Request) -> Response:
        """Render the index page with the screening and summary tables."""
        portfolio_left, portfolio_right = data.split_columns(data.load_portfolio(settings.data_dir))
        core30_left, core30_right = data.split_columns(data.load_core30(settings.data_dir))
        return render(
            request,
            "index.html",
            {
                "stocks": data.load_stocks(settings.data_dir),
                "screening": data.load_screening(settings.data_dir),
                "portfolio_left": portfolio_left,
                "portfolio_right": portfolio_right,
                "core30_left": core30_left,
                "core30_right": core30_right,
            },
        )

    @app.get("/clear_recent", name="clear_recent")
    async def clear_recent(request: Request) -> Response:
        """Clear the recently viewed codes and return to the index page."""
        request.session["recent"] = []
        return RedirectResponse(request.url_for("index"), status_code=303)

    @app.get("/stock/{code}", name="stock")
    async def stock(request: Request, code: str = Path(pattern=CODE_PATTERN)) -> Response:
        """Render the standard chart page of a stock."""
        return _chart_page(request, code, "chart")

    @app.get("/stock/{code}/{view}", name="stock_view")
    async def stock_view(
        request: Request,
        code: str = Path(pattern=CODE_PATTERN),
        view: str = Path(pattern=r"^(long|short|detail|none)$"),
    ) -> Response:
        """Render the long, short, detail, or empty view of a stock."""
        if view == "none":
            return render(request, "none.html", stock_context(request, code))
        if view == "detail":
            rows = indicator_rows(code)
            if not rows:
                return _no_data(request, code)
            reversed_rows = list(reversed(rows))
            context = stock_context(request, code)
            context.update(
                {
                    "series_rows": indicators.build_rows(reversed_rows, indicators.SERIES_COLUMNS),
                    "trend_columns": indicators.TREND_COLUMNS,
                    "trend_rows": indicators.build_rows(reversed_rows, indicators.TREND_COLUMNS),
                    "oscillator_columns": indicators.OSCILLATOR_ALL_COLUMNS,
                    "oscillator_rows": indicators.build_rows(
                        reversed_rows, indicators.OSCILLATOR_ALL_COLUMNS
                    ),
                }
            )
            return render(request, "detail.html", context)
        return _chart_page(request, code, view)

    def _chart_page(request: Request, code: str, view: str) -> Response:
        """Render one of the chart pages, or fall back when data is missing."""
        rows = indicator_rows(code)
        if not rows:
            return _no_data(request, code)
        _remember(request, code)
        context = stock_context(request, code)
        context.update(
            {
                "chart_image": "{}_{}.png".format(CHART_VIEWS[view], code),
                "series_rows": indicators.build_rows(
                    rows[-SERIES_LIMIT:], indicators.SERIES_COLUMNS
                ),
                "trend_columns": indicators.TREND_LATEST_COLUMNS,
                "trend_rows": indicators.build_rows(rows[-1:], indicators.TREND_LATEST_COLUMNS),
                "oscillator_columns": indicators.OSCILLATOR_COLUMNS,
                "oscillator_rows": indicators.build_rows(
                    rows[-OSCILLATOR_LIMIT:], indicators.OSCILLATOR_COLUMNS
                ),
            }
        )
        return render(request, "stock.html", context)

    def _no_data(request: Request, code: str) -> Response:
        """Redirect to the empty view when a stock has no indicator data."""
        logger.warning("No indicator data available for code: %s", code)
        return RedirectResponse(
            request.url_for("stock_view", code=code, view="none"), status_code=303
        )

    return app


def __getattr__(name: str) -> object:
    """Build the application on first access to keep imports side effect free."""
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError("module {} has no attribute {}".format(__name__, name))


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse the command line options of the development launcher."""
    parser = argparse.ArgumentParser(
        prog="finance_dashboard", description="Run the Finance Dashboard server."
    )
    parser.add_argument("--host", default="127.0.0.1", help="address to bind")
    parser.add_argument("--port", type=int, default=3000, help="port to bind")
    parser.add_argument("--reload", action="store_true", help="reload on source changes")
    parser.add_argument(
        "-v", "--version", action="version", version="finance-dashboard {}".format(__version__)
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Start the development server and report the exit status."""
    arguments = parse_arguments(argv)
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logging.addLevelName(logging.WARNING, "WARN")
    try:
        import uvicorn
    except ImportError:
        sys.stderr.write("[ERROR] Uvicorn is not installed.\n")
        return 1
    uvicorn.run(
        "finance_dashboard.main:app",
        host=arguments.host,
        port=arguments.port,
        reload=arguments.reload,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
