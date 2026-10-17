"""Restaura uma cópia lógica num banco vazio e reaplica o livro de exclusões.

ISA_RESTORE_URL precisa ser outro database, não o database ativo.
ISA_ERASURE_LEDGER precisa ser o mesmo livro de quando a exclusão foi registrada.
Não há agenda. O destino externo não está implantado.

    $env:ISA_RESTORE_URL = "postgresql://.../isa_restore"
    $env:ISA_ERASURE_LEDGER = "C:\caminho\erasure-ledger.jsonl"
    python C:\Projetos\isa\scripts\ops\restore-isa.py C:\caminho\da-copia
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import store


def main():
    url = os.environ.get("ISA_RESTORE_URL") or ""
    active = os.environ.get("ISA_DATABASE_URL") or ""
    if not url.startswith("postgres"):
        raise SystemExit("A restauração do piloto exige ISA_RESTORE_URL de PostgreSQL.")
    if url == active:
        raise SystemExit("A restauração precisa de um database separado do ativo.")
    if len(sys.argv) < 2:
        raise SystemExit("Informe a pasta da cópia.")
    conn = store.connect(url)
    try:
        result = store.logical_restore(conn, sys.argv[1])
    finally:
        conn.close()
    print(result["restored"], result["erasuresReapplied"])
    print("Agenda e destino externo não estão implantados.")


if __name__ == "__main__":
    main()
