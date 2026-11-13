"""Isolamento do marketplace: a Loja não importa o módulo, e o módulo não lê a Loja."""

import ast
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
MARKET = APP / "marketplace"
DATABASE = BACKEND.parent / "database"
MIGRATION = DATABASE / "migrations" / "versions" / "b7c4e2a91f30_m1_marketplace_schema.py"

ALLOWED = {
    (APP / "api" / "v1" / "__init__.py").resolve(),
    (DATABASE / "migrations" / "env.py").resolve(),
}

ALLOWED_DOMAIN = frozenset({"app.domain.media", "app.domain.errors"})

BANNED_PREFIXES = (
    "app.models.orders",
    "app.models.payments",
    "app.models.schedule",
    "app.models.email_outbox",
)


def _modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def _banned(module: str) -> bool:
    if module == "app.domain" or module.startswith("app.domain."):
        return module not in ALLOWED_DOMAIN
    return any(module == prefix or module.startswith(prefix + ".") for prefix in BANNED_PREFIXES)


def test_fora_do_modulo_so_importa_nos_dois_pontos_autorizados():
    leaks: list[str] = []
    roots = [APP, DATABASE]
    for root in roots:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts or path.resolve() in ALLOWED:
                continue
            if MARKET in path.parents or path == MARKET:
                continue
            if any(name == "app.marketplace" or name.startswith("app.marketplace.") for name in _modules(path)):
                leaks.append(str(path.relative_to(BACKEND.parent)))
    assert leaks == []


def test_modulo_nao_importa_dominio_pedido_pagamento_agenda_nem_aviso():
    for path in MARKET.rglob("*.py"):
        if path.name == "house_catalog.py":
            continue
        banned = [name for name in _modules(path) if _banned(name)]
        assert banned == [], f"{path.name}: {banned}"


def test_house_catalog_so_le_produto_publicado():
    text = (MARKET / "house_catalog.py").read_text(encoding="utf-8")
    assert "FROM products" in text
    upper = text.upper()
    for verb in ("INSERT", "UPDATE", "DELETE"):
        assert verb not in upper
    banned = [name for name in _modules(MARKET / "house_catalog.py") if name.startswith("app.")]
    assert banned == []
    for path in MARKET.rglob("*.py"):
        if path.name == "house_catalog.py":
            continue
        assert "FROM products" not in path.read_text(encoding="utf-8")


def test_migracao_so_cria_o_schema_marketplace():
    source = MIGRATION.read_text(encoding="utf-8")
    upgrade = source.split("def downgrade", 1)[0]
    for forbidden in ("op.add_column", "op.alter_column", "op.drop_column", "op.drop_table", "op.rename"):
        assert forbidden not in upgrade
    assert "ALTER TABLE" not in upgrade.upper()
    targets = re.findall(r'ForeignKey\(\s*"([^"]+)"', upgrade)
    assert targets, "a migração precisa declarar as chaves internas"
    assert all(target.startswith("marketplace.") for target in targets)
    assert upgrade.count("op.create_table(") >= 6
    assert 'schema=_SCHEMA' in upgrade or 'schema="marketplace"' in upgrade
