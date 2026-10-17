"""Cópia manual da base. Não é uma rota do navegador.

Uso, com os caminhos já exportados:

    python scripts/ops/backup-isa.py nome-da-copia

ISA_DATA é a pasta ativa. ISA_BACKUP_ROOT é outra pasta. A função recusa
quando o destino está dentro da origem. Esta cópia, sozinha, não protege
contra a perda do disco.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server"))

import store


def main():
    data = os.environ.get("ISA_DATA")
    root = os.environ.get("ISA_BACKUP_ROOT")
    if not data or not root:
        raise SystemExit("Defina ISA_DATA e ISA_BACKUP_ROOT fora do código.")
    name = os.path.basename(sys.argv[1] if len(sys.argv) > 1 else "manual")
    manifest = store.backup_dir(data, os.path.join(root, name))
    print(manifest["createdAt"], manifest["retention"])


if __name__ == "__main__":
    main()
