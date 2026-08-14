#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance_dashboard/indicators.py: Indicator table definitions
#
#  Description:
#  Decide which indicator columns each table on a stock page carries, what
#  each is labelled, how its value is printed, and when it is emphasized.
#  All of that is held as data -- a tuple of Column definitions per table
#  -- rather than as markup repeated once per column in a template.
#
#  The dashboard shows around forty indicator columns across several
#  tables. Written as markup, a change of threshold would mean finding one
#  number among forty near-identical blocks of HTML, and the templates
#  would carry the display logic. Here a table is a tuple, a column is a
#  NamedTuple of key, label, reference link, formatter and rule, and
#  build_rows() turns a list of data rows into a list of rendered Cells
#  that a template loops over without deciding anything.
#
#  A rule receives the whole row and the current value already converted
#  to a float by formatting.to_float, so it never has to parse or guard
#  against an empty field. It returns an emphasis class the stylesheet
#  interprets: "up" for the overbought or positive range, "down" for the
#  opposite, "mid" for the neutral band of a stochastic style indicator,
#  and "" for no emphasis. band(), threshold(), above_only() and
#  below_reference() build the four shapes of rule the tables need; the
#  thresholds are the ones the previous Sinatra implementation used.
#
#  The column keys are the normalized header cells of ti_CODE.csv, which
#  data.py produces by lowercasing each header and reducing it to
#  [0-9a-z_]. A key naming a column the file does not carry renders empty
#  rather than failing, so a table stays displayable against an older file.
#
#  This module computes no indicator. The values are calculated by the
#  finance pipeline and read from disk; what is decided here is only how
#  they are presented. The links point at third-party explanations of each
#  indicator and are the only outbound URLs on a stock page.
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

from typing import Callable, List, NamedTuple, Optional, Sequence

from finance_dashboard.data import Row
from finance_dashboard.formatting import number_with_delimiter, round2, to_float

MA_LINK = "http://www.kabuciao.com/tech/ido.html"
BOLLINGER_LINK = "http://www.kabuciao.com/tech/trend/bollin.html"
SAR_LINK = "https://www.rakuten-sec.co.jp/web/fop/futures/chart_guide/09.html"
RSI_LINK = "http://www.kabuciao.com/tech/oscillator/rsi.html"
MFI_LINK = "http://www.kabuciao.com/tech/oscillator/mfi.html"
ROC_LINK = "http://www.kabuciao.com/tech/oscillator/roc.html"
CCI_LINK = "http://www.kabuciao.com/tech/oscillator/cci.html"
UO_LINK = "http://www.kabuciao.com/tech/oscillator/kyukyoku.html"
STOCHASTIC_LINK = "http://www.kabuciao.com/tech/oscillator/stokyasu.html"
MACD_LINK = "http://www.kabuciao.com/tech/trend/macd.html"
WILLR_LINK = "http://www.moneypartners.co.jp/support/tech/wir.html"
VOLATILITY_LINK = "http://www.sevendata.co.jp/shihyou/jukyuu/volla.html"
ATR_LINK = "http://www.moneypartners.co.jp/support/tech/atr.html"

Rule = Callable[[Row, float], str]
Formatter = Callable[[object], str]


class Column(NamedTuple):
    """Describe a single column of an indicator table."""

    key: str
    label: str
    link: Optional[str] = None
    formatter: Formatter = round2
    rule: Optional[Rule] = None


class Cell(NamedTuple):
    """Hold the rendered text of a cell and its emphasis class."""

    text: str
    emphasis: str


def band(upper: float, lower: float, middle: str = "") -> Rule:
    """Emphasize values above the upper bound or below the lower bound."""

    def rule(row: Row, value: float) -> str:
        if value >= upper:
            return "up"
        if value <= lower:
            return "down"
        return middle

    return rule


def threshold(limit: float, above: str = "up", below: str = "down") -> Rule:
    """Emphasize values by comparing them with a single threshold."""

    def rule(row: Row, value: float) -> str:
        return above if value >= limit else below

    return rule


def above_only(limit: float) -> Rule:
    """Emphasize values above a threshold and leave the rest untouched."""

    def rule(row: Row, value: float) -> str:
        return "up" if value >= limit else ""

    return rule


def below_reference(reference: str) -> Rule:
    """Emphasize values that stay at or below another column of the row."""

    def rule(row: Row, value: float) -> str:
        return "up" if value <= to_float(row.get(reference)) else "down"

    return rule


