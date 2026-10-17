"""Cópia manual da base. Não é uma rota do navegador e não está agendada.

Com PostgreSQL, que é a base do piloto:

    $env:ISA_DATABASE_URL = "postgresql://..."
    $env:ISA_BACKUP_ROOT = "C:\Projetos\isa\data\backups"
    python C:\Projetos\isa\scripts\ops\backup-isa.py nome-da-copia

A cópia lógica não inclui o livro de exclusões. O livro fica em ISA_ERASURE_LEDGER,
fora do banco, e a restauração o reaplica antes de devolver consulta.

Esta execução é manual. Não cria bucket, não liga agenda e não protege sozinha
contra a perda do equipamento.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import store


def main():
    root = os.environ.get("ISA_BACKUP_ROOT")
    if not root:
        raise SystemExit("Defina ISA_BACKUP_ROOT fora do código.")
    name = os.path.basename(sys.argv[1] if len(sys.argv) > 1 else "manual")
    dest = os.path.join(root, name)
    url = os.environ.get("ISA_DATABASE_URL") or ""
    if url.startswith("postgres"):
        conn = store.connect(url)
        try:
            manifest = store.logical_dump(conn, dest)
        finally:
            conn.close()
        print(manifest["createdAt"], manifest["engine"])
        print("Cópia manual. Sem agenda e sem destino externo.")
        return
    data = os.environ.get("ISA_DATA")
    if not data:
        raise SystemExit("O laboratório SQLite exige ISA_DATA. A produção exige ISA_DATABASE_URL.")
    manifest = store.backup_dir(data, dest)
    print(manifest["createdAt"], manifest["retention"])
    print("Cópia no disco local. Não é proteção contra perda do equipamento.")


if __name__ == "__main__":
    main()
