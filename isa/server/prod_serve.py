"""Sobe a ISA para produção, só em 127.0.0.1, atrás do proxy HTTPS.

Não usar com ISA_ENV=lab. O processo de laboratório continua sendo serve.py.
A documentação do Python pede para não publicar http.server:
https://docs.python.org/3/library/http.server.html
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve

import wsgi_app


def main():
    env = os.environ.get("ISA_ENV")
    if env == "lab":
        raise SystemExit("Produção recusa ISA_ENV=lab. Use scripts/dev/start-isa.ps1 para a demonstração.")
    if env != "production":
        raise SystemExit("Defina ISA_ENV=production. Este processo não é o servidor de laboratório.")
    data = os.environ.get("ISA_DATA")
    if not data or not os.path.isabs(data):
        raise SystemExit("ISA_DATA precisa ser um caminho absoluto e durável, fora do código.")
    if os.path.abspath(data).startswith(os.path.abspath(os.path.join(ROOT, "prototype"))):
        raise SystemExit("A base não pode ficar dentro dos arquivos públicos.")
    os.makedirs(data, exist_ok=True)
    port = int(os.environ.get("ISA_PORT") or "8099")
    app = wsgi_app.build_app(data, time.time)
    print("ISA produção em http://127.0.0.1:%s" % port, flush=True)
    serve(app, host="127.0.0.1", port=port, threads=4, channel_timeout=30, max_request_body_size=1_000_000)


if __name__ == "__main__":
    main()
