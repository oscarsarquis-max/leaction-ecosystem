"""
ETL para relatórios Azure DevOps agregados por pessoa (pessoas[]).
Espelha o pipeline Node POST /api/ingestao/json.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models import Colaboradores, Indicadores, Medicoes

logger = logging.getLogger(__name__)

SEM_INFORMACAO_RE = re.compile(r"sem\s+informa[cç][aã]o", re.IGNORECASE)
NUMERO_STRING_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
MATRICULA_MAX_LEN = 20

INDICADOR_PAYLOAD_MAP: dict[str, dict[str, Any]] = {
    "P007": {"keys": ["ir", "ie"]},
    "P003": {
        "keys": ["tb", "tr", "horas_bloqueado", "ainda_bloqueado"],
        "aliases": {"bt": "tb"},
    },
    "A004": {"keys": ["mi", "dv"]},
    "E008": {"keys": ["mcy", "dpcy"]},
    "E006": {"keys": ["tec", "ctt"]},
    "E002": {"keys": ["ta", "ltt"], "aliases": {"lt": "ltt"}},
    "A001": {"keys": ["ca", "i3s"], "aliases": {"bp": "i3s"}},
    "A002": {"keys": ["fd", "fp"]},
    "A005": {"keys": ["spb", "spa"], "aliases": {"spr": "spb", "spi": "spa"}},
    "A006": {"keys": ["md", "mp"], "aliases": {"mt": "md"}},
    "A009": {"keys": ["sta", "sdp"]},
    "A010": {"keys": ["btes", "bprod"]},
    "C001": {"keys": ["t0", "tq"], "aliases": {"it": "t0"}},
    "C002": {"keys": ["dr", "i3us"]},
    "C008": {"keys": ["wdr", "ics"]},
    "P001": {
        "keys": ["bv_ir", "bv_rs", "bv_eo", "bv_rc"],
        "aliases": {"ir": "bv_ir", "rs": "bv_rs", "eo": "bv_eo", "rc": "bv_rc"},
    },
    "P004": {"keys": ["pe", "pp"]},
    "P005": {"keys": ["cmpp", "cmpt"], "aliases": {"zmpt": "cmpt"}},
    "E001": {"keys": ["mwi", "mwi_n_itens", "mwi_min_dias", "mwi_max_dias"]},
}


@dataclass
class PessoasIngestionResult:
    sucesso: bool
    mensagem: str
    colaboradores_processados: int = 0
    medicoes_inseridas: int = 0
    colaboradores_ignorados: int = 0
    data_referencia: date | None = None


def is_sem_informacao(valor: Any) -> bool:
    return isinstance(valor, str) and bool(SEM_INFORMACAO_RE.search(valor.strip()))


def sanitize_json_value(valor: Any) -> Any:
    if valor is None:
        return None

    if isinstance(valor, str):
        if is_sem_informacao(valor):
            return None
        trimmed = valor.strip()
        if trimmed and NUMERO_STRING_RE.match(trimmed):
            try:
                numerico = float(trimmed)
                if numerico.is_integer() and "." not in trimmed and "e" not in trimmed.lower():
                    return int(numerico)
                return numerico
            except ValueError:
                return valor
        return valor

    if isinstance(valor, bool) or isinstance(valor, (int, float)):
        return valor

    if isinstance(valor, list):
        return [sanitize_json_value(item) for item in valor]

    if isinstance(valor, dict):
        limpo: dict[str, Any] = {}
        for chave, filho in valor.items():
            if str(chave).startswith("sc_"):
                continue
            limpo[chave] = sanitize_json_value(filho)
        return limpo

    return valor


def _local_part_email(email: str) -> str | None:
    local = email.strip().split("@")[0]
    if not local:
        return None
    normalizado = unicodedata.normalize("NFD", local)
    sem_acento = "".join(ch for ch in normalizado if unicodedata.category(ch) != "Mn")
    limpo = re.sub(r"[^a-zA-Z0-9._-]", ".", sem_acento).lower()
    return limpo or None


def matricula_artificial_from_email(email: Any) -> str | None:
    if email is None:
        return None
    email_str = str(email).strip()
    if not email_str or is_sem_informacao(email_str) or "@" not in email_str:
        return None

    local_part = _local_part_email(email_str)
    if not local_part or is_sem_informacao(local_part):
        return None

    candidata = f"EXT-{local_part}"
    if len(candidata) <= MATRICULA_MAX_LEN:
        return candidata

    digest = hashlib.sha1(local_part.encode("utf-8")).hexdigest()[:4]
    max_local = MATRICULA_MAX_LEN - len("EXT-") - 1 - len(digest)
    return f"EXT-{local_part[: max(1, max_local)]}-{digest}"


def resolver_matricula(pessoa: dict) -> str | None:
    matricula_bruta = pessoa.get("matricula")
    if (
        matricula_bruta is not None
        and str(matricula_bruta).strip()
        and not is_sem_informacao(str(matricula_bruta))
    ):
        matricula = str(matricula_bruta).strip()
        if len(matricula) > MATRICULA_MAX_LEN:
            raise ValueError(f"matricula excede {MATRICULA_MAX_LEN} caracteres: {matricula}")
        return matricula

    return matricula_artificial_from_email(pessoa.get("responsavel_email"))


def resolver_nome(pessoa: dict, matricula: str) -> str:
    nome = pessoa.get("responsavel") or pessoa.get("nome")
    if isinstance(nome, str) and nome.strip() and not is_sem_informacao(nome):
        return nome.strip()[:150]
    return matricula[:150]


def extrair_payload_indicador(pessoa_limpa: dict, cod_indicador: str) -> dict | None:
    mapa = INDICADOR_PAYLOAD_MAP.get(cod_indicador)
    if not mapa:
        return None

    payload: dict[str, Any] = {}
    for chave in mapa["keys"]:
        payload[chave] = pessoa_limpa.get(chave)

    for alias, origem in (mapa.get("aliases") or {}).items():
        payload[alias] = payload.get(origem, pessoa_limpa.get(origem))

    return payload


def payload_tem_dados(payload: dict | None) -> bool:
    if not payload:
        return False
    return any(valor is not None for valor in payload.values())


def extrair_data_referencia(documento: dict) -> date:
    fim = (documento.get("periodo") or {}).get("fim")
    if isinstance(fim, str) and fim.strip():
        return date.fromisoformat(fim.strip()[:10])
    raise ValueError("periodo.fim é obrigatório no JSON para data_referencia")


def is_documento_por_pessoa(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("pessoas"), list)


def _carregar_mapa_indicadores(session: Session) -> dict[str, int]:
    rows = session.execute(
        text(
            """
            SELECT DISTINCT ON (cod_indicador) id, cod_indicador
            FROM indicadores
            ORDER BY
              cod_indicador,
              CASE WHEN nome_grupo = 'Técnica' THEN 0 ELSE 1 END,
              id
            """
        )
    ).mappings().all()
    return {str(row["cod_indicador"]).upper(): int(row["id"]) for row in rows}


def _upsert_colaborador(session: Session, pessoa: dict) -> tuple[int, str]:
    matricula = resolver_matricula(pessoa)
    if not matricula:
        raise ValueError("sem_matricula_nem_email_valido")

    nome = resolver_nome(pessoa, matricula)
    existente = session.scalar(
        select(Colaboradores).where(Colaboradores.matricula == matricula)
    )

    if existente:
        existente.nome = nome
        session.flush()
        return existente.id_colaborador, matricula

    novo = Colaboradores(matricula=matricula, nome=nome)
    session.add(novo)
    session.flush()
    return novo.id_colaborador, matricula


def processar_ingestao_pessoas(
    engine,
    *,
    nome_arquivo: str,
    documento: dict,
) -> PessoasIngestionResult:
    pessoas = documento.get("pessoas") or []
    if not isinstance(pessoas, list):
        raise ValueError("JSON inválido: campo pessoas[] é obrigatório")

    data_referencia = extrair_data_referencia(documento)
    agora = datetime.now(timezone.utc)

    colaboradores_processados = 0
    medicoes_inseridas = 0
    colaboradores_ignorados = 0

    with Session(engine) as session:
        try:
            mapa_indicadores = _carregar_mapa_indicadores(session)
            codigos = list(INDICADOR_PAYLOAD_MAP.keys())

            for pessoa_bruta in pessoas:
                if not isinstance(pessoa_bruta, dict):
                    continue

                try:
                    matricula = resolver_matricula(pessoa_bruta)
                except ValueError:
                    colaboradores_ignorados += 1
                    continue

                if not matricula:
                    colaboradores_ignorados += 1
                    continue

                id_colaborador, _ = _upsert_colaborador(session, pessoa_bruta)
                colaboradores_processados += 1
                pessoa_limpa = sanitize_json_value(pessoa_bruta)

                for cod in codigos:
                    indicador_id = mapa_indicadores.get(cod)
                    if not indicador_id:
                        continue

                    payload = extrair_payload_indicador(pessoa_limpa, cod)
                    if not payload_tem_dados(payload):
                        continue

                    session.add(
                        Medicoes(
                            indicador_id=indicador_id,
                            id_colaborador=id_colaborador,
                            nome_arquivo=nome_arquivo[:100],
                            payload=payload,
                            data_importacao=agora,
                            data_referencia=data_referencia,
                            status_import="SUCESSO",
                            detalhe_status=None,
                        )
                    )
                    medicoes_inseridas += 1

            session.commit()
        except Exception:
            session.rollback()
            raise

    mensagem = (
        f"{colaboradores_processados} colaboradores processados, "
        f"{medicoes_inseridas} medições limpas inseridas"
    )
    logger.info("Ingestão por pessoa concluída (%s): %s", nome_arquivo, mensagem)

    return PessoasIngestionResult(
        sucesso=True,
        mensagem=mensagem,
        colaboradores_processados=colaboradores_processados,
        medicoes_inseridas=medicoes_inseridas,
        colaboradores_ignorados=colaboradores_ignorados,
        data_referencia=data_referencia,
    )
