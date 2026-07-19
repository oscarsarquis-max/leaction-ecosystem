#!/usr/bin/env python3
"""
Simulador eSIM — Base Mobile (operadora externa)
================================================
Simula um chip inteligente (eSIM) enviando alerta bruto de telemetria ao webhook
do PanelDX. Este script representa a operadora: envia APENAS dados técnicos de
telecomunicação. Não conhece o Framework LeAction.

Uso:
    python scripts/simulador_esim.py
    python scripts/simulador_esim.py --cliente-id 2
    python scripts/simulador_esim.py --codigo-evento GARGALO_ADMN_SEC
    python scripts/simulador_esim.py --listar-codigos
    BASEMOBILE_WEBHOOK_SECRET=meu-token python scripts/simulador_esim.py

Requisitos:
    pip install requests
    Backend Flask rodando em http://localhost:5002
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from typing import Any

import requests

DEFAULT_URL = "http://localhost:5002/api/webhooks/esim"
DEFAULT_TIMEOUT = 60
DEFAULT_CODIGO_EVENTO = "QDA_ACESSO_PEDAG"
DEFAULT_ICCID = "8944123456789012345"

# Códigos de alerta da operadora (contrato técnico).
# O PanelDX resolve internamente cada código → Framework LeAction (esim_eventos_catalog).
TELECOM_EVENT_CODES: dict[str, str] = {
    "QDA_ACESSO_PEDAG": "Queda de tráfego — perfil pedagógico",
    "GARGALO_ADMN_SEC": "Gargalo de autenticação — perfil administrativo",
    "LENTIDAO_TI_SIST": "Degradação de performance — perfil TI/infraestrutura",
}

# Cenários de telemetria bruta (sem referência a dimensões/blocos LeAction).
TELECOM_ALERT_SCENARIOS: dict[str, dict[str, Any]] = {
    "QDA_ACESSO_PEDAG": {
        "grupo_acesso": "Pedagógico",
        "dominio_acessado": "lms.escola.com.br",
        "titulo_alerta": "Queda crítica de tráfego eSIM no LMS",
        "descricao_evento": (
            "Queda de 40% no volume de dados eSIM no grupo Pedagógico ao acessar "
            "lms.escola.com.br nos últimos 7 dias. Aumento de timeouts HTTP, "
            "sessões encerradas abruptamente e falhas TLS intermitentes."
        ),
        "trafego_mb_7dias": 45,
        "status_anomalia": "queda_critica",
        "variacao_percentual": -40,
    },
    "GARGALO_ADMN_SEC": {
        "grupo_acesso": "Administrativo",
        "dominio_acessado": "sso.escola.com.br",
        "titulo_alerta": "Pico de falhas de autenticação SSO",
        "descricao_evento": (
            "Pico de falhas de login e bloqueios de sessão no domínio sso.escola.com.br "
            "para o grupo Administrativo. Latência elevada no handshake OAuth e "
            "aumento de códigos HTTP 401/403 nas últimas 24 horas."
        ),
        "trafego_mb_7dias": 18,
        "status_anomalia": "falha_auth",
        "variacao_percentual": -25,
    },
    "LENTIDAO_TI_SIST": {
        "grupo_acesso": "TI / Infraestrutura",
        "dominio_acessado": "erp.escola.com.br",
        "titulo_alerta": "Lentidão severa em sistemas corporativos",
        "descricao_evento": (
            "Degradação de performance (latência média +320%) no acesso ao erp.escola.com.br "
            "pelo grupo TI / Infraestrutura. Pacotes TCP retransmitidos e "
            "jitter elevado na rota de saída do chip."
        ),
        "trafego_mb_7dias": 120,
        "status_anomalia": "lentidao",
        "variacao_percentual": -15,
    },
}


def montar_payload(
    cliente_id: int | str,
    codigo_evento: str,
    *,
    iccid: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Monta payload bruto de telecom — sem metadados do Framework LeAction."""
    codigo = codigo_evento.strip().upper()
    if codigo not in TELECOM_EVENT_CODES:
        validos = ", ".join(sorted(TELECOM_EVENT_CODES))
        raise ValueError(f"Código de evento inválido '{codigo}'. Códigos da operadora: {validos}")

    cenario = TELECOM_ALERT_SCENARIOS.get(codigo)
    if not cenario:
        cenario = {
            "grupo_acesso": "Operações",
            "dominio_acessado": "sistema.escola.com.br",
            "titulo_alerta": TELECOM_EVENT_CODES[codigo],
            "descricao_evento": f"Alerta de telemetria eSIM — código {codigo}.",
            "trafego_mb_7dias": 30,
            "status_anomalia": "queda_critica",
            "variacao_percentual": -20,
        }

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chip = (iccid or DEFAULT_ICCID).strip()

    return {
        "cliente_id": str(cliente_id),
        "codigo_evento": codigo,
        "iccid": chip,
        "timestamp": ts,
        "grupo_acesso": cenario["grupo_acesso"],
        "dominio_acessado": cenario["dominio_acessado"],
        "titulo_alerta": cenario["titulo_alerta"],
        "descricao_evento": cenario["descricao_evento"],
        "trafego_mb_7dias": cenario["trafego_mb_7dias"],
        "status_anomalia": cenario["status_anomalia"],
        "variacao_percentual": cenario["variacao_percentual"],
    }


def montar_headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "BaseMobile-eSIM-Telemetry/1.0",
    }
    secret = (os.environ.get("BASEMOBILE_WEBHOOK_SECRET") or "").strip()
    if secret:
        headers["X-BaseMobile-Token"] = secret
    return headers


def imprimir_separador(titulo: str = "") -> None:
    linha = "=" * 60
    if titulo:
        print(f"\n{linha}\n  {titulo}\n{linha}")
    else:
        print(linha)


