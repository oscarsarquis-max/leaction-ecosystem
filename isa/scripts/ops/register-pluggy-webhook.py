"""Registra o webhook da ISA na Pluggy. Não imprime o segredo."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "server"))

import banksync
import pluggy


def main():
    if not pluggy.enabled():
        print("ISA bank webhook não registrado: segredo ausente.", flush=True)
        return 1
    url = banksync._webhook_url()
    secret = pluggy.load_credentials().get("webhookSecret") or ""
    if not secret:
        print("ISA bank webhook não registrado: cabeçalho ausente.", flush=True)
        return 1
    try:
        pluggy.client().register_webhook(url, banksync.HEADER, secret)
    except pluggy.PluggyError as exc:
        print("ISA bank webhook " + (exc.code or "erro"), flush=True)
        return 1
    print("ISA bank webhook registrado.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
