#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# links.py: External link definitions
#
#  Description:
#  Keep the external reference links of the dashboard as data so that the
#  templates stay free of repeated markup. Stock links embed the stock
#  code, index links are shown only for the codes listed with them.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
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
