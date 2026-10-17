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
    url = os.environ.get("ISA_DATABASE_URL") or ""
    if not url.startswith("postgres"):
        raise SystemExit("Produção exige ISA_DATABASE_URL de PostgreSQL. Um arquivo local não é a base do piloto.")
    issuer = os.environ.get("ISA_OIDC_ISSUER") or ""
    local_issuer = issuer.startswith("http://127.") or issuer.startswith("http://localhost")
    host = os.environ.get("ISA_BIND_ADDRESS", "127.0.0.1")
    published = host not in ("127.0.0.1", "localhost", "::1")
    if published and (os.environ.get("ISA_OIDC_REHEARSAL") == "1" or local_issuer):
        raise SystemExit("A publicação recusa o provedor de ensaio.")
    if local_issuer and os.environ.get("ISA_OIDC_REHEARSAL") != "1":
        raise SystemExit("Produção recusa emissor local. O ensaio precisa de ISA_OIDC_REHEARSAL=1 e não é o Cognito.")
    origin = os.environ.get("ISA_ORIGIN") or ""
    if published and not origin.startswith("https://"):
        raise SystemExit("A publicação exige ISA_ORIGIN em HTTPS.")
    if published and not os.environ.get("ISA_BACKUP_BUCKET"):
        raise SystemExit("A publicação exige o livro de exclusões no destino externo.")
    data = os.environ.get("ISA_DATA") or os.path.join(ROOT, "data", "prod-empty")
    if not os.path.isabs(data):
        data = os.path.abspath(data)
    if os.path.abspath(data).startswith(os.path.abspath(os.path.join(ROOT, "prototype"))):
        raise SystemExit("Arquivos auxiliares não podem ficar dentro dos arquivos públicos.")
    port = int(os.environ.get("ISA_PORT") or ("8091" if published else "8099"))
    app = wsgi_app.build_app(data, time.time)
    label = "ensaio local, não é Cognito" if os.environ.get("ISA_OIDC_REHEARSAL") == "1" else "diretório externo"
    print("ISA produção em http://%s:%s (%s)" % (host, port, label), flush=True)
    serve(
        app,
        host=host,
        port=port,
        threads=4,
        connection_limit=16,
        channel_timeout=30,
        cleanup_interval=30,
        max_request_body_size=1_000_000,
    )


if __name__ == "__main__":
    main()
