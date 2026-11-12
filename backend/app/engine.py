"""Event-sourced MRR reconstruction and movement analytics.

Core model
----------
* A contract's MRR is derived from its latest effective ``paid_start`` /
  ``plan_change`` event.
* Monthly contracts contribute their monthly amount; annual contracts
  contribute ``amount / 12``.
* A contract contributes zero before its paid start, while paused, after an
  end event, or while it is still a trial.
* A customer's MRR is the sum of all of that customer's contracts.  The
  customer layer is always calculated *before* movement classification, so an
  old contract ending as part of an upgrade is not mistaken for churn.

All amounts are CNY.  Calculations use 4-decimal Decimal arithmetic; API
responses expose 2-decimal display amounts plus an explicit rounding tail.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

import duckdb

from . import config
from .seed_data import SCENARIOS

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")
ZERO = Decimal("0.0000")

MRR_EVENT_TYPES = {
    "paid_start",
    "plan_change",
    "pause",
    "resume",
    "cancel_scheduled",
    "contract_end",
}
AMOUNT_EVENT_TYPES = {"paid_start", "plan_change"}
END_EVENT_TYPES = {"contract_end", "cancel_scheduled"}

STATUS_LABELS = {
    "active": "生效中",
    "scheduled_cancel": "已预约取消",
    "paused": "暂停中",
    "ended": "已终止",
    "trial": "试用中",
    "not_started": "未开始",
}


def q4(value: Decimal | int | float | str) -> Decimal:
    return Decimal(value).quantize(Q4, rounding=ROUND_HALF_UP)


def q2(value: Decimal | int | float | str) -> Decimal:
    return Decimal(value).quantize(Q2, rounding=ROUND_HALF_UP)


def f2(value: Decimal | int | float | str) -> float:
    return float(q2(value))


def f4(value: Decimal | int | float | str) -> float:
    return float(q4(value))


def month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_start(key: str) -> date:
    year, month = (int(part) for part in key.split("-"))
    return date(year, month, 1)


def month_end(key: str) -> date:
    year, month = (int(part) for part in key.split("-"))
    return date(year, month, calendar.monthrange(year, month)[1])


def previous_month(key: str) -> str:
    start = month_start(key)
    return month_key(start - timedelta(days=1))


def iter_month_keys(start: date, end: date) -> list[str]:
    current = date(start.year, start.month, 1)
    stop = date(end.year, end.month, 1)
    keys: list[str] = []
    while current <= stop:
        keys.append(month_key(current))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return keys


@dataclass(frozen=True)
class Contract:
    contract_id: str
    customer_id: str
    plan_name: str
    billing_cycle: str
    amount_rmb: Decimal
    currency: str
    signed_date: date


@dataclass(frozen=True)
class Event:
    event_id: str
    event_order: int
    contract_id: str
    customer_id: str
    event_type: str
    event_date: date
    effective_date: date
    amount_rmb: Decimal | None
    billing_cycle: str | None
    note: str


@dataclass(frozen=True)
class ContractState:
    contract: Contract
    status: str
    status_label: str
    amount_rmb: Decimal | None
    billing_cycle: str | None
    mrr_rmb: Decimal
    scheduled_effective_date: date | None = None


class MrrEngine:
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        as_of: date = config.AS_OF_DATE,
        report_start: date = config.REPORT_START,
        report_end: date = config.REPORT_END,
    ) -> None:
        self.conn = conn
        self.as_of = as_of
        self.report_start = report_start
        self.report_end = report_end
        self.months = iter_month_keys(report_start, report_end)
        self.last_completed_month = self.months[-1]

        self._load()
        self._build_month_snapshots()
        self._build_event_effects()
        self._persist()
        self._build_cohorts()
        self._build_retention()

        self._bridge_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        customer_rows = self.conn.execute(
            "SELECT customer_id, name, city, segment, created_at FROM customers"
        ).fetchall()
        self.customers = {
            row[0]: {
                "customer_id": row[0],
                "name": row[1],
                "city": row[2],
                "segment": row[3],
                "created_at": row[4],
            }
            for row in customer_rows
        }

        contract_rows = self.conn.execute(
            """
            SELECT contract_id, customer_id, plan_name, billing_cycle,
                   amount_rmb, currency, signed_date
            FROM contracts
            """
        ).fetchall()
        self.contracts = {
            row[0]: Contract(
                contract_id=row[0],
                customer_id=row[1],
                plan_name=row[2],
                billing_cycle=row[3],
                amount_rmb=q4(row[4]),
                currency=row[5],
                signed_date=row[6],
            )
            for row in contract_rows
        }
        self.contracts_by_customer: dict[str, list[Contract]] = defaultdict(list)
        for contract in self.contracts.values():
            self.contracts_by_customer[contract.customer_id].append(contract)
        for contracts in self.contracts_by_customer.values():
            contracts.sort(key=lambda item: (item.signed_date, item.contract_id))

        event_rows = self.conn.execute(
            """
            SELECT event_id, event_order, contract_id, customer_id, event_type,
                   event_date, effective_date, amount_rmb, billing_cycle, note
            FROM contract_events
            ORDER BY effective_date, event_order
            """
        ).fetchall()
        self.events = [
            Event(
                event_id=row[0],
                event_order=row[1],
                contract_id=row[2],
                customer_id=row[3],
                event_type=row[4],
                event_date=row[5],
                effective_date=row[6],
                amount_rmb=q4(row[7]) if row[7] is not None else None,
                billing_cycle=row[8],
                note=row[9] or "",
            )
            for row in event_rows
        ]
        self.events_by_contract: dict[str, list[Event]] = defaultdict(list)
        self.events_by_customer: dict[str, list[Event]] = defaultdict(list)
        for event in self.events:
            self.events_by_contract[event.contract_id].append(event)
            self.events_by_customer[event.customer_id].append(event)
        for event_list in self.events_by_contract.values():
            event_list.sort(key=lambda item: (item.effective_date, item.event_order))
        for event_list in self.events_by_customer.values():
            event_list.sort(key=lambda item: (item.effective_date, item.event_order))

        self.paid_starts_by_customer: dict[str, list[date]] = defaultdict(list)
        for event in self.events:
            if event.event_type == "paid_start":
                self.paid_starts_by_customer[event.customer_id].append(event.effective_date)

    # --------------------------------------------------------------- state
    @staticmethod
    def _mrr_for_terms(amount_rmb: Decimal | None, billing_cycle: str | None) -> Decimal:
        if amount_rmb is None:
            return ZERO
        if billing_cycle == "annual":
            return q4(amount_rmb / Decimal(12))
        if billing_cycle == "monthly":
            return q4(amount_rmb)
        return ZERO

    def _events_up_to(
        self,
        contract_id: str,
        at_date: date,
        seq_cutoff: int | None = None,
        inclusive: bool = True,
    ) -> list[Event]:
        selected: list[Event] = []
        for event in self.events_by_contract.get(contract_id, []):
            if event.effective_date < at_date:
                selected.append(event)
            elif event.effective_date == at_date:
                if seq_cutoff is None:
                    selected.append(event)
                elif inclusive and event.event_order <= seq_cutoff:
                    selected.append(event)
                elif not inclusive and event.event_order < seq_cutoff:
                    selected.append(event)
            else:
                break
        return selected

    def _pending_cancel_date(self, contract_id: str, at_date: date) -> date | None:
        pending: list[date] = []
        for event in self.events_by_contract.get(contract_id, []):
            if (
                event.event_type == "cancel_scheduled"
                and event.event_date <= at_date < event.effective_date
            ):
                pending.append(event.effective_date)
        return min(pending) if pending else None

    def state_at(
        self,
        contract: Contract,
        at_date: date,
        seq_cutoff: int | None = None,
        inclusive: bool = True,
    ) -> ContractState:
        events = self._events_up_to(contract.contract_id, at_date, seq_cutoff, inclusive)
        amount_event: Event | None = None
        paused = False
        for event in events:
            if event.event_type in AMOUNT_EVENT_TYPES:
                amount_event = event
            if event.event_type == "pause":
                paused = True
            elif event.event_type == "resume":
                paused = False

        ended = any(event.event_type in END_EVENT_TYPES for event in events)
        trial = any(event.event_type == "trial_start" for event in events)
        pending_date = self._pending_cancel_date(contract.contract_id, at_date)

        amount_rmb = amount_event.amount_rmb if amount_event else contract.amount_rmb
        billing_cycle = (
            amount_event.billing_cycle if amount_event and amount_event.billing_cycle else contract.billing_cycle
        )

        if ended:
            status = "ended"
            mrr = ZERO
        elif paused:
            status = "paused"
            mrr = ZERO
        elif amount_event is not None:
            status = "scheduled_cancel" if pending_date else "active"
            mrr = self._mrr_for_terms(amount_event.amount_rmb, billing_cycle)
        elif trial:
            status = "trial"
            mrr = ZERO
        else:
            status = "not_started"
            mrr = ZERO

        return ContractState(
            contract=contract,
            status=status,
            status_label=STATUS_LABELS[status],
            amount_rmb=q4(amount_rmb) if amount_rmb is not None else None,
            billing_cycle=billing_cycle,
            mrr_rmb=mrr,
            scheduled_effective_date=pending_date,
        )

    def customer_snapshot(
        self,
        customer_id: str,
        at_date: date,
        seq_cutoff: int | None = None,
        inclusive: bool = True,
    ) -> dict:
        states = [
            self.state_at(contract, at_date, seq_cutoff, inclusive)
            for contract in self.contracts_by_customer.get(customer_id, [])
        ]
        mrr = q4(sum((state.mrr_rmb for state in states), ZERO))
        customer = self.customers[customer_id]
        return {
            "customer_id": customer_id,
            "name": customer["name"],
            "city": customer["city"],
            "segment": customer["segment"],
            "mrr_rmb": mrr,
            "contracts": states,
        }

    # ----------------------------------------------------------- snapshots
    def _build_month_snapshots(self) -> None:
        self.month_customer_mrr: dict[str, dict[str, Decimal]] = {}
        self.month_customer_snapshot: dict[str, dict[str, dict]] = {}
        self.month_contract_states: dict[str, dict[str, ContractState]] = {}

        for month in self.months:
            snap_date = month_end(month)
            customer_mrr: dict[str, Decimal] = {}
            customer_snapshots: dict[str, dict] = {}
            contract_states: dict[str, ContractState] = {}
            for customer_id in self.customers:
                snapshot = self.customer_snapshot(customer_id, snap_date)
                customer_snapshots[customer_id] = snapshot
                customer_mrr[customer_id] = snapshot["mrr_rmb"]
                for state in snapshot["contracts"]:
                    contract_states[state.contract.contract_id] = state
            self.month_customer_mrr[month] = customer_mrr
            self.month_customer_snapshot[month] = customer_snapshots
            self.month_contract_states[month] = contract_states

        self.prior_month_snapshot = {
            customer_id: self.customer_snapshot(customer_id, month_start(self.months[0]) - timedelta(days=1))
            for customer_id in self.customers
        }

    def _prior_mrr(self, month: str) -> dict[str, Decimal]:
        prev_month = previous_month(month)
        if prev_month in self.month_customer_mrr:
            return self.month_customer_mrr[prev_month]
        return {customer_id: snap["mrr_rmb"] for customer_id, snap in self.prior_month_snapshot.items()}

    # --------------------------------------------------------- event effects
    def _customer_mrr_at(
        self,
        customer_id: str,
        at_date: date,
        seq_cutoff: int,
        inclusive: bool,
    ) -> Decimal:
        return q4(
            sum(
                (
                    self.state_at(contract, at_date, seq_cutoff, inclusive).mrr_rmb
                    for contract in self.contracts_by_customer.get(customer_id, [])
                ),
                ZERO,
            )
        )

    def _build_event_effects(self) -> None:
        self.event_effects: list[dict] = []
        for event in self.events:
            if event.event_type not in MRR_EVENT_TYPES:
                continue
            before = self._customer_mrr_at(
                event.customer_id, event.effective_date, event.event_order, inclusive=False
            )
            after = self._customer_mrr_at(
                event.customer_id, event.effective_date, event.event_order, inclusive=True
            )
            self.event_effects.append(
                {
                    "event_id": event.event_id,
                    "event_order": event.event_order,
                    "month": month_key(event.effective_date),
                    "contract_id": event.contract_id,
                    "customer_id": event.customer_id,
                    "event_type": event.event_type,
                    "event_date": event.event_date,
                    "effective_date": event.effective_date,
                    "amount_rmb": event.amount_rmb,
                    "billing_cycle": event.billing_cycle,
                    "note": event.note,
                    "before_mrr_rmb": before,
                    "after_mrr_rmb": after,
                    "delta_rmb": q4(after - before),
                }
            )
        self.effects_by_month: dict[str, list[dict]] = defaultdict(list)
        self.effects_by_customer_month: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for effect in self.event_effects:
            self.effects_by_month[effect["month"]].append(effect)
            self.effects_by_customer_month[(effect["customer_id"], effect["month"])].append(effect)
        for effects in self.effects_by_month.values():
            effects.sort(key=lambda item: (item["effective_date"], item["event_order"]))

    # ------------------------------------------------------------- persist
    def _persist(self) -> None:
        self.conn.execute("DROP TABLE IF EXISTS monthly_contract_mrr")
        self.conn.execute(
            """
            CREATE TABLE monthly_contract_mrr (
                month VARCHAR,
                snapshot_date DATE,
                customer_id VARCHAR,
                contract_id VARCHAR,
                plan_name VARCHAR,
                billing_cycle VARCHAR,
                amount_rmb DECIMAL(18, 4),
                mrr_rmb DECIMAL(18, 4),
                status VARCHAR
            )
            """
        )
        contract_rows = []
        for month in self.months:
            snap_date = month_end(month)
            for contract_id, state in self.month_contract_states[month].items():
                contract_rows.append(
                    (
                        month,
                        snap_date,
                        state.contract.customer_id,
                        contract_id,
                        state.contract.plan_name,
                        state.billing_cycle,
                        state.amount_rmb,
                        state.mrr_rmb,
                        state.status,
                    )
                )
        if contract_rows:
            self.conn.executemany(
                "INSERT INTO monthly_contract_mrr VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                contract_rows,
            )

        self.conn.execute("DROP TABLE IF EXISTS monthly_customer_mrr")
        self.conn.execute(
            """
            CREATE TABLE monthly_customer_mrr (
                month VARCHAR,
                snapshot_date DATE,
                customer_id VARCHAR,
                mrr_rmb DECIMAL(18, 4)
            )
            """
        )
        customer_rows = [
            (month, month_end(month), customer_id, mrr)
            for month in self.months
            for customer_id, mrr in self.month_customer_mrr[month].items()
        ]
        self.conn.executemany(
            "INSERT INTO monthly_customer_mrr VALUES (?, ?, ?, ?)", customer_rows
        )

        self.conn.execute("DROP TABLE IF EXISTS event_effects")
        self.conn.execute(
            """
            CREATE TABLE event_effects (
                event_id VARCHAR,
                event_order INTEGER,
                month VARCHAR,
                contract_id VARCHAR,
                customer_id VARCHAR,
                event_type VARCHAR,
                event_date DATE,
                effective_date DATE,
                before_mrr_rmb DECIMAL(18, 4),
                after_mrr_rmb DECIMAL(18, 4),
                delta_rmb DECIMAL(18, 4)
            )
            """
        )
        if self.event_effects:
            self.conn.executemany(
                """
                INSERT INTO event_effects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        effect["event_id"],
                        effect["event_order"],
                        effect["month"],
                        effect["contract_id"],
                        effect["customer_id"],
                        effect["event_type"],
                        effect["event_date"],
                        effect["effective_date"],
                        effect["before_mrr_rmb"],
                        effect["after_mrr_rmb"],
                        effect["delta_rmb"],
                    )
                    for effect in self.event_effects
                ],
            )

        self.conn.execute("DROP TABLE IF EXISTS month_dim")
        self.conn.execute(
            """
            CREATE TABLE month_dim (
                month VARCHAR,
                month_start DATE,
                month_end DATE
            )
            """
        )
        self.conn.executemany(
            "INSERT INTO month_dim VALUES (?, ?, ?)",
            [(month, month_start(month), month_end(month)) for month in self.months],
        )

    def _build_cohorts(self) -> None:
        self.conn.execute("DROP TABLE IF EXISTS customer_cohorts")
        self.conn.execute(
            """
            CREATE TABLE customer_cohorts AS
            SELECT customer_id,
                   strftime(min(effective_date), '%Y-%m') AS first_paid_month
            FROM contract_events
            WHERE event_type = 'paid_start'
            GROUP BY customer_id
            """
        )
        rows = self.conn.execute(
            "SELECT customer_id, first_paid_month FROM customer_cohorts"
        ).fetchall()
        self.cohort_by_customer = {row[0]: row[1] for row in rows}

    def _build_retention(self) -> None:
        cohort_sizes = {
            row[0]: int(row[1])
            for row in self.conn.execute(
                "SELECT first_paid_month, count(*) FROM customer_cohorts GROUP BY 1"
            ).fetchall()
        }
        aggregate = {
            (row[0], row[1]): (int(row[2]), int(row[3]))
            for row in self.conn.execute(
                """
                SELECT co.first_paid_month, cm.month,
                       count(DISTINCT cm.customer_id) AS cohort_size,
                       count(DISTINCT CASE WHEN cm.mrr_rmb > 0 THEN cm.customer_id END) AS active_count
                FROM customer_cohorts co
                JOIN monthly_customer_mrr cm ON cm.customer_id = co.customer_id
                WHERE cm.month >= co.first_paid_month
                GROUP BY 1, 2
                """
            ).fetchall()
        }

        retention_months = list(self.months)
        if config.CURRENT_INCOMPLETE_MONTH not in retention_months:
            retention_months.append(config.CURRENT_INCOMPLETE_MONTH)

        cohorts = sorted(cohort_sizes)
        cohort_rows: list[dict] = []
        for cohort in cohorts:
            size = cohort_sizes[cohort]
            cells: list[dict] = []
            for month in retention_months:
                if month < cohort:
                    status = "before"
                    cells.append(
                        {
                            "month": month,
                            "status": status,
                            "active_count": None,
                            "cohort_size": size,
                            "rate": None,
                            "rate_pct": None,
                        }
                    )
                    continue
                if month > self.last_completed_month:
                    cells.append(
                        {
                            "month": month,
                            "status": "future",
                            "active_count": None,
                            "cohort_size": size,
                            "rate": None,
                            "rate_pct": None,
                        }
                    )
                    continue
                aggregate_size, active = aggregate.get((cohort, month), (size, 0))
                rate = q4(Decimal(active) / Decimal(aggregate_size)) if aggregate_size else ZERO
                cells.append(
                    {
                        "month": month,
                        "status": "ok",
                        "active_count": active,
                        "cohort_size": aggregate_size,
                        "rate": f4(rate),
                        "rate_pct": f4(rate * Decimal(100)),
                    }
                )
            cohort_rows.append(
                {
                    "cohort": cohort,
                    "cohort_size": size,
                    "cells": cells,
                }
            )

        self.retention = {
            "months": retention_months,
            "last_completed_month": self.last_completed_month,
            "future_months": [m for m in retention_months if m > self.last_completed_month],
            "cohorts": cohort_rows,
            "note": (
                "按首付月份分组；单元格 = 该月末客户 MRR > 0 的客户数 / 该首付月份客户数。"
                "首付月份之前的月份不适用；尚未结束的月份留空。"
            ),
        }

    # ------------------------------------------------------------- helpers
    def _event_type_label(self, event_type: str) -> str:
        return config.EVENT_LABELS.get(event_type, event_type)

    def _effect_payload(self, effect: dict, in_bridge: bool, treatment: str) -> dict:
        contract = self.contracts.get(effect["contract_id"])
        delta = effect["delta_rmb"]
        effect_label = "增加" if delta > 0 else ("减少" if delta < 0 else "不变")
        return {
            "event_id": effect["event_id"],
            "contract_id": effect["contract_id"],
            "plan_name": contract.plan_name if contract else "",
            "event_type": effect["event_type"],
            "event_type_label": self._event_type_label(effect["event_type"]),
            "event_date": effect["event_date"].isoformat(),
            "effective_date": effect["effective_date"].isoformat(),
            "amount_rmb": f2(effect["amount_rmb"]) if effect["amount_rmb"] is not None else None,
            "billing_cycle": effect["billing_cycle"],
            "before_mrr_rmb": f2(effect["before_mrr_rmb"]),
            "after_mrr_rmb": f2(effect["after_mrr_rmb"]),
            "delta_rmb": f2(delta),
            "delta_exact_rmb": f4(delta),
            "effect_label": effect_label,
            "note": effect["note"],
            "in_bridge": in_bridge,
            "treatment": treatment,
        }

    def _state_payload(self, state: ContractState) -> dict:
        return {
            "contract_id": state.contract.contract_id,
            "plan_name": state.contract.plan_name,
            "billing_cycle": state.billing_cycle,
            "amount_rmb": f2(state.amount_rmb) if state.amount_rmb is not None else None,
            "mrr_rmb": f2(state.mrr_rmb),
            "status": state.status,
            "status_label": state.status_label,
            "scheduled_effective_date": (
                state.scheduled_effective_date.isoformat() if state.scheduled_effective_date else None
            ),
            "signed_date": state.contract.signed_date.isoformat(),
        }

    def _snapshot_payload(self, snapshot: dict) -> dict:
        return {
            "customer_id": snapshot["customer_id"],
            "name": snapshot["name"],
            "city": snapshot["city"],
            "segment": snapshot["segment"],
            "mrr_rmb": f2(snapshot["mrr_rmb"]),
            "contracts": [self._state_payload(state) for state in snapshot["contracts"]],
        }

    # --------------------------------------------------------------- bridge
    def _classify(
        self,
        prev_mrr: Decimal,
        end_mrr: Decimal,
        customer_effects: list[dict],
        end_snapshot: dict,
        paid_before_month: bool,
    ) -> tuple[str, str]:
        if prev_mrr == 0 and end_mrr > 0:
            if any(effect["event_type"] == "resume" and effect["delta_rmb"] > 0 for effect in customer_effects):
                return "resume", "暂停后恢复计费"
            if paid_before_month:
                return "reactivation", "曾付费，本月重新产生正 MRR"
            return "new", "月初前从未付费，本月首次产生正 MRR"
        if prev_mrr > 0 and end_mrr == 0:
            ended_in_month = any(
                effect["event_type"] in END_EVENT_TYPES and effect["delta_rmb"] < 0
                for effect in customer_effects
            )
            paused_at_end = any(
                state.status == "paused" for state in end_snapshot["contracts"]
            )
            if ended_in_month:
                return "churn", "合同终止或到期取消，客户 MRR 归零"
            if paused_at_end:
                return "pause", "合同暂停，暂停期间 MRR 为零"
            return "churn", "客户 MRR 归零"
        if prev_mrr > 0 and end_mrr > 0:
            if end_mrr > prev_mrr:
                return "upgrade", "客户层 MRR 增加"
            if end_mrr < prev_mrr:
                return "downgrade", "客户层 MRR 减少"
            return "none", "客户层 MRR 与上月末持平"
        return "none", "客户层月初月末均为零"

    def bridge(self, month: str) -> dict:
        if month in self._bridge_cache:
            return self._bridge_cache[month]
        if month not in self.months:
            raise ValueError(f"month {month} is outside the reporting window")

        prev_mrr_by_customer = self._prior_mrr(month)
        end_mrr_by_customer = self.month_customer_mrr[month]
        end_snapshots = self.month_customer_snapshot[month]
        month_first_day = month_start(month)

        all_customers = sorted(set(prev_mrr_by_customer) | set(end_mrr_by_customer))
        items_by_category: dict[str, list[dict]] = defaultdict(list)
        offset_groups: list[dict] = []
        event_ledger: list[dict] = []

        for customer_id in all_customers:
            prev_mrr = q4(prev_mrr_by_customer.get(customer_id, ZERO))
            end_mrr = q4(end_mrr_by_customer.get(customer_id, ZERO))
            customer_effects = self.effects_by_customer_month.get((customer_id, month), [])
            paid_before = any(
                paid_date < month_first_day
                for paid_date in self.paid_starts_by_customer.get(customer_id, [])
            )
            category, reason = self._classify(
                prev_mrr,
                end_mrr,
                customer_effects,
                end_snapshots[customer_id],
                paid_before,
            )
            delta = q4(end_mrr - prev_mrr)

            treatment = config.CATEGORY_LABELS.get(category, "月内抵消")
            for effect in customer_effects:
                event_treatment = (
                    f"计入桥接：{treatment}"
                    if category != "none"
                    else ("月内抵消（不进桥接）" if effect["delta_rmb"] != 0 else "MRR 不变")
                )
                event_ledger.append(
                    self._effect_payload(
                        effect,
                        in_bridge=category != "none",
                        treatment=event_treatment,
                    )
                )

            if category == "none":
                if customer_effects:
                    exact_sum = q4(sum((effect["delta_rmb"] for effect in customer_effects), ZERO))
                    if exact_sum == 0 and any(effect["delta_rmb"] != 0 for effect in customer_effects):
                        positive = q4(
                            sum(
                                (effect["delta_rmb"] for effect in customer_effects if effect["delta_rmb"] > 0),
                                ZERO,
                            )
                        )
                        offset_groups.append(
                            {
                                "customer_id": customer_id,
                                "customer_name": self.customers[customer_id]["name"],
                                "city": self.customers[customer_id]["city"],
                                "mrr_before_rmb": f2(prev_mrr),
                                "mrr_after_rmb": f2(end_mrr),
                                "offset_rmb": f2(positive),
                                "net_delta_rmb": f2(exact_sum),
                                "events": [
                                    self._effect_payload(
                                        effect,
                                        in_bridge=False,
                                        treatment="月内抵消（不进桥接）",
                                    )
                                    for effect in customer_effects
                                ],
                            }
                        )
                continue

            customer = self.customers[customer_id]
            items_by_category[category].append(
                {
                    "customer_id": customer_id,
                    "customer_name": customer["name"],
                    "city": customer["city"],
                    "segment": customer["segment"],
                    "category": category,
                    "category_label": config.CATEGORY_LABELS[category],
                    "reason": reason,
                    "mrr_before_rmb": f2(prev_mrr),
                    "mrr_after_rmb": f2(end_mrr),
                    "delta_rmb": f2(delta),
                    "delta_exact_rmb": f4(delta),
                    "event_count": len(customer_effects),
                    "events": [
                        self._effect_payload(effect, in_bridge=True, treatment=treatment)
                        for effect in customer_effects
                    ],
                }
            )

        for category, items in items_by_category.items():
            items.sort(key=lambda item: (abs(item["delta_exact_rmb"]), item["customer_name"]), reverse=True)
        offset_groups.sort(key=lambda item: (item["offset_rmb"], item["customer_name"]), reverse=True)
        event_ledger.sort(key=lambda item: (item["effective_date"], item["event_id"]))

        begin = q4(sum((prev_mrr_by_customer.get(cid, ZERO) for cid in all_customers), ZERO))
        end = q4(sum((end_mrr_by_customer.get(cid, ZERO) for cid in all_customers), ZERO))
        net_change = q4(end - begin)

        components: list[dict] = []
        for key, label in config.CATEGORY_ORDER:
            items = items_by_category.get(key, [])
            exact = q4(sum((Decimal(str(item["delta_exact_rmb"])) for item in items), ZERO))
            components.append(
                {
                    "key": key,
                    "label": label,
                    "count": len(items),
                    "amount_rmb": f2(exact),
                    "amount_exact_rmb": f4(exact),
                    "items": items,
                }
            )

        # Reconciliation in exact arithmetic: begin + category deltas = end.
        internal_components_sum = q4(
            sum((Decimal(str(component["amount_exact_rmb"])) for component in components), ZERO)
        )
        internal_difference = q4(end - begin - internal_components_sum)

        # Display arithmetic: every category, the beginning and the end are
        # rounded independently.  The residual is surfaced as its own step.
        begin_display = q2(begin)
        end_display = q2(end)
        component_displays = [
            q2(component["amount_exact_rmb"]) for component in components if component["count"] > 0
        ]
        component_display_sum = q2(sum(component_displays, ZERO))
        rounding_adjustment = q2(end_display - begin_display - component_display_sum)

        waterfall: list[dict] = [
            {
                "key": "beginning",
                "label": "期初 MRR",
                "value_rmb": float(begin_display),
                "kind": "total",
                "category": None,
                "count": None,
            }
        ]
        running = begin_display
        for component in components:
            if component["count"] == 0:
                continue
            value = q2(component["amount_exact_rmb"])
            running = q2(running + value)
            waterfall.append(
                {
                    "key": component["key"],
                    "label": component["label"],
                    "value_rmb": float(value),
                    "kind": "positive" if value >= 0 else "negative",
                    "category": component["key"],
                    "count": component["count"],
                    "cumulative_rmb": float(running),
                }
            )
        if rounding_adjustment != 0:
            running = q2(running + rounding_adjustment)
            waterfall.append(
                {
                    "key": "rounding",
                    "label": "舍入尾差",
                    "value_rmb": float(rounding_adjustment),
                    "kind": "rounding",
                    "category": "rounding",
                    "count": None,
                    "cumulative_rmb": float(running),
                }
            )
        waterfall.append(
            {
                "key": "ending",
                "label": "期末 MRR",
                "value_rmb": float(end_display),
                "kind": "total",
                "category": None,
                "count": None,
                "cumulative_rmb": float(end_display),
            }
        )

        # Scheduled cancellations requested but not yet effective at month-end.
        pending_changes: list[dict] = []
        for event in self.events:
            if (
                event.event_type == "cancel_scheduled"
                and event.event_date <= month_end(month) < event.effective_date
            ):
                state = self.month_contract_states[month].get(event.contract_id)
                if state is None:
                    continue
                pending_changes.append(
                    {
                        "customer_id": event.customer_id,
                        "customer_name": self.customers[event.customer_id]["name"],
                        "contract_id": event.contract_id,
                        "plan_name": self.contracts[event.contract_id].plan_name,
                        "requested_on": event.event_date.isoformat(),
                        "effective_date": event.effective_date.isoformat(),
                        "mrr_rmb": f2(state.mrr_rmb),
                        "note": event.note,
                    }
                )
        pending_changes.sort(key=lambda item: item["effective_date"])

        refunds = [
            {
                "event_id": event.event_id,
                "customer_id": event.customer_id,
                "customer_name": self.customers[event.customer_id]["name"],
                "contract_id": event.contract_id,
                "event_date": event.event_date.isoformat(),
                "amount_rmb": f2(event.amount_rmb or ZERO),
                "note": event.note,
            }
            for event in self.events
            if event.event_type == "refund"
            and month_start(month) <= event.event_date <= month_end(month)
        ]
        refund_total = q4(
            sum((Decimal(str(item["amount_rmb"])) for item in refunds), ZERO)
        )

        rounded_note = (
            "显示金额按分四舍五入。各分项显示值相加与期初/期末显示值存在 "
            f"{f2(rounding_adjustment):,.2f} 元尾差，已作为独立步骤列示；它不是现金变动。"
            if rounding_adjustment != 0
            else "显示金额按分四舍五入，桥接分项相加恰好等于期末显示值。"
        )

        result = {
            "month": month,
            "month_label": f"{month.split('-')[0]} 年 {int(month.split('-')[1])} 月",
            "period": {
                "month_start": month_first_day.isoformat(),
                "month_end": month_end(month).isoformat(),
                "previous_month": previous_month(month),
                "previous_month_end": (month_first_day - timedelta(days=1)).isoformat(),
            },
            "beginning_mrr_rmb": f2(begin),
            "ending_mrr_rmb": f2(end),
            "net_change_rmb": f2(net_change),
            "net_change_pct": f4(net_change / begin * Decimal(100)) if begin else None,
            "components": components,
            "waterfall": waterfall,
            "offset_ledger": offset_groups,
            "event_ledger": event_ledger,
            "pending_changes": pending_changes,
            "refunds": refunds,
            "refund_total_rmb": f2(refund_total),
            "reconciliation": {
                "beginning_mrr_rmb": f4(begin),
                "ending_mrr_rmb": f4(end),
                "components_sum_rmb": f4(internal_components_sum),
                "difference_rmb": f4(internal_difference),
                "displayed_beginning_mrr_rmb": float(begin_display),
                "displayed_ending_mrr_rmb": float(end_display),
                "displayed_components_sum_rmb": float(component_display_sum),
                "rounding_adjustment_rmb": float(rounding_adjustment),
                "note": rounded_note,
            },
        }
        self._bridge_cache[month] = result
        return result

    # -------------------------------------------------------------- retention
    def retention_report(self) -> dict:
        return self.retention

    def retention_cell(self, cohort: str, month: str) -> dict:
        if month not in self.months:
            raise ValueError(f"month {month} is outside the reporting window")
        cohort_customers = sorted(
            customer_id
            for customer_id, first_month in self.cohort_by_customer.items()
            if first_month == cohort
        )
        if not cohort_customers:
            raise KeyError(cohort)
        if month < cohort:
            raise ValueError("month is before the cohort month")

        active: list[dict] = []
        inactive: list[dict] = []
        for customer_id in cohort_customers:
            mrr = q4(self.month_customer_mrr[month].get(customer_id, ZERO))
            entry = {
                "customer_id": customer_id,
                "customer_name": self.customers[customer_id]["name"],
                "city": self.customers[customer_id]["city"],
                "segment": self.customers[customer_id]["segment"],
                "mrr_rmb": f2(mrr),
                "status": "active" if mrr > 0 else "zero",
            }
            (active if mrr > 0 else inactive).append(entry)

        size = len(cohort_customers)
        rate = q4(Decimal(len(active)) / Decimal(size)) if size else ZERO
        return {
            "cohort": cohort,
            "month": month,
            "month_end": month_end(month).isoformat(),
            "cohort_size": size,
            "active_count": len(active),
            "inactive_count": len(inactive),
            "rate_pct": f4(rate * Decimal(100)),
            "active_customers": active,
            "inactive_customers": inactive,
            "note": "活跃 = 该月末客户层 MRR > 0；零 MRR 包含流失、暂停或全部合同未生效。",
        }

    # ----------------------------------------------------------- detail
    def customer_detail(self, customer_id: str, month: str) -> dict:
        if customer_id not in self.customers:
            raise KeyError(customer_id)
        if month not in self.months:
            raise ValueError(f"month {month} is outside the reporting window")

        bridge = self.bridge(month)
        item = None
        for component in bridge["components"]:
            for candidate in component["items"]:
                if candidate["customer_id"] == customer_id:
                    item = candidate
                    break
            if item:
                break

        snap_after = self.customer_snapshot(customer_id, month_end(month))
        snap_before = self.customer_snapshot(
            customer_id, month_start(month) - timedelta(days=1)
        )

        # Events that were recorded or became effective during the month.
        effect_ids = {
            effect["event_id"]
            for effect in self.effects_by_customer_month.get((customer_id, month), [])
        }
        detail_events: list[dict] = []
        for effect in self.effects_by_customer_month.get((customer_id, month), []):
            if item and item["category"] != "none":
                treatment = f"计入桥接：{config.CATEGORY_LABELS[item['category']]}"
            elif effect["delta_rmb"] != 0:
                treatment = "月内抵消（不进桥接）"
            else:
                treatment = "MRR 不变"
            detail_events.append(
                self._effect_payload(
                    effect,
                    in_bridge=bool(item and item["category"] != "none"),
                    treatment=treatment,
                )
            )

        all_month_events = [
            event
            for event in self.events_by_customer.get(customer_id, [])
            if month_start(month) <= event.event_date <= month_end(month)
            or month_start(month) <= event.effective_date <= month_end(month)
        ]
        for event in all_month_events:
            if event.event_id in effect_ids:
                continue
            before = after = ZERO
            if event.event_type not in ("refund", "trial_start"):
                before = self.customer_snapshot(customer_id, event.effective_date, event.event_order, inclusive=False)["mrr_rmb"]
                after = self.customer_snapshot(customer_id, event.effective_date, event.event_order, inclusive=True)["mrr_rmb"]
            else:
                after = before = self.customer_snapshot(customer_id, event.event_date)["mrr_rmb"]
            detail_events.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "plan_name": self.contracts[event.contract_id].plan_name,
                    "event_type": event.event_type,
                    "event_type_label": self._event_type_label(event.event_type),
                    "event_date": event.event_date.isoformat(),
                    "effective_date": event.effective_date.isoformat(),
                    "amount_rmb": f2(event.amount_rmb) if event.amount_rmb is not None else None,
                    "billing_cycle": event.billing_cycle,
                    "before_mrr_rmb": f2(before),
                    "after_mrr_rmb": f2(after),
                    "delta_rmb": f2(q4(after - before)),
                    "delta_exact_rmb": f4(q4(after - before)),
                    "note": event.note,
                    "in_bridge": event.event_id in effect_ids,
                    "treatment": "现金指标" if event.event_type == "refund" else ("试用不计" if event.event_type == "trial_start" else ("待生效" if event.effective_date > month_end(month) else "")),
                }
            )

        detail_events.sort(key=lambda item: (item["event_date"], item["event_id"]))

        before_contracts = {
            state.contract.contract_id: state for state in snap_before["contracts"]
        }
        after_contracts = {
            state.contract.contract_id: state for state in snap_after["contracts"]
        }
        contract_rows: list[dict] = []
        for contract_id in sorted(set(before_contracts) | set(after_contracts)):
            state_before = before_contracts.get(contract_id)
            state_after = after_contracts.get(contract_id)
            contract = self.contracts[contract_id]
            contract_rows.append(
                {
                    "contract_id": contract_id,
                    "plan_name": contract.plan_name,
                    "billing_cycle": (state_after.billing_cycle if state_after else (state_before.billing_cycle if state_before else contract.billing_cycle)),
                    "amount_rmb": f2(
                        (state_after.amount_rmb if state_after and state_after.amount_rmb is not None else contract.amount_rmb)
                    ),
                    "signed_date": contract.signed_date.isoformat(),
                    "before": self._state_payload(state_before) if state_before else None,
                    "after": self._state_payload(state_after) if state_after else None,
                }
            )

        trend_rows = [
            (
                month_key_value,
                mrr,
            )
            for month_key_value, mrr in sorted(self.month_customer_mrr.items())
            if month_key_value <= month
        ]
        trend = [
            {"month": key, "mrr_rmb": f2(mrr.get(customer_id, ZERO))}
            for key, mrr in trend_rows
        ][-12:]

        pending_changes = [
            change
            for change in bridge["pending_changes"]
            if change["customer_id"] == customer_id
        ]
        refunds = [
            refund for refund in bridge["refunds"] if refund["customer_id"] == customer_id
        ]

        category = item["category"] if item else "none"
        return {
            "customer": {
                "customer_id": customer_id,
                "name": self.customers[customer_id]["name"],
                "city": self.customers[customer_id]["city"],
                "segment": self.customers[customer_id]["segment"],
                "cohort_month": self.cohort_by_customer.get(customer_id),
            },
            "month": month,
            "category": category,
            "category_label": config.CATEGORY_LABELS.get(category, "无桥接变动"),
            "reason": item["reason"] if item else "本月客户层 MRR 未发生桥接类别变动",
            "mrr_before_rmb": f2(snap_before["mrr_rmb"]),
            "mrr_after_rmb": f2(snap_after["mrr_rmb"]),
            "delta_rmb": f2(q4(snap_after["mrr_rmb"] - snap_before["mrr_rmb"])),
            "snapshot_before": self._snapshot_payload(snap_before),
            "snapshot_after": self._snapshot_payload(snap_after),
            "contracts": contract_rows,
            "events": detail_events,
            "trend": trend,
            "pending_changes": pending_changes,
            "refunds": refunds,
            "period": bridge["period"],
        }

    # ----------------------------------------------------------------- meta
    def meta(self) -> dict:
        return {
            "title": "订阅收入 MRR 变动与首付月份留存",
            "currency": config.CURRENCY,
            "currency_symbol": config.CURRENCY_SYMBOL,
            "as_of": self.as_of.isoformat(),
            "months": self.months,
            "last_completed_month": self.last_completed_month,
            "current_incomplete_month": config.CURRENT_INCOMPLETE_MONTH,
            "categories": [
                {"key": key, "label": label} for key, label in config.CATEGORY_ORDER
            ],
            "primary_categories": list(config.PRIMARY_CATEGORIES),
            "scenarios": SCENARIOS,
            "definitions": {
                "mrr": "仅计入已生效的付费合同；月付按周期金额，年付按金额 ÷ 12；统一人民币。",
                "trial": "试用期不计 MRR；试用转付费时按首次付费月份计入新增。",
                "cancellation": "预约取消在到期后的生效日才减少 MRR；到期前显示为待取消。",
                "pause": "暂停/恢复按 effective_date 生效；暂停期间 MRR 为 0。",
                "customer_layer": "先把同一客户的多份合同加总到客户层，再判断新增/升级/降级/流失/回流。",
                "bridge": "比较上月末与本月末的客户层 MRR：零转正且此前从未付费=新增，曾付费=回流；正转零=流失；持续为正按差额=升级/降级。",
                "offset": "月内先发生后抵消、月末回到原点的变动不进入桥接，单独列入事件流水。",
                "rounding": "计算使用 4 位小数；展示按分四舍五入，分项加总与期初期末的显示尾差单独列示。",
                "retention": "按首付月份分组，统计各月末仍为正 MRR 的客户比例；未来月份留空。",
                "refund": "退款仅计入现金指标，不修改合同 MRR。",
            },
        }
