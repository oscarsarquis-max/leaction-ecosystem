from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "app" / "seed"


def test_seed_package_has_no_external_or_secret_hooks() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in SEED.glob("*.py"))
    assert "boto3" not in text
    assert "bedrock" not in text.lower() or "FakeModelGateway" in text
    assert "actionhub.com.br" not in text
    assert "password123" not in text
    assert "CREATE PASSWORD" not in text.upper()
    assert "mysql" not in text or "mysql proibido" in text
