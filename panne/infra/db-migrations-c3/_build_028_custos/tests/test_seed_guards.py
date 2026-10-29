from app.seed.target import SeedTargetError, assert_seed_target, describe_target
import pytest


def test_refuses_logical_panne() -> None:
    with pytest.raises(SeedTargetError, match="panne"):
        assert_seed_target("postgresql+psycopg://admin:x@127.0.0.1:5434/panne", "local")


def test_refuses_production() -> None:
    with pytest.raises(SeedTargetError, match="production"):
        assert_seed_target("postgresql+psycopg://admin:x@127.0.0.1:5434/panne_demo", "production")


def test_refuses_invalid_suffix_and_host() -> None:
    with pytest.raises(SeedTargetError, match="sufixo"):
        assert_seed_target("postgresql+psycopg://admin:x@127.0.0.1:5434/leaction_hub", "local")
    with pytest.raises(SeedTargetError, match="host"):
        assert_seed_target("postgresql+psycopg://admin:x@192.168.0.10:5434/panne_demo", "local")


def test_accepts_demo_and_smoke() -> None:
    assert assert_seed_target("postgresql+psycopg://admin:x@127.0.0.1:5434/panne_demo", "demo") == "panne_demo"
    assert assert_seed_target("postgresql+psycopg://admin:x@localhost:5434/panne_smoke", "test") == "panne_smoke"
    target = describe_target("postgresql+psycopg://admin:x@127.0.0.1:5434/panne_demo", "local")
    assert target["database"] == "panne_demo"


def test_alembic_head_constant() -> None:
    from app.seed import ALEMBIC_HEAD

    assert ALEMBIC_HEAD == "0022_fiscal_inbound"
