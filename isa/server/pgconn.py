"""Conexão PostgreSQL com o mesmo texto SQL do laboratório SQLite."""

import sqlite3

import psycopg
from psycopg.rows import dict_row


def translate(sql):
    text = " ".join(sql.split())
    upper = text.upper()
    if upper == "BEGIN IMMEDIATE":
        return "BEGIN"
    return sql.replace("?", "%s")


class PgConn:
    def __init__(self, raw, pool=None):
        self.raw = raw
        self._pool = pool
        self.isa_pg = True
        self.broken = False
        self.queries = 0

    def _quiet_rollback(self):
        try:
            self.raw.rollback()
        except Exception:
            pass
        self.raw.autocommit = True

    def execute(self, sql, params=()):
        statement = translate(sql)
        command = " ".join(statement.split()).upper()
        if command == "BEGIN" or command.startswith("BEGIN "):
            if self.raw.autocommit:
                self.raw.autocommit = False
            if command != "BEGIN":
                self.raw.execute(statement)
            return self.raw.cursor()
        if command == "COMMIT":
            if not self.raw.autocommit:
                self.raw.commit()
            self.raw.autocommit = True
            return self.raw.cursor()
        if command == "ROLLBACK":
            self._quiet_rollback()
            return self.raw.cursor()
        try:
            cursor = self.raw.execute(statement, params)
            self.queries += 1
            return cursor
        except (psycopg.OperationalError, psycopg.InterfaceError):
            self.broken = True
            raise
        except psycopg.errors.UniqueViolation as exc:
            self._quiet_rollback()
            raise sqlite3.IntegrityError(str(exc)) from exc

    def executescript(self, script):
        for part in script.split(";"):
            statement = part.strip()
            if statement:
                self.raw.execute(statement)
        self.raw.commit()

    def close(self):
        raw = self.raw
        pool = self._pool
        self.raw = None
        self._pool = None
        if raw is None:
            return
        discard = self.broken or bool(getattr(raw, "closed", False))
        if not discard:
            try:
                if not raw.autocommit:
                    raw.rollback()
                raw.autocommit = True
            except Exception:
                discard = True
        if discard:
            try:
                if not getattr(raw, "closed", False):
                    raw.close()
            except Exception:
                pass
        if pool is None:
            if not getattr(raw, "closed", True):
                raw.close()
            return
        pool.putconn(raw)


_pool = None
_pool_url = ""
_timeout = 5.0


def is_db_failure(exc):
    return type(exc).__name__ in ("OperationalError", "InterfaceError", "PoolTimeout")


def enable_pool(url, min_size=1, max_size=6, timeout=5):
    """Um pool por processo. max_size cabe nas 4 threads, no worker e numa folga."""
    global _pool, _pool_url, _timeout
    from psycopg_pool import ConnectionPool
    if _pool is not None:
        if _pool_url == url and _pool.max_size == max_size:
            return _pool
        close_pool()
    _timeout = float(timeout)
    _pool_url = url
    _pool = ConnectionPool(
        url,
        min_size=min_size,
        max_size=max_size,
        timeout=_timeout,
        kwargs={"autocommit": True, "row_factory": dict_row, "connect_timeout": 5},
        open=True,
        name="isa",
    )
    try:
        _pool.wait(timeout=10)
    except Exception:
        close_pool()
        raise
    return _pool


def close_pool():
    global _pool, _pool_url
    pool = _pool
    _pool = None
    _pool_url = ""
    if pool is not None:
        pool.close()


def connect(url):
    if _pool is not None and _pool_url == url:
        from psycopg_pool import PoolTimeout
        try:
            raw = _pool.getconn(timeout=_timeout)
        except PoolTimeout:
            raise
        return PgConn(raw, pool=_pool)
    raw = psycopg.connect(url, autocommit=True, row_factory=dict_row, connect_timeout=5)
    return PgConn(raw)
