#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# formatting.py: Value conversion and display helpers
#
#  Description:
#  Convert raw CSV fields into numbers and format them for display.
#  Fields may be empty, non numeric, or NaN, so conversions never raise
#  and fall back to zero, matching the tolerant behavior of the previous
#  Ruby implementation.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
########################################################################

import math
from typing import Any


def to_float(value: Any) -> float:
    """Convert a field to float, returning 0.0 when it is not a finite number."""
    if value is None:
        return 0.0
    try:
        number = float(str(value).strip().replace(",", ""))
    except ValueError:
        return 0.0
    if math.isnan(number) or math.isinf(number):
        return 0.0
    return number


def to_int(value: Any) -> int:
    """Convert a field to int by truncating toward zero."""
    return int(to_float(value))


def number_with_delimiter(value: Any) -> str:
    """Insert thousands separators into an integer value."""
    return "{:,}".format(to_int(value))


def round2(value: Any) -> str:
    """Format a field as a number rounded to two decimal places."""
    return "{:.2f}".format(to_float(value))


def percent(value: Any) -> str:
    """Append a percent sign to a raw ratio field."""
    return "{}%".format(str(value).strip())