def build_cells(row: Row, columns: Sequence[Column]) -> List[Cell]:
    """Render one table row as cells with their emphasis classes."""
    cells = []
    for column in columns:
        raw = row.get(column.key, "")
        emphasis = column.rule(row, to_float(raw)) if column.rule else ""
        cells.append(Cell(column.formatter(raw), emphasis))
    return cells


def build_rows(rows: Sequence[Row], columns: Sequence[Column]) -> List[List[Cell]]:
    """Render a series of rows with the given column definitions."""
    return [build_cells(row, columns) for row in rows]


SERIES_COLUMNS: Sequence[Column] = (
    Column("date", "日付", formatter=str),
    Column("open", "始値", formatter=number_with_delimiter),
    Column("high", "高値", formatter=number_with_delimiter),
    Column("low", "安値", formatter=number_with_delimiter),
    Column("adj_close", "終値", formatter=number_with_delimiter),
    Column("volume", "出来高", formatter=number_with_delimiter),
)

TREND_COLUMNS: Sequence[Column] = (
    Column("ewma5", "MA5", MA_LINK, number_with_delimiter),
    Column("ewma25", "MA25", MA_LINK, number_with_delimiter),
    Column("ewma50", "MA50", MA_LINK, number_with_delimiter),
    Column("ewma75", "MA75", MA_LINK, number_with_delimiter),
    Column("ewma200", "MA200", MA_LINK, number_with_delimiter),
    Column("upperband", "UPPER", BOLLINGER_LINK, number_with_delimiter),
    Column("lowerband", "LOWER", BOLLINGER_LINK, number_with_delimiter),
)

TREND_LATEST_COLUMNS: Sequence[Column] = tuple(TREND_COLUMNS) + (
    Column("sar", "SAR", SAR_LINK, number_with_delimiter),
)

_COMMON_OSCILLATOR_COLUMNS: Sequence[Column] = (
    Column("rsi9", "RSI9", RSI_LINK, rule=band(70, 30)),
    Column("rsi14", "RSI14", RSI_LINK, rule=band(70, 30)),
    Column("mfi14", "MFI", MFI_LINK, rule=band(80, 20)),
    Column("roc10", "ROC10", ROC_LINK, rule=threshold(0)),
    Column("roc25", "ROC25", ROC_LINK, rule=threshold(0)),
)

_TRAILING_OSCILLATOR_COLUMNS: Sequence[Column] = (
    Column("cci14", "CCI", CCI_LINK, rule=band(100, -100)),
    Column("ultosc", "UO", UO_LINK, rule=band(70, 35)),
    Column("slowk", "SLOWK", STOCHASTIC_LINK, rule=band(80, 20, "mid")),
    Column("slowd", "SLOWD", STOCHASTIC_LINK, rule=band(80, 20, "mid")),
    Column("fastk", "FASTK", STOCHASTIC_LINK, rule=band(80, 20, "mid")),
    Column("fastd", "FASTD", STOCHASTIC_LINK, rule=band(80, 20, "mid")),
    Column("macd", "MACD", MACD_LINK, rule=threshold(0)),
    Column("macdsignal", "SIG", MACD_LINK, rule=below_reference("macd")),
    Column("macdhist", "HIST", MACD_LINK, rule=threshold(0)),
    Column("willr14", "%R", WILLR_LINK, rule=band(-10, -90, "mid")),
    Column("vl", "VL", VOLATILITY_LINK, rule=above_only(5)),
    Column("tr", "TR", ATR_LINK, number_with_delimiter),
    Column("atr", "ATR", ATR_LINK),
    Column("natr", "NATR", ATR_LINK),
)

OSCILLATOR_COLUMNS: Sequence[Column] = tuple(_COMMON_OSCILLATOR_COLUMNS) + tuple(
    _TRAILING_OSCILLATOR_COLUMNS
)

OSCILLATOR_ALL_COLUMNS: Sequence[Column] = (
    (
        Column("ret_index", "RET", rule=threshold(1)),
        Column("sar", "SAR", SAR_LINK, number_with_delimiter),
    )
    + tuple(_COMMON_OSCILLATOR_COLUMNS)
    + (
        Column("roc50", "ROC50", ROC_LINK, rule=threshold(0)),
        Column("roc75", "ROC75", ROC_LINK, rule=threshold(0)),
        Column("roc150", "ROC150", ROC_LINK, rule=threshold(0)),
    )
    + tuple(_TRAILING_OSCILLATOR_COLUMNS)
)
