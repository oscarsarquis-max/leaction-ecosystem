import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

GRUPOS_VALIDOS = frozenset({"Gestão Geral", "Gerência Técnica", "Técnica"})

INDICATOR_CATALOG = {
    "P001": {
        "nome_grupo": "Gestão Geral",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
    },
    "P003": {
        "nome_grupo": "Gerência Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
    },
    "P004": {
        "nome_grupo": "Gerência Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
    },
    "P005": {
        "nome_grupo": "Gestão Geral",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
    },
    "P007": {
        "nome_grupo": "Gerência Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
        "subpapeis_aplicaveis": ["Dev", "Tester"],
    },
    "A001": {
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
    },
    "A002": {
        "nome_grupo": "Gerência Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
    },
    "A009": {
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
    },
    "A010": {
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
    },
}

METRICA_PATTERN = re.compile(r"^([PA]\d{3})\s*-\s*(.+)$", re.IGNORECASE)
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")
SCORE_KEYS = frozenset({"score", "score_percentual", "score_medio", "score_medio_geral"})


def parse_periodo_date(value, field_name: str) -> date | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None

        normalized = cleaned.replace("Z", "+00:00")
        try:
            if "T" in normalized:
                return datetime.fromisoformat(normalized).date()
            return date.fromisoformat(normalized[:10])
        except ValueError:
            pass

        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Formato de data inválido em {field_name}: '{value}'")

    raise ValueError(f"Tipo inválido para {field_name}: {type(value).__name__}")


def extract_codigo_e_nome(payload: dict) -> tuple[str, str]:
    for key in ("metrica", "nome_metrica", "nome"):
        raw = payload.get(key)
        if not raw:
            continue

        match = METRICA_PATTERN.match(str(raw).strip())
        if match:
            return match.group(1).upper(), match.group(2).strip()

    cod = payload.get("cod_indicador")
    nome = payload.get("nome_indicador")
    if cod and nome:
        return str(cod).upper(), str(nome).strip()

    raise ValueError(
        "Não foi possível extrair cod_indicador e nome_indicador. "
        "Use o formato 'P001 - Nome da Métrica' no campo metrica."
    )


def resolve_periodo(payload: dict) -> tuple[date, date]:
    periodo = payload.get("periodo")
    if isinstance(periodo, dict):
        inicio = parse_periodo_date(periodo.get("inicio"), "periodo.inicio")
        fim = parse_periodo_date(periodo.get("fim"), "periodo.fim")
        if inicio and fim:
            if inicio > fim:
                raise ValueError("periodo.inicio não pode ser posterior a periodo.fim")
            return inicio, fim

    timestamp = payload.get("timestamp")
    if timestamp:
        ref = parse_periodo_date(timestamp, "timestamp")
        if ref:
            return ref, ref

    raise ValueError(
        "Período de referência obrigatório. Inclua periodo.inicio e periodo.fim no JSON."
    )


def normalize_score(value) -> Decimal | None:
    if value is None:
        return None

    try:
        score = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

    if score > Decimal("1"):
        return (score / Decimal("100")).quantize(Decimal("0.0001"))

    return score.quantize(Decimal("0.0001"))


def extract_score(payload: dict) -> Decimal | None:
    resumo = payload.get("resumo") if isinstance(payload.get("resumo"), dict) else {}

    for key in ("score", "efficiency_score"):
        if payload.get(key) is not None:
            normalized = normalize_score(payload.get(key))
            if normalized is not None:
                return normalized

    for key in ("score", "score_percentual", "score_medio", "score_medio_geral"):
        if resumo.get(key) is not None:
            normalized = normalize_score(resumo.get(key))
            if normalized is not None:
                return normalized

    if payload.get("efficiency_percentage") is not None:
        return normalize_score(payload.get("efficiency_percentage"))

    return None


def build_resumo_parametros(payload: dict) -> dict:
    resumo = payload.get("resumo")
    if not isinstance(resumo, dict):
        return {}

    return {
        key: value
        for key, value in resumo.items()
        if key not in SCORE_KEYS and value is not None
    }


