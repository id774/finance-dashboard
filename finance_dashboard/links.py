#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance_dashboard/links.py: External link definitions
#
#  Description:
#  Hold the outbound links the pages offer, as data rather than as markup
#  repeated in a template. The dashboard renders what the finance pipeline
#  computed; these links are how a reader gets from a code on a page to
#  the places that carry what the pipeline does not -- company results,
#  ratings, shareholder perks, short interest, a broker, a market index.
#
#  Three sets, differing in how they are selected:
#
#  - STOCK_LINK_TEMPLATES: URL templates with a {code} placeholder, and in
#    one case a {prefix} of the leading digit. stock_links() fills them in
#    for the stock being viewed, so every stock page carries all of them.
#  - REFERENCE_LINKS: fixed URLs that do not depend on a stock. Shown once
#    on the index page.
#  - INDEX_LINKS: pairs of a code tuple and the links belonging to it.
#    index_links() returns the links only for a code in the tuple, which
#    is how a chart of the Nikkei is offered on the pages of the ETFs that
#    track it and nowhere else.
#
#  The labels are Japanese and the targets are Japanese market sites, so
#  the labels are stored as they are displayed. Translating them would
#  leave a caption naming a site the reader then has to recognize.
#
#  Nothing here is fetched, checked or proxied. These are hrefs the
#  templates print; this application makes no outbound request of its own,
#  and a dead link is a dead link on the page rather than a failure of a
#  page view. The list is maintained by hand as sites come and go.
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

from typing import List, NamedTuple, Sequence, Tuple


class Link(NamedTuple):
    """Hold a label and the target of an external link."""

    label: str
    url: str


STOCK_LINK_TEMPLATES: Sequence[Tuple[str, str]] = (
    ("Y!", "http://stocks.finance.yahoo.co.jp/stocks/detail/?code={code}"),
    ("業績", "https://www.buffett-code.com/company/{code}"),
    ("理論", "http://kabuka.biz/riron/{prefix}000/{code}.htm"),
    ("指標", "https://jp.reuters.com/investing/stocks/detail/{code}.T"),
    ("優待", "http://gethaitou.webcrow.jp/kobetsumeigara/kenrikakuteibi_{code}.html"),
    ("Q", "https://moneyworld.jp/stock/{code}/chart"),
    ("進捗", "http://kabuyoho.ifis.co.jp/index.php?sa=report&bcode={code}"),
    ("T's", "https://www.traders.co.jp/stocks_info/individual_info_basic.asp?SC={code}"),
    ("ドラ", "http://www.kabudragon.com/s?t={code}/ichimoku=1"),
    ("株探", "http://kabutan.jp/stock/?code={code}"),
    ("目標", "http://www.kabuka.jp.net/rating/{code}.html"),
    ("空売", "http://karauri.net/{code}/"),
    ("PTS", "http://www.morningstar.co.jp/StockInfo/info/compare/{code}"),
    ("ADR", "http://moneybox.jp/investment/adr.php?t={code}"),
    ("株速", "http://kabu-sokuhou.com/brand/item/code___{code}"),
    ("みん", "http://minkabu.jp/stock/{code}/signal"),
)

REFERENCE_LINKS: Sequence[Link] = (
    Link("表計算", "https://docs.google.com/spreadsheets/u/0/"),
    Link("UFJ", "http://direct.bk.mufg.jp/"),
    Link("楽天", "https://www.rakuten-sec.co.jp/"),
    Link("岡三", "https://www.okasan-online.co.jp/login/jp/"),
    Link("GMO", "https://sec-sso.click-sec.com/loginweb/"),
    Link("年金", "https://life.smtb.jp/Lifeguide"),
    Link("トレダビ", "https://www.k-zone.co.jp/td"),
    Link("Bloomberg", "https://www.bloomberg.co.jp/markets/stocks"),
    Link("日経", "http://www.nikkei.com/video/"),
    Link("ダイワ", "http://www.daiwatv.jp/contents/strategy/day/"),
    Link("モーサテ", "http://www.tv-tokyo.co.jp/mv/nms/market/"),
    Link("AI", "https://nikkeiyosoku.com/"),
    Link("VI", "http://indexes.nikkei.co.jp/nkave/index/profile?cid=3&idx=nk225vi"),
    Link("為替", "https://www.77bank.co.jp/kawase/cash.html"),
    Link("先物", "http://nikkei225jp.com/cme/"),
    Link("世界", "http://sekai-kabuka.com/"),
)

INDEX_LINKS: Sequence[Tuple[Sequence[str], Sequence[Link]]] = (
    (
        ("N225", "1321", "1357", "1570", "1579", "1580", "1360", "1366"),
        (
            Link("[日経平均]", "http://www.conceptsengine.com/finance/technical-chart/1011.html"),
            Link(
                "[ドル建て日経平均]",
                "http://www.conceptsengine.com/finance/technical-chart/1010.html",
            ),
        ),
    ),
    (
        ("1348", "1356"),
        (Link("[TOPIX]", "http://www.conceptsengine.com/finance/technical-chart/1013.html"),),
    ),
    (
        ("1546",),
        (Link("[ダウ]", "http://www.conceptsengine.com/finance/technical-chart/1100.html"),),
    ),
    (
        ("1557",),
        (Link("[S&P500]", "http://www.conceptsengine.com/finance/technical-chart/1101.html"),),
    ),
    (
        ("1545",),
        (Link("[NASDAQ]", "http://www.conceptsengine.com/finance/technical-chart/1102.html"),),
    ),
    (
        ("2042", "1563"),
        (Link("[マザーズ指数]", "https://kabutan.jp/stock/chart?code=0012"),),
    ),
    (
        ("2049", "1552"),
        (Link("[恐怖指数]", "https://nikkei225jp.com/data/vix.php"),),
    ),
    (
        ("1671", "1699", "2038", "1605"),
        (Link("[原油]", "https://nikkei225jp.com/oil/"),),
    ),
)


def stock_links(code: str) -> List[Link]:
    """Build the external links of a single stock."""
    return [
        Link(label, template.format(code=code, prefix=code[0] if code else ""))
        for label, template in STOCK_LINK_TEMPLATES
    ]


def index_links(code: str) -> List[Link]:
    """Build the index chart links shown only for the matching codes."""
    links: List[Link] = []
    for codes, entries in INDEX_LINKS:
        if code in codes:
            links.extend(entries)
    return links
