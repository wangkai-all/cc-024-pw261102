"""Engine-level regression tests for the MRR event reconstruction."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.db import initialize
from app.engine import MrrEngine, month_end
from datetime import date


@pytest.fixture(scope="module")
def engine() -> MrrEngine:
    conn = initialize(":memory:")
    eng = MrrEngine(conn)
    yield eng
    conn.close()


def item_for(engine: MrrEngine, month: str, customer_id: str):
    bridge = engine.bridge(month)
    for component in bridge["components"]:
        for item in component["items"]:
            if item["customer_id"] == customer_id:
                return component, item
    return None, None


def test_all_months_reconcile_exactly(engine: MrrEngine):
    for month in engine.months:
        bridge = engine.bridge(month)
        reconciliation = bridge["reconciliation"]
        assert reconciliation["difference_rmb"] == 0.0, month
        displayed = (
            reconciliation["displayed_beginning_mrr_rmb"]
            + reconciliation["displayed_components_sum_rmb"]
            + reconciliation["rounding_adjustment_rmb"]
        )
        assert round(displayed, 2) == reconciliation["displayed_ending_mrr_rmb"], month


def test_monthly_and_annual_mrr(engine: MrrEngine):
    assert engine.month_customer_mrr["2025-02"]["C002"] == Decimal("8333.3333")
    assert engine.month_customer_mrr["2025-01"]["C001"] == Decimal("12800.0000")
    assert engine.month_customer_mrr["2026-03"]["C001"] == Decimal("18000.0000")


def test_trial_is_ignored_until_paid(engine: MrrEngine):
    assert engine.month_customer_mrr["2025-01"]["C005"] == Decimal("0")
    assert engine.month_customer_mrr["2025-02"]["C005"] == Decimal("5000")
    component, item = item_for(engine, "2025-02", "C005")
    assert component["key"] == "new"
    assert engine.cohort_by_customer["C005"] == "2025-02"


def test_rounding_tail_is_surfaced(engine: MrrEngine):
    bridge = engine.bridge("2026-02")
    assert bridge["reconciliation"]["difference_rmb"] == 0.0
    assert bridge["reconciliation"]["rounding_adjustment_rmb"] == 0.01
    assert any(step["key"] == "rounding" for step in bridge["waterfall"])
    assert "尾差" in bridge["reconciliation"]["note"]


def test_multi_contract_upgrade_is_not_churn(engine: MrrEngine):
    component, item = item_for(engine, "2026-04", "C004")
    assert component["key"] == "upgrade"
    assert item["mrr_before_rmb"] == 10000.0
    assert item["mrr_after_rmb"] == 16000.0
    assert item["delta_rmb"] == 6000.0
    assert len(item["events"]) == 2
    assert {event["event_type"] for event in item["events"]} == {"contract_end", "paid_start"}
    # The old contract ended, but the customer remained positive.
    assert engine.month_customer_mrr["2026-04"]["C004"] == Decimal("16000")
    assert item_for(engine, "2026-04", "C004")[0]["key"] != "churn"


def test_scheduled_cancellation_only_drops_after_expiry(engine: MrrEngine):
    june = engine.month_customer_snapshot["2026-06"]["C003"]["contracts"][0]
    assert june.status == "scheduled_cancel"
    assert june.mrr_rmb == Decimal("8000")
    assert june.scheduled_effective_date == date(2026, 7, 1)
    assert item_for(engine, "2026-06", "C003") == (None, None)
    june_bridge = engine.bridge("2026-06")
    assert any(
        change["customer_id"] == "C003" and change["mrr_rmb"] == 8000.0
        for change in june_bridge["pending_changes"]
    )
    component, item = item_for(engine, "2026-07", "C003")
    assert component["key"] == "churn"
    assert item["delta_rmb"] == -8000.0
    assert item["events"][0]["effective_date"] == "2026-07-01"


def test_same_month_changes_and_offset_ledger(engine: MrrEngine):
    component, item = item_for(engine, "2025-10", "C008")
    assert component["key"] == "upgrade"
    assert item["delta_rmb"] == 500.0
    assert [event["delta_rmb"] for event in item["events"]] == [2500.0, -2000.0]

    assert item_for(engine, "2025-11", "C008") == (None, None)
    bridge = engine.bridge("2025-11")
    offsets = [group for group in bridge["offset_ledger"] if group["customer_id"] == "C008"]
    assert len(offsets) == 1
    assert offsets[0]["offset_rmb"] == 3000.0
    assert offsets[0]["net_delta_rmb"] == 0.0
    assert [event["delta_rmb"] for event in offsets[0]["events"]] == [3000.0, -3000.0]
    assert all(not event["in_bridge"] for event in offsets[0]["events"])


def test_pause_and_resume(engine: MrrEngine):
    assert engine.month_customer_mrr["2025-06"]["C007"] == Decimal("5500")
    assert engine.month_customer_mrr["2025-07"]["C007"] == Decimal("0")
    assert engine.month_customer_mrr["2025-08"]["C007"] == Decimal("0")
    assert engine.month_customer_mrr["2025-09"]["C007"] == Decimal("5500")
    component, item = item_for(engine, "2025-07", "C007")
    assert component["key"] == "pause"
    assert item["delta_rmb"] == -5500.0
    # Once already zero, a continuing pause produces no new bridge movement.
    assert item_for(engine, "2025-08", "C007") == (None, None)
    component, item = item_for(engine, "2025-09", "C007")
    assert component["key"] == "resume"
    assert item["delta_rmb"] == 5500.0


def test_refund_is_cash_only(engine: MrrEngine):
    bridge = engine.bridge("2025-12")
    assert bridge["refund_total_rmb"] == 2000.0
    assert len(bridge["refunds"]) == 1
    assert engine.month_customer_mrr["2025-12"]["C018"] == Decimal("8000")
    assert engine.month_customer_mrr["2026-01"]["C018"] == Decimal("8000")


def test_retention_cohorts_and_future_blanks(engine: MrrEngine):
    report = engine.retention_report()
    assert report["future_months"] == ["2026-11"]
    c001 = next(cohort for cohort in report["cohorts"] if cohort["cohort"] == "2025-01")
    assert c001["cohort_size"] == 3
    oct_cell = next(cell for cell in c001["cells"] if cell["month"] == "2026-10")
    assert oct_cell["status"] == "ok"
    assert oct_cell["active_count"] == 2
    assert oct_cell["rate_pct"] == pytest.approx(66.67)
    nov_cell = next(cell for cell in c001["cells"] if cell["month"] == "2026-11")
    assert nov_cell["status"] == "future"
    assert nov_cell["rate"] is None
    feb_cohort = next(cohort for cohort in report["cohorts"] if cohort["cohort"] == "2025-02")
    jan_cell = next(cell for cell in feb_cohort["cells"] if cell["month"] == "2025-01")
    assert jan_cell["status"] == "before"
    assert jan_cell["rate"] is None


def test_customer_detail_contains_snapshots_and_events(engine: MrrEngine):
    detail = engine.customer_detail("C004", "2026-04")
    assert detail["mrr_before_rmb"] == 10000.0
    assert detail["mrr_after_rmb"] == 16000.0
    assert detail["category"] == "upgrade"
    assert [contract["contract_id"] for contract in detail["contracts"]] == [
        "CT004A",
        "CT004B",
        "CT004C",
    ]
    assert detail["snapshot_before"]["mrr_rmb"] == 10000.0
    assert detail["snapshot_after"]["mrr_rmb"] == 16000.0
    assert [event["event_type"] for event in detail["events"]] == ["contract_end", "paid_start"]
    assert detail["trend"][-1] == {"month": "2026-04", "mrr_rmb": 16000.0}


def test_customer_detail_shows_pending_cancellation(engine: MrrEngine):
    detail = engine.customer_detail("C003", "2026-06")
    assert detail["category"] == "none"
    assert detail["mrr_before_rmb"] == 8000.0
    assert detail["mrr_after_rmb"] == 8000.0
    assert len(detail["pending_changes"]) == 1
    assert detail["pending_changes"][0]["effective_date"] == "2026-07-01"


def test_api_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("MRR_DB_PATH", str(tmp_path / "api.duckdb"))
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        meta = client.get("/api/meta").json()
        assert meta["last_completed_month"] == "2026-10"
        bridge = client.get("/api/mrr/bridge", params={"month": "2026-02"}).json()
        assert bridge["reconciliation"]["rounding_adjustment_rmb"] == 0.01
        retention = client.get("/api/retention").json()
        assert retention["future_months"] == ["2026-11"]
        cell = client.get(
            "/api/retention/cell",
            params={"cohort": "2025-01", "month": "2026-10"},
        ).json()
        assert cell["cohort_size"] == 3
        assert cell["active_count"] == 2
        assert cell["rate_pct"] == pytest.approx(66.67)
        assert [customer["customer_id"] for customer in cell["active_customers"]] == [
            "C001",
            "C007",
        ]
        assert (
            client.get(
                "/api/retention/cell",
                params={"cohort": "2025-02", "month": "2025-01"},
            ).status_code
            == 400
        )
        detail = client.get("/api/customers/C004/detail", params={"month": "2026-04"}).json()
        assert detail["category"] == "upgrade"
        assert client.get("/api/mrr/bridge", params={"month": "2024-01"}).status_code == 400
        assert client.get("/api/customers/UNKNOWN/detail").status_code == 404
        assert client.get("/api/health").json()["status"] == "ok"
