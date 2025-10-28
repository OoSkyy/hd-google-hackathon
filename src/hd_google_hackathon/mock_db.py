"""Lightweight SQLite-backed mock database helpers for the hackathon.

This module intentionally uses the Python standard library (sqlite3) so no
extra deps are required. It provides a small schema and simple helpers to
connect, initialize and query the mock DB.
"""
from __future__ import annotations

import sqlite3
from typing import List, Dict, Any
from pathlib import Path

from .config import get_database_path


def connect_db(read_only: bool = False) -> sqlite3.Connection:
    """Return a SQLite connection to the mock database.

    By default this connects in default mode. When read_only=True, it will
    open the DB in a read-only mode which is useful for concurrency safety.
    """
    db_path = get_database_path()
    # Ensure parent exists. If the requested parent is not writable (for
    # example on local dev where /data is root-owned), fall back to a
    # repository-local ./data directory so the developer can run the seed
    # script without root privileges.
    parent = Path(db_path).parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        fallback = Path.cwd() / "data" / Path(db_path).name
        fallback.parent.mkdir(parents=True, exist_ok=True)
        db_path = str(fallback)
    if read_only:
        uri = f"file:{db_path}?mode=ro"
        return sqlite3.connect(uri, uri=True, check_same_thread=False)
    return sqlite3.connect(db_path, check_same_thread=False)


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            sku TEXT,
            name TEXT,
            price_cents INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dealers (
            id TEXT PRIMARY KEY,
            name TEXT,
            region TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            dealer_id TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            product_id TEXT,
            quantity INTEGER
        )
        """
    )
    conn.commit()


def get_products(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT id, sku, name, price_cents FROM products")
    rows = cur.fetchall()
    return [dict(id=r[0], sku=r[1], name=r[2], price_cents=r[3]) for r in rows]

def get_orders_for_dealer(conn: sqlite3.Connection, dealer_id: str):
    cur = conn.cursor()
    cur.execute("SELECT id, status, created_at FROM orders WHERE dealer_id = ?", (dealer_id,))
    return [dict(id=r[0], status=r[1], created_at=r[2]) for r in cur.fetchall()]


__all__ = [
    "connect_db",
    "initialize_schema",
    "get_products",
    "get_orders_for_dealer",
]
