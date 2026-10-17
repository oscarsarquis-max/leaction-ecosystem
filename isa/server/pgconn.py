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
    def __init__(self, raw):
        self.raw = raw
        self.isa_pg = True

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
            return self.raw.execute(statement, params)
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
        self.raw.close()


def connect(url):
    raw = psycopg.connect(url, autocommit=True, row_factory=dict_row)
    return PgConn(raw)
