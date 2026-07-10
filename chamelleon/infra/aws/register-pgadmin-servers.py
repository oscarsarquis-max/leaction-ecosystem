"""Registra servidores Chamelleon e Diario de Obra no pgAdmin local."""
from __future__ import annotations

import binascii
import importlib.util
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import keyring

PGADMIN_WEB = Path(r"C:\Users\Oscar Sarquis\AppData\Local\Programs\pgAdmin 4\web")
PGADMIN_DB = Path.home() / "AppData/Roaming/pgAdmin/pgadmin4.db"
KEY_RING_SERVICE = "pgAdmin4"
KEY_RING_MASTER = "pgadmin4-master-password"

SERVERS = [
    {
        "name": "Chamelleon PROD (AWS)",
        "maintenance_db": "chamelleon",
        "comment": "Tunel manual: ssh -L 5435:127.0.0.1:5432 ubuntu@18.227.125.118",
    },
    {
        "name": "Diario de Obra PROD (AWS)",
        "maintenance_db": "diario-obra",
        "comment": "Mesmo tunel :5435 — usuario chamelleon",
    },
]

HOST = "127.0.0.1"
PORT = 5435
USERNAME = "chamelleon"
PASSWORD = "mYEJMIukXLRdnXpOm3RW132P"
CONNECTION_PARAMS = json.dumps({"sslmode": "prefer", "connect_timeout": 10})


def load_crypto():
    crypto_path = PGADMIN_WEB / "pgadmin/utils/crypto.py"
    spec = importlib.util.spec_from_file_location("pgcrypto", crypto_path)
    crypto = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crypto)
    return crypto


def encrypt_password_hex(plain: str) -> str:
    crypto = load_crypto()
    master_key = keyring.get_password(KEY_RING_SERVICE, KEY_RING_MASTER)
    if not master_key:
        raise SystemExit(
            "Master key do pgAdmin nao encontrada no keyring. "
            "Abra o pgAdmin uma vez e tente novamente."
        )
    encrypted = crypto.encrypt(plain, master_key)
    if isinstance(encrypted, bytes):
        return binascii.hexlify(encrypted).decode()
    return encrypted


def main() -> None:
    if not PGADMIN_DB.exists():
        raise SystemExit(f"pgadmin4.db nao encontrado: {PGADMIN_DB}")

    backup = PGADMIN_DB.with_suffix(f".bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(PGADMIN_DB, backup)
    print(f"Backup: {backup}")

    enc_pass = encrypt_password_hex(PASSWORD)

    con = sqlite3.connect(PGADMIN_DB)
    cur = con.cursor()
    cur.execute("SELECT id, user_id, servergroup_id FROM server WHERE id = 29")
    template = cur.fetchone()
    if not template:
        raise SystemExit("Servidor modelo RDS_OFICIAL_AWS (id=29) nao encontrado.")
    _, user_id, servergroup_id = template

    for spec in SERVERS:
        cur.execute("SELECT id FROM server WHERE name = ?", (spec["name"],))
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """
                UPDATE server SET
                  host = ?, port = ?, maintenance_db = ?, username = ?,
                  password = ?, save_password = 1, comment = ?,
                  use_ssh_tunnel = 0, connection_params = ?
                WHERE id = ?
                """,
                (
                    HOST,
                    PORT,
                    spec["maintenance_db"],
                    USERNAME,
                    enc_pass,
                    spec["comment"],
                    CONNECTION_PARAMS,
                    existing[0],
                ),
            )
            print(f"Atualizado: {spec['name']} (id={existing[0]})")
            continue

        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM server")
        new_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO server (
              id, user_id, servergroup_id, name, host, port, maintenance_db,
              username, comment, password, save_password, use_ssh_tunnel,
              tunnel_port, tunnel_authentication, connection_params, shared
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, '22', 0, ?, 0)
            """,
            (
                new_id,
                user_id,
                servergroup_id,
                spec["name"],
                HOST,
                PORT,
                spec["maintenance_db"],
                USERNAME,
                spec["comment"],
                enc_pass,
                CONNECTION_PARAMS,
            ),
        )
        print(f"Criado: {spec['name']} (id={new_id})")

    con.commit()
    con.close()
    print("Concluido. Feche e reabra o pgAdmin para ver os servidores.")


if __name__ == "__main__":
    main()
