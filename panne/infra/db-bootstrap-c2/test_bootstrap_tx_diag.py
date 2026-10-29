"""Regression: B1 must not toggle autocommit on a used connection."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOOTSTRAP = ROOT / "bootstrap.py"


class BootstrapSourceOrderTests(unittest.TestCase):
    def test_ensure_database_does_not_assign_autocommit(self) -> None:
        tree = ast.parse(BOOTSTRAP.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "ensure_database":
                for n in ast.walk(node):
                    if isinstance(n, ast.Assign):
                        for t in n.targets:
                            if isinstance(t, ast.Attribute) and t.attr == "autocommit":
                                self.fail("ensure_database must not assign conn.autocommit")
                return
        self.fail("ensure_database not found")

    def test_connect_accepts_autocommit_kw(self) -> None:
        src = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("autocommit: bool = False", src)
        self.assertIn("autocommit=True", src)

    def test_no_put_secret_value_roundtrip(self) -> None:
        src = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("put_secret_value", src.lower())
        self.assertIn("tag_resource", src)


if __name__ == "__main__":
    unittest.main()
