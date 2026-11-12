"""Reporting calendar and business constants.

MRR is a point-in-time metric, so all comparisons are made at calendar
month-end.  The dataset is static (a demo environment), therefore the
reporting window and the "as of" date are fixed.
"""

from __future__ import annotations

from datetime import date

AS_OF_DATE = date(2026, 11, 12)

# First and last *completed* reporting months.  2026-11 is the current,
# incomplete month and is deliberately excluded from MRR / bridge reports.
REPORT_START = date(2025, 1, 1)
REPORT_END = date(2026, 10, 1)

CURRENT_INCOMPLETE_MONTH = "2026-11"

CURRENCY = "CNY"
CURRENCY_SYMBOL = "¥"


CATEGORY_ORDER = (
    ("new", "新增"),
    ("reactivation", "回流"),
    ("resume", "恢复"),
    ("upgrade", "升级"),
    ("downgrade", "降级"),
    ("pause", "暂停"),
    ("churn", "流失"),
)

CATEGORY_LABELS = dict(CATEGORY_ORDER)

# The five categories requested for the movement bridge.  Pause / resume are
# surfaced separately so a temporary pause is never mis-labelled as churn or
# reactivation, while still reconciling to the exact MRR delta.
PRIMARY_CATEGORIES = ("new", "reactivation", "upgrade", "downgrade", "churn")

EVENT_LABELS = {
    "trial_start": "试用开始",
    "paid_start": "付费开始",
    "plan_change": "方案变更",
    "pause": "暂停",
    "resume": "恢复",
    "cancel_scheduled": "预约取消（到期生效）",
    "contract_end": "立即终止",
    "refund": "退款（现金）",
}
