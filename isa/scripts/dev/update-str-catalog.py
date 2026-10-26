"""Atualiza a cópia local do CSV de participantes do STR.

Uma falha de download ou um arquivo vazio não substitui a última cópia válida.
A data de obtenção fica no catálogo; o CSV do Banco Central não traz data oficial própria.
"""

import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "server" / "catalog" / "ParticipantesSTR.csv"
URL = "https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv"
HEADER = "ISPB,Nome_Reduzido,Número_Código,Participa_da_Compe,Acesso_Principal,Nome_Extenso,Início_da_Operação"


def main():
    temp = DEST.with_suffix(".csv.part")
    request = urllib.request.Request(URL, headers={"User-Agent": "ISA-catalog/0.6.8"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
    except Exception as exc:
        print("A cópia atual permanece. Falha ao obter o CSV:", exc)
        return 1
    text = body.decode("utf-8-sig", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("ISPB,") or HEADER not in lines[0]:
        print("A cópia atual permanece. O arquivo recebido não tem o cabeçalho esperado.")
        return 1
    if len(lines) < 400:
        print("A cópia atual permanece. O arquivo recebido tem poucas linhas:", len(lines) - 1)
        return 1
    DEST.parent.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(body)
    shutil.move(str(temp), str(DEST))
    print("Catálogo gravado:", DEST)
    print("Linhas de dados:", len(lines) - 1)
    print("Fonte:", URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