def imprimir_json_rotulado(rotulo: str, dados: Any) -> None:
    print(f"\n{rotulo}:")
    print(json.dumps(dados, indent=2, ensure_ascii=False))


def executar_simulacao(url: str, payload: dict[str, Any], timeout: int) -> int:
    headers = montar_headers()
    codigo = payload.get("codigo_evento", "")

    imprimir_separador("SIMULADOR eSIM — Base Mobile (operadora)")
    print("Enviando telemetria bruta do chip inteligente...")
    print(f"Destino: {url}")
    print(f"Código evento (operadora): {codigo}")
    print(f"ICCID: {payload.get('iccid')}")
    print(f"Timestamp: {payload.get('timestamp')}")
    print("Correlação com Framework LeAction: responsabilidade do PanelDX (interno).")

    if "X-BaseMobile-Token" in headers:
        print("\nAutenticação: header X-BaseMobile-Token presente.")
    else:
        print("\nAutenticação: nenhum secret — webhook em modo aberto (dev).")

    imprimir_json_rotulado("Payload enviado (telecom)", payload)

    print(f"\nEnviando alerta ({payload.get('status_anomalia')}) ao webhook PanelDX...")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.exceptions.ConnectionError:
        print("\n[ERRO] Não foi possível conectar ao backend.", file=sys.stderr)
        print(
            textwrap.dedent(
                """
                Verifique se o Flask está rodando:
                  cd LeAction_SysF
                  python app.py
                URL esperada: http://localhost:5002
                """
            ).strip(),
            file=sys.stderr,
        )
        return 1
    except requests.exceptions.Timeout:
        print("\n[ERRO] Timeout aguardando resposta do servidor.", file=sys.stderr)
        return 1
    except requests.exceptions.RequestException as exc:
        print(f"\n[ERRO] Falha na requisição HTTP: {exc}", file=sys.stderr)
        return 1

    imprimir_separador("RESPOSTA DO PANELDX")
    print(f"Status Code: {response.status_code} {response.reason or ''}".strip())

    content_type = (response.headers.get("Content-Type") or "").lower()
    corpo_texto = response.text.strip()

    if "application/json" in content_type or corpo_texto.startswith(("{", "[")):
        try:
            corpo_json = response.json()
            imprimir_json_rotulado("JSON retornado", corpo_json)

            if response.ok:
                if corpo_json.get("ia_processada"):
                    print("\n[OK] PanelDX processou o alerta e correlacionou com o Framework.")
                    if corpo_json.get("bloco_associado") or corpo_json.get("bloco_escolhido"):
                        print(
                            f"Bloco associado (PanelDX): "
                            f"{corpo_json.get('bloco_associado') or corpo_json.get('bloco_escolhido')}"
                        )
                    if corpo_json.get("dominio_associado") or corpo_json.get("dominio_fixado"):
                        print(
                            f"Domínio associado (PanelDX): "
                            f"{corpo_json.get('dominio_associado') or corpo_json.get('dominio_fixado')}"
                        )
                    if corpo_json.get("ia_fallback"):
                        print("[INFO] ia_fallback=true — Bedrock indisponível; bloco via fallback interno.")
                else:
                    print("\n[OK] Webhook aceito pelo PanelDX.")
            else:
                print(f"\n[AVISO] PanelDX respondeu com erro: {corpo_json.get('message', 'sem mensagem')}")

        except json.JSONDecodeError:
            print("\nCorpo (não-JSON):")
            print(corpo_texto or "(vazio)")
    else:
        print("\nCorpo da resposta:")
        print(corpo_texto or "(vazio)")

    imprimir_separador()
    return 0 if response.ok else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simula operadora eSIM enviando telemetria bruta ao webhook Base Mobile do PanelDX.",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("BASEMOBILE_WEBHOOK_URL", DEFAULT_URL),
        help=f"URL do webhook (padrão: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--cliente-id",
        default=os.environ.get("BASEMOBILE_CLIENTE_ID", "1"),
        help="ID do cliente no contrato Base Mobile (padrão: 1)",
    )
    parser.add_argument(
        "--codigo-evento",
        default=os.environ.get("BASEMOBILE_CODIGO_EVENTO", DEFAULT_CODIGO_EVENTO),
        help=f"Código de alerta da operadora (padrão: {DEFAULT_CODIGO_EVENTO})",
    )
    parser.add_argument(
        "--iccid",
        default=os.environ.get("BASEMOBILE_ICCID", DEFAULT_ICCID),
        help=f"ICCID do chip eSIM (padrão: {DEFAULT_ICCID})",
    )
    parser.add_argument(
        "--timestamp",
        default=os.environ.get("BASEMOBILE_TIMESTAMP", ""),
        help="Timestamp ISO8601 UTC (padrão: agora)",
    )
    parser.add_argument(
        "--listar-codigos",
        action="store_true",
        help="Lista códigos de alerta suportados pela operadora (contrato técnico).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("BASEMOBILE_TIMEOUT", DEFAULT_TIMEOUT)),
        help=f"Timeout da requisição em segundos (padrão: {DEFAULT_TIMEOUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.listar_codigos:
        print("Códigos de alerta da operadora (telemetria bruta):")
        for codigo, rotulo in sorted(TELECOM_EVENT_CODES.items()):
            print(f"  • {codigo} — {rotulo}")
        print("\nA correlação com o Framework LeAction é feita internamente pelo PanelDX.")
        return 0

    try:
        payload = montar_payload(
            args.cliente_id,
            args.codigo_evento,
            iccid=args.iccid,
            timestamp=args.timestamp or None,
        )
    except ValueError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1

    return executar_simulacao(args.url, payload, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
