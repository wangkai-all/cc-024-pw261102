"""DuckDB persistence layer.

The database is the source of truth: reference rows plus an append-only
contract event stream.  ``MrrEngine`` materialises month-end snapshots from
that stream at startup so every API response can be traced back to events.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

from .seed_data import CONTRACT_EVENTS, CONTRACTS, CUSTOMERS

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "mrr.duckdb"


def get_db_path() -> Path:
    override = os.getenv("MRR_DB_PATH")
    if override:
        return Path(override)
    return DEFAULT_DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    city VARCHAR,
    segment VARCHAR,
    created_at DATE
);

CREATE TABLE IF NOT EXISTS contracts (
    contract_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR NOT NULL,
    plan_name VARCHAR NOT NULL,
    billing_cycle VARCHAR NOT NULL,
    amount_rmb DECIMAL(18, 4) NOT NULL,
    currency VARCHAR NOT NULL DEFAULT 'CNY',
    signed_date DATE
);

CREATE TABLE IF NOT EXISTS contract_events (
    event_id VARCHAR PRIMARY KEY,
    event_order INTEGER NOT NULL,
    contract_id VARCHAR NOT NULL,
    customer_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    event_date DATE NOT NULL,
    effective_date DATE NOT NULL,
    amount_rmb DECIMAL(18, 4),
    billing_cycle VARCHAR,
    note VARCHAR
);
"""


def connect(db_path: Path | str | None = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = str(db_path) if db_path is not None else str(get_db_path())
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(path, read_only=read_only)


def create_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(SCHEMA_SQL)


def seed_database(conn: duckdb.DuckDBPyConnection) -> None:
    """Insert the deterministic demo rows once."""
    if conn.execute("SELECT count(*) FROM customers").fetchone()[0]:
        return

    conn.executemany(
        """
        INSERT INTO customers (customer_id, name, city, segment, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (c["customer_id"], c["name"], c["city"], c["segment"], c["created_at"])
            for c in CUSTOMERS
        ],
    )
    conn.executemany(
        """
        INSERT INTO contracts
            (contract_id, customer_id, plan_name, billing_cycle, amount_rmb, currency, signed_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                c["contract_id"],
                c["customer_id"],
                c["plan_name"],
                c["billing_cycle"],
                c["amount_rmb"],
                c["currency"],
                c["signed_date"],
            )
            for c in CONTRACTS
        ],
    )
    conn.executemany(
        """
        INSERT INTO contract_events
            (event_id, event_order, contract_id, customer_id, event_type,
             event_date, effective_date, amount_rmb, billing_cycle, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                e["event_id"],
                idx,
                e["contract_id"],
                e["customer_id"],
                e["event_type"],
                e["event_date"],
                e["effective_date"],
                e["amount_rmb"],
                e["billing_cycle"],
                e["note"],
            )
            for idx, e in enumerate(CONTRACT_EVENTS, start=1)
        ],
    )


def initialize(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    conn = connect(db_path)
    create_schema(conn)
    seed_database(conn)
    return conn
