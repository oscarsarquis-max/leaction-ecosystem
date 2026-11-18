#!/usr/bin/env python3
"""Envia um arquivo ao S3 (PutObject, assinatura SigV4) usando só a biblioteca padrão.

O host não tem AWS CLI e não instalamos nada nele. Uso:

    AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=us-east-2 \
      s3_put.py <arquivo> <bucket> <chave>

A credencial vem só do ambiente; nada dela é impresso. Falha com código diferente de zero se o S3 não
responder 200.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote


def _hmac(chave: bytes, texto: str) -> bytes:
    return hmac.new(chave, texto.encode("utf-8"), hashlib.sha256).digest()


def enviar(arquivo: str, bucket: str, chave: str) -> None:
    acesso = os.environ["AWS_ACCESS_KEY_ID"]
    segredo = os.environ["AWS_SECRET_ACCESS_KEY"]
    token = os.environ.get("AWS_SESSION_TOKEN", "")
    regiao = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
    host = f"{bucket}.s3.{regiao}.amazonaws.com"
    caminho = "/" + quote(chave, safe="/-_.~")

    sha = hashlib.sha256()
    with open(arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(bloco)
    carga = sha.hexdigest()
    tamanho = os.path.getsize(arquivo)

    agora = datetime.now(timezone.utc)
    amz_data = agora.strftime("%Y%m%dT%H%M%SZ")
    dia = agora.strftime("%Y%m%d")

    cabecalhos = {
        "host": host,
        "x-amz-content-sha256": carga,
        "x-amz-date": amz_data,
        "x-amz-server-side-encryption": "AES256",
    }
    if token:
        cabecalhos["x-amz-security-token"] = token
    nomes = sorted(cabecalhos)
    canonicos = "".join(f"{n}:{cabecalhos[n]}\n" for n in nomes)
    assinados = ";".join(nomes)
    requisicao = "\n".join(["PUT", caminho, "", canonicos, assinados, carga])

    escopo = f"{dia}/{regiao}/s3/aws4_request"
    para_assinar = "\n".join(
        ["AWS4-HMAC-SHA256", amz_data, escopo, hashlib.sha256(requisicao.encode()).hexdigest()]
    )
    k = _hmac(("AWS4" + segredo).encode(), dia)
    k = _hmac(k, regiao)
    k = _hmac(k, "s3")
    k = _hmac(k, "aws4_request")
    assinatura = hmac.new(k, para_assinar.encode(), hashlib.sha256).hexdigest()

    enviados = dict(cabecalhos)
    enviados.pop("host")
    enviados["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={acesso}/{escopo}, SignedHeaders={assinados}, Signature={assinatura}"
    )
    enviados["Content-Length"] = str(tamanho)
    enviados["Content-Type"] = "application/octet-stream"

    conexao = http.client.HTTPSConnection(host, timeout=120)
    try:
        with open(arquivo, "rb") as f:
            conexao.request("PUT", caminho, body=f, headers=enviados)
            resposta = conexao.getresponse()
            corpo = resposta.read()
    finally:
        conexao.close()
    if resposta.status != 200:
        sys.stderr.write(f"ERRO: o S3 respondeu {resposta.status}: {corpo[:300].decode('utf-8', 'replace')}\n")
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 4:
        sys.stderr.write("uso: s3_put.py <arquivo> <bucket> <chave>\n")
        raise SystemExit(2)
    enviar(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