def extract_itens_detalhe(payload: dict) -> list:
    for key in ("itens", "bugs_detalhes"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def enrich_payload_indicador(cod_indicador: str, payload: dict) -> dict:
    """Normaliza aliases de variáveis e resumo de score por indicador."""
    if not isinstance(payload, dict):
        return payload

    enriched = dict(payload)
    cod = str(cod_indicador or "").upper()

    if cod == "A010":
        btes = enriched.get("btes")
        if btes is None and enriched.get("bugs_detectados_teste") is not None:
            btes = enriched["bugs_detectados_teste"]
            enriched["btes"] = btes

        bprod = enriched.get("bprod")
        if bprod is None and enriched.get("bugs_em_producao") is not None:
            bprod = enriched["bugs_em_producao"]
        if bprod is None and enriched.get("bugs_producao") is not None:
            bprod = enriched["bugs_producao"]
        if (
            bprod is None
            and enriched.get("total_bugs") is not None
            and btes is not None
        ):
            try:
                bprod = max(0, int(enriched["total_bugs"]) - int(btes))
            except (TypeError, ValueError):
                bprod = None
        if bprod is not None:
            enriched["bprod"] = bprod

    score = extract_score(enriched)
    if score is not None:
        resumo = enriched.get("resumo")
        if not isinstance(resumo, dict):
            resumo = {}
        else:
            resumo = dict(resumo)
        score_float = float(score)
        resumo["score"] = score_float
        resumo["score_percentual"] = round(score_float * 100, 4)
        enriched["resumo"] = resumo

    return enriched


def extract_matricula(payload: dict) -> str | None:
    for key in ("matricula", "colaborador_matricula"):
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    colaborador = payload.get("colaborador")
    if isinstance(colaborador, dict):
        value = colaborador.get("matricula")
        if value is not None and str(value).strip():
            return str(value).strip()

    resumo = payload.get("resumo")
    if isinstance(resumo, dict):
        for key in ("matricula", "colaborador_matricula"):
            value = resumo.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()

    return None


def resolve_catalog_metadata(cod_indicador: str, payload: dict) -> dict:
    catalog = INDICATOR_CATALOG.get(cod_indicador, {})

    nome_grupo = payload.get("nome_grupo") or catalog.get("nome_grupo")
    if nome_grupo not in GRUPOS_VALIDOS:
        if cod_indicador.startswith("P"):
            nome_grupo = "Gerência Técnica"
        elif cod_indicador.startswith("A"):
            nome_grupo = "Técnica"
        else:
            raise ValueError(
                f"nome_grupo inválido para {cod_indicador}. "
                f"Valores aceites: {', '.join(sorted(GRUPOS_VALIDOS))}"
            )

    return {
        "nome_grupo": nome_grupo,
        "dimensao": payload.get("dimensao") or catalog.get("dimensao"),
        "nivel_avaliacao": payload.get("nivel_avaliacao") or catalog.get("nivel_avaliacao"),
    }


def parse_payload_to_posicao(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("O payload JSON deve ser um objeto")

    cod_indicador, nome_indicador = extract_codigo_e_nome(payload)
    data_referencia_inicio, data_referencia_fim = resolve_periodo(payload)
    metadata = resolve_catalog_metadata(cod_indicador, payload)

    return {
        "nome_grupo": metadata["nome_grupo"],
        "cod_indicador": cod_indicador,
        "nome_indicador": nome_indicador,
        "dimensao": metadata["dimensao"],
        "nivel_avaliacao": metadata["nivel_avaliacao"],
        "score_indicador": extract_score(payload),
        "data_referencia_inicio": data_referencia_inicio,
        "data_referencia_fim": data_referencia_fim,
        "resumo_parametros": build_resumo_parametros(payload),
        "itens_detalhe": extract_itens_detalhe(payload),
    }
