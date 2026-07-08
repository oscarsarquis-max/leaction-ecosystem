"""Diagnóstico de acesso ao Claude via AWS Bedrock (mesmo fluxo do PanelDX)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICOS = ROOT / "servicos"
sys.path.insert(0, str(SERVICOS))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from ai.bedrock_client import BEDROCK_MODEL_ID, BEDROCK_REGION, testar_conexao


def main() -> int:
    print("--- Prodinx: diagnóstico Bedrock / Claude ---\n")
    print(f"Região:  {BEDROCK_REGION}")
    print(f"Modelo:  {BEDROCK_MODEL_ID}\n")

    try:
        resultado = testar_conexao()
        print("SUCESSO — Bedrock respondeu.")
        print(f"Resposta: {resultado['resposta']!r}")
        return 0
    except Exception as exc:
        print(f"FALHA: {exc}")
        print(
            "\nDica: defina AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env "
            "(mesmas credenciais usadas no PanelDX)."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
