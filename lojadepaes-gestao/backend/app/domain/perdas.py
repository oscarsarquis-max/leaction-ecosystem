"""Perda e rendimento. Um serviço só: a tela, o custo e o Gigio leem daqui.

A perda não é decisão do Gigio. A origem, nesta ordem: ajuste manual com motivo,
medido (3 produções ou mais), padrão da casa, referência externa. Sem referência
que sirva, o valor fica vazio — nunca 0 %.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import stdev
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ErroDeDominio
from app.models.perdas import FORMATOS, TIPOS_PERDA, PerdaMedicao, PerdaPadrao, PerdaReferencia
from app.models.produtos import Receita

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "catalogo" / "referencia-perdas.yaml"
OBS_SEMENTE = "informado pelo Oscar, 06/11"
OBS_CASA = "padrão da casa, definido pelo Oscar em 23/11"
MOTIVO_ANTIGO = "Valor informado antes do modelo de perdas."
_GRAMA = Decimal("1")
_DECIMO = Decimal("0.1")
_CEM = Decimal(100)
_FORMATOS_REF = ("qualquer", *FORMATOS)
_ROTULO_TIPO = {"processo": "Processo", "coccao": "Cocção", "comercial": "Comercial"}
_ROTULO_FORMATO = {
    "qualquer": "Qualquer formato",
    "forma": "Forma",
    "forma_enriquecida": "Forma enriquecida",
    "livre": "Livre",
    "assadeira": "Assadeira",
    "pequeno": "Pequeno",
}


class ReferenciaInvalida(Exception):
    def __init__(self, erros: list[str]) -> None:
        self.erros = erros
        super().__init__("; ".join(erros))


@dataclass
class ResultadoCarga:
    versao: int
    inseridos: int = 0
    alterados: int = 0
    iguais: int = 0
    fora_do_arquivo: int = 0


def _q(valor: Decimal, passo: Decimal = _DECIMO) -> Decimal:
    return valor.quantize(passo, rounding=ROUND_HALF_UP)


def _d(valor) -> Decimal | None:
    if valor is None or valor == "":
        return None
    return Decimal(str(valor))


def _txt_pct(valor: Decimal) -> str:
    numero = _q(valor)
    if numero == numero.to_integral_value():
        return f"{numero.to_integral_value():f}"
    return f"{numero:.1f}".replace(".", ",")


def peso_cru_exato(peso_final: Decimal, coccao_pct: Decimal) -> Decimal:
    return peso_final / (Decimal(1) - coccao_pct / _CEM)


def peso_cru_g(peso_final: Decimal, coccao_pct: Decimal) -> Decimal:
    return peso_cru_exato(peso_final, coccao_pct).quantize(_GRAMA, rounding=ROUND_HALF_UP)


def unidades_de(massa_total: Decimal, processo_pct: Decimal, peso_cru: Decimal) -> int:
    if peso_cru <= 0:
        return 0
    disponivel = massa_total * (Decimal(1) - processo_pct / _CEM)
    return int((disponivel / peso_cru).to_integral_value(rounding=ROUND_FLOOR))


def massa_necessaria(unidades: int, peso_final: Decimal, coccao_pct: Decimal, processo_pct: Decimal) -> Decimal:
    cru = peso_cru_exato(peso_final, coccao_pct)
    return (Decimal(unidades) * cru / (Decimal(1) - processo_pct / _CEM)).quantize(_GRAMA, rounding=ROUND_HALF_UP)


def _faixa_peso(minimo, maximo) -> str | None:
    if minimo is None and maximo is None:
        return None
    if minimo is None:
        return f"até {_txt_pct(Decimal(str(maximo)))} g"
    if maximo is None:
        return f"a partir de {_txt_pct(Decimal(str(minimo)))} g"
    return f"{_txt_pct(Decimal(str(minimo)))}–{_txt_pct(Decimal(str(maximo)))} g"


def _cabe(peso: Decimal | None, minimo, maximo) -> bool:
    if minimo is None and maximo is None:
        return True
    if peso is None:
        return False
    if minimo is not None and peso < Decimal(str(minimo)):
        return False
    if maximo is not None and peso > Decimal(str(maximo)):
        return False
    return True


def _rotulo(percentual: Decimal | None, origem: str | None, *, extra: str = "", n: int = 0) -> str:
    if percentual is None or origem is None:
        return "sem referência"
    texto = f"{_txt_pct(percentual)} %"
    if origem == "padrao":
        return f"{texto} · padrão da casa"
    if origem == "referencia":
        return f"{texto} · referência ({extra})" if extra else f"{texto} · referência"
    if origem == "medido":
        producoes = "produção" if n == 1 else "produções"
        return f"{texto} · medido em {n} {producoes}"
    return f"{texto} · ajuste manual"


def _medidas(medicoes: list[dict]) -> dict | None:
    completas = []
    for item in medicoes:
        massa = _d(item.get("massa_total_g"))
        pecas = item.get("pecas")
        cru = _d(item.get("peso_cru_medio_g"))
        final = _d(item.get("peso_final_medio_g"))
        if massa is None or not pecas or cru is None or final is None or massa <= 0 or cru <= 0:
            continue
        processo = (massa - Decimal(pecas) * cru) / massa * _CEM
        coccao = (cru - final) / cru * _CEM
        completas.append({"processo": processo, "coccao": coccao, "data": item.get("data")})
    if len(completas) < 3:
        return None
    saida = {"n": len(completas), "linhas": completas}
    for tipo in ("processo", "coccao"):
        valores = [item[tipo] for item in completas]
        saida[tipo] = _q(sum(valores, Decimal(0)) / Decimal(len(valores)))
        saida[f"desvio_{tipo}"] = _q(Decimal(str(stdev([float(v) for v in valores]))))
    return saida


def _especifico_padrao(item: dict) -> bool:
    return item.get("familia_id") is not None or item.get("formato") is not None


def _melhor_padrao(
    padroes: list[dict],
    tipo: str,
    formato: str | None,
    familia_id,
    peso: Decimal | None,
    *,
    so_especifico: bool | None = None,
) -> dict | None:
    candidatos = []
    for item in padroes:
        if not item.get("ativo", True) or item.get("tipo") != tipo:
            continue
        if item.get("familia_id") not in (None, familia_id):
            continue
        if item.get("formato") not in (None, formato):
            continue
        if not _cabe(peso, item.get("peso_min_g"), item.get("peso_max_g")):
            continue
        especifico = _especifico_padrao(item)
        if so_especifico is True and not especifico:
            continue
        if so_especifico is False and especifico:
            continue
        grau = int(item.get("familia_id") is not None) + int(item.get("formato") is not None)
        candidatos.append((grau, item))
    if not candidatos:
        return None
    candidatos.sort(key=lambda par: par[0], reverse=True)
    return candidatos[0][1]


def _distancia_faixa(peso: Decimal, minimo, maximo) -> Decimal | None:
    if minimo is None and maximo is None:
        return Decimal(0)
    lo = None if minimo is None else Decimal(str(minimo))
    hi = None if maximo is None else Decimal(str(maximo))
    if lo is not None and hi is not None and lo <= peso <= hi:
        return Decimal(0)
    if lo is not None and peso < lo:
        return lo - peso
    if hi is not None and peso > hi:
        return peso - hi
    if lo is not None and hi is None and peso >= lo:
        return Decimal(0)
    if hi is not None and lo is None and peso <= hi:
        return Decimal(0)
    return None


def _melhor_referencia(
    referencias: list[dict],
    tipo: str,
    formato: str | None,
    peso: Decimal | None,
    *,
    so_formato: bool | None = None,
    permitir_proxima: bool = True,
) -> dict | None:
    exatos = []
    for item in referencias:
        if item.get("tipo") != tipo:
            continue
        formato_ref = item.get("formato")
        if formato_ref != "qualquer" and formato_ref != formato:
            continue
        geral = formato_ref == "qualquer"
        if so_formato is True and geral:
            continue
        if so_formato is False and not geral:
            continue
        if not _cabe(peso, item.get("peso_min_g"), item.get("peso_max_g")):
            continue
        exatos.append((0 if geral else 1, item))
    if exatos:
        exatos.sort(key=lambda par: par[0], reverse=True)
        return exatos[0][1]
    if not permitir_proxima or peso is None or so_formato is False:
        return None
    # Peso fora das faixas do mesmo formato: a faixa mais próxima, confiança baixa.
    proximas = []
    for item in referencias:
        if item.get("tipo") != tipo:
            continue
        if item.get("formato") != formato or formato is None:
            continue
        dist = _distancia_faixa(peso, item.get("peso_min_g"), item.get("peso_max_g"))
        if dist is None:
            continue
        proximas.append((dist, item))
    if not proximas:
        return None
    proximas.sort(key=lambda par: par[0])
    escolhida = dict(proximas[0][1])
    escolhida["_fora_faixa"] = True
    escolhida["_peso_fora"] = peso
    return escolhida


def _extra_referencia(ref: dict | None) -> str:
    if ref is None:
        return ""
    partes = [_ROTULO_FORMATO.get(ref.get("formato") or "", ref.get("formato") or "")]
    faixa = _faixa_peso(ref.get("peso_min_g"), ref.get("peso_max_g"))
    if faixa:
        partes.append(faixa)
    return ", ".join(p for p in partes if p)


def _explicar(ref: dict | None, medidas: dict | None, medicoes: list[dict]) -> dict:
    if ref is None:
        faixa = "Sem referência para este formato e este peso."
        fonte = None
        url = None
        nota = None
    else:
        limites = ""
        if ref.get("faixa_min") is not None and ref.get("faixa_max") is not None:
            limites = f", faixa {_txt_pct(Decimal(str(ref['faixa_min'])))}–{_txt_pct(Decimal(str(ref['faixa_max'])))} %"
        faixa = f"Referência: {_extra_referencia(ref)}{limites}, sugerido {_txt_pct(Decimal(str(ref['sugerido'])))} %."
        fonte = ref.get("fonte_titulo")
        url = ref.get("fonte_url")
        nota = ref.get("nota")
        if ref.get("_fora_faixa") and ref.get("_peso_fora") is not None:
            fora = int(Decimal(str(ref["_peso_fora"])).quantize(_GRAMA, rounding=ROUND_HALF_UP))
            faixa = f"{faixa} Fora da faixa ({fora} g): usada a faixa mais próxima."
            nota = f"fora da faixa ({fora} g)" + (f"; {nota}" if nota else "")
    return {
        "faixa": faixa,
        "fonte": fonte,
        "fonte_url": url,
        "nota": nota,
        "n_medicoes": 0 if medidas is None else medidas["n"],
        "desvio_processo": None if medidas is None else float(medidas["desvio_processo"]),
        "desvio_coccao": None if medidas is None else float(medidas["desvio_coccao"]),
        "medicoes": [
            {
                "data": str(item["data"]) if item.get("data") else None,
                "massa_total_g": float(item["massa_total_g"]),
                "pecas": int(item["pecas"]),
                "peso_cru_medio_g": float(item["peso_cru_medio_g"]),
                "peso_final_medio_g": float(item["peso_final_medio_g"]),
            }
            for item in medicoes
            if item.get("massa_total_g") is not None
        ],
    }


def _lado_de(
    pct,
    origem: str,
    *,
    motivo=None,
    referencia_id=None,
    padrao_id=None,
    desvio=None,
    rotulo_extra="",
    n=0,
    explicacao,
    confianca=None,
) -> dict:
    valor = pct if isinstance(pct, Decimal) else _d(pct)
    saida = {
        "percentual": float(valor) if valor is not None else None,
        "origem": origem,
        "rotulo": _rotulo(valor, origem, extra=rotulo_extra, n=n),
        "motivo": motivo,
        "referencia_id": referencia_id,
        "explicacao": explicacao,
    }
    if padrao_id is not None:
        saida["padrao_id"] = padrao_id
    if desvio is not None:
        saida["desvio"] = desvio
    if confianca is not None:
        saida["confianca"] = confianca
    elif origem == "referencia" and explicacao.get("nota") and str(explicacao["nota"]).startswith("fora da faixa"):
        saida["confianca"] = "baixa"
    return saida


def _uma(
    *,
    tipo: str,
    manual_pct,
    manual_origem,
    manual_motivo,
    padroes,
    referencias,
    medidas,
    medicoes,
    formato,
    familia_id,
    peso,
) -> dict:
    """Ordem: manual → medido → padrão específico → referência do formato → padrão geral → referência geral."""
    ref_fmt = _melhor_referencia(referencias, tipo, formato, peso, so_formato=True)
    ref_geral = _melhor_referencia(referencias, tipo, formato, peso, so_formato=False, permitir_proxima=False)
    ref_explicacao = ref_fmt or ref_geral or _melhor_referencia(referencias, tipo, formato, peso)
    explicacao = _explicar(ref_explicacao, medidas, medicoes)
    if manual_origem == "manual" and manual_pct is not None and (manual_motivo or "").strip():
        return _lado_de(manual_pct, "manual", motivo=manual_motivo, explicacao=explicacao)
    if medidas is not None and medidas.get(tipo) is not None:
        return _lado_de(
            medidas[tipo],
            "medido",
            desvio=float(medidas[f"desvio_{tipo}"]),
            n=medidas["n"],
            explicacao=explicacao,
        )
    padrao_esp = _melhor_padrao(padroes, tipo, formato, familia_id, peso, so_especifico=True)
    if padrao_esp is not None:
        return _lado_de(
            padrao_esp["percentual"],
            "padrao",
            motivo=padrao_esp.get("observacao"),
            padrao_id=str(padrao_esp["id"]) if padrao_esp.get("id") else None,
            explicacao=explicacao,
        )
    if ref_fmt is not None:
        return _lado_de(
            ref_fmt["sugerido"],
            "referencia",
            referencia_id=str(ref_fmt["id"]) if ref_fmt.get("id") else None,
            rotulo_extra=_extra_referencia(ref_fmt),
            explicacao=_explicar(ref_fmt, medidas, medicoes),
        )
    padrao_geral = _melhor_padrao(padroes, tipo, formato, familia_id, peso, so_especifico=False)
    if padrao_geral is not None:
        return _lado_de(
            padrao_geral["percentual"],
            "padrao",
            motivo=padrao_geral.get("observacao"),
            padrao_id=str(padrao_geral["id"]) if padrao_geral.get("id") else None,
            explicacao=explicacao,
        )
    if ref_geral is not None:
        return _lado_de(
            ref_geral["sugerido"],
            "referencia",
            referencia_id=str(ref_geral["id"]) if ref_geral.get("id") else None,
            rotulo_extra=_extra_referencia(ref_geral),
            explicacao=_explicar(ref_geral, medidas, medicoes),
        )
    return {
        "percentual": None,
        "origem": None,
        "rotulo": "sem referência",
        "motivo": None,
        "referencia_id": None,
        "explicacao": explicacao,
    }


def _kwargs_manual(manual):
    if manual is None:
        return None, None, None
    return manual.get("percentual"), manual.get("origem"), manual.get("motivo")


def resolver_valores(
    *,
    formato: str | None,
    familia_id,
    peso_final,
    massa_total,
    unidades_desejadas,
    manual_processo=None,
    manual_coccao=None,
    padroes: list[dict] | None = None,
    referencias: list[dict] | None = None,
    medicoes: list[dict] | None = None,
    unidades_rendimento: int | None = None,
) -> dict:
    """Conta pura. Com `unidades_rendimento` (N), o peso final sai do sistema; senão, usa o peso final informado."""
    padroes = padroes or []
    referencias = referencias or []
    medicoes = medicoes or []
    medidas = _medidas(medicoes)
    mp, mo, mm = _kwargs_manual(manual_processo)
    cp, co, cm = _kwargs_manual(manual_coccao)
    n = int(unidades_rendimento) if unidades_rendimento and int(unidades_rendimento) > 0 else None
    massa = _d(massa_total)

    if n is not None and massa is not None:
        # Modo N: cru = massa × (1 − processo) ÷ N; cocção uma vez pelo cru; final = cru × (1 − cocção).
        processo = _uma(
            tipo="processo",
            manual_pct=mp,
            manual_origem=mo,
            manual_motivo=mm,
            padroes=padroes,
            referencias=referencias,
            medidas=medidas,
            medicoes=medicoes,
            formato=formato,
            familia_id=familia_id,
            peso=None,
        )
        cru = None
        cru_g = None
        final = None
        coccao = _uma(
            tipo="coccao",
            manual_pct=cp,
            manual_origem=co,
            manual_motivo=cm,
            padroes=padroes,
            referencias=referencias,
            medidas=medidas,
            medicoes=medicoes,
            formato=formato,
            familia_id=familia_id,
            peso=None,
        )
        if processo["percentual"] is not None:
            cru = massa * (Decimal(1) - Decimal(str(processo["percentual"])) / _CEM) / Decimal(n)
            cru_g = cru.quantize(_GRAMA, rounding=ROUND_HALF_UP)
            coccao = _uma(
                tipo="coccao",
                manual_pct=cp,
                manual_origem=co,
                manual_motivo=cm,
                padroes=padroes,
                referencias=referencias,
                medidas=medidas,
                medicoes=medicoes,
                formato=formato,
                familia_id=familia_id,
                peso=cru,
            )
            if coccao["percentual"] is not None:
                final = (cru * (Decimal(1) - Decimal(str(coccao["percentual"])) / _CEM)).quantize(
                    _GRAMA, rounding=ROUND_HALF_UP
                )
        necessaria = None
        if unidades_desejadas and cru is not None and processo["percentual"] is not None:
            necessaria = (
                Decimal(int(unidades_desejadas)) * cru / (Decimal(1) - Decimal(str(processo["percentual"])) / _CEM)
            ).quantize(_GRAMA, rounding=ROUND_HALF_UP)
        return {
            "formato": formato,
            "peso_final_g": float(final) if final is not None else None,
            "unidades_desejadas": int(unidades_desejadas) if unidades_desejadas else None,
            "processo": processo,
            "coccao": coccao,
            "peso_cru_g": float(cru_g) if cru_g is not None else None,
            "unidades": n,
            "massa_necessaria_g": float(necessaria) if necessaria is not None else None,
        }

    # Legado: peso final informado → deriva cru e quantos pães cabem.
    final = _d(peso_final)
    peso = final
    coccao = _uma(
        tipo="coccao",
        manual_pct=cp,
        manual_origem=co,
        manual_motivo=cm,
        padroes=padroes,
        referencias=referencias,
        medidas=medidas,
        medicoes=medicoes,
        formato=formato,
        familia_id=familia_id,
        peso=peso,
    )
    cru = None
    if final is not None and coccao["percentual"] is not None:
        cru = peso_cru_exato(final, Decimal(str(coccao["percentual"])))
        de_novo = _uma(
            tipo="coccao",
            manual_pct=cp,
            manual_origem=co,
            manual_motivo=cm,
            padroes=padroes,
            referencias=referencias,
            medidas=medidas,
            medicoes=medicoes,
            formato=formato,
            familia_id=familia_id,
            peso=cru,
        )
        if de_novo.get("referencia_id") != coccao.get("referencia_id") or de_novo.get("origem") != coccao.get("origem"):
            coccao = de_novo
            if coccao["percentual"] is not None:
                cru = peso_cru_exato(final, Decimal(str(coccao["percentual"])))
    processo = _uma(
        tipo="processo",
        manual_pct=mp,
        manual_origem=mo,
        manual_motivo=mm,
        padroes=padroes,
        referencias=referencias,
        medidas=medidas,
        medicoes=medicoes,
        formato=formato,
        familia_id=familia_id,
        peso=cru if cru is not None else peso,
    )
    cru_g = None
    unidades = None
    necessaria = None
    if final is not None and coccao["percentual"] is not None and processo["percentual"] is not None:
        cru_g = peso_cru_g(final, Decimal(str(coccao["percentual"])))
        if massa is not None:
            unidades = unidades_de(massa, Decimal(str(processo["percentual"])), cru_g)
        if unidades_desejadas:
            necessaria = massa_necessaria(
                int(unidades_desejadas), final, Decimal(str(coccao["percentual"])), Decimal(str(processo["percentual"]))
            )
    return {
        "formato": formato,
        "peso_final_g": float(final) if final is not None else None,
        "unidades_desejadas": int(unidades_desejadas) if unidades_desejadas else None,
        "processo": processo,
        "coccao": coccao,
        "peso_cru_g": float(cru_g) if cru_g is not None else None,
        "unidades": unidades,
        "massa_necessaria_g": float(necessaria) if necessaria is not None else None,
    }


def texto_fixo(vista: dict | None) -> str:
    base = "Não estime perda de processo nem de cocção. Esses números já vêm resolvidos. Se vier perda_pct, ela é ignorada."
    if not vista:
        return base
    return (
        f"Perda de processo já resolvida: {vista['processo']['rotulo']}. "
        f"Perda de cocção já resolvida: {vista['coccao']['rotulo']}. {base}"
    )


def _linhas_padrao(db: Session) -> list[dict]:
    return [
        {
            "id": p.id,
            "tipo": p.tipo,
            "formato": p.formato,
            "familia_id": p.familia_id,
            "peso_min_g": p.peso_min_g,
            "peso_max_g": p.peso_max_g,
            "percentual": p.percentual,
            "observacao": p.observacao,
            "ativo": p.ativo,
        }
        for p in db.scalars(select(PerdaPadrao).where(PerdaPadrao.ativo.is_(True)))
    ]


def _linhas_referencia(db: Session) -> list[dict]:
    return [
        {
            "id": r.id,
            "tipo": r.tipo,
            "formato": r.formato,
            "peso_min_g": r.peso_min_g,
            "peso_max_g": r.peso_max_g,
            "faixa_min": r.faixa_min,
            "faixa_max": r.faixa_max,
            "sugerido": r.sugerido,
            "fonte_titulo": r.fonte_titulo,
            "fonte_url": r.fonte_url,
            "nota": r.nota,
        }
        for r in db.scalars(select(PerdaReferencia))
    ]


def _linhas_medicao(db: Session, receita_id: UUID) -> list[dict]:
    linhas = db.scalars(select(PerdaMedicao).where(PerdaMedicao.receita_id == receita_id).order_by(PerdaMedicao.data))
    return [
        {
            "data": m.data,
            "massa_total_g": m.massa_total_g,
            "pecas": m.pecas,
            "peso_cru_medio_g": m.peso_cru_medio_g,
            "peso_final_medio_g": m.peso_final_medio_g,
        }
        for m in linhas
    ]


def perda_medida(db: Session, receita_id: UUID) -> dict | None:
    """Média e desvio quando há 3 medições completas ou mais. Com menos, nada."""
    return _medidas(_linhas_medicao(db, receita_id))


def resolver_receita(db: Session, receita: Receita, *, familia_id, massa_total_g) -> dict:
    manual_processo = None
    if receita.perda_processo_origem == "manual":
        manual_processo = {
            "percentual": receita.perda_processo_pct,
            "origem": "manual",
            "motivo": receita.perda_processo_motivo,
        }
    manual_coccao = None
    if receita.perda_coccao_origem == "manual":
        manual_coccao = {
            "percentual": receita.perda_coccao_pct,
            "origem": "manual",
            "motivo": receita.perda_coccao_motivo,
        }
    padroes = _linhas_padrao(db)
    referencias = _linhas_referencia(db)
    medicoes = _linhas_medicao(db, receita.id)
    kwargs = dict(
        formato=receita.formato,
        familia_id=familia_id,
        massa_total=massa_total_g,
        unidades_desejadas=receita.unidades_desejadas,
        manual_processo=manual_processo,
        manual_coccao=manual_coccao,
        padroes=padroes,
        referencias=referencias,
        medicoes=medicoes,
    )
    n = None
    if (
        receita.rendimento_unidade == "un"
        and receita.rendimento_quantidade is not None
        and Decimal(str(receita.rendimento_quantidade)) > 0
    ):
        n = int(Decimal(str(receita.rendimento_quantidade)).to_integral_value(rounding=ROUND_HALF_UP))
    peso = receita.peso_unidade_g
    if n and peso is None:
        return resolver_valores(**kwargs, peso_final=None, unidades_rendimento=n)
    if n and peso is not None and massa_total_g is not None:
        # Ambos gravados: se o final do modo N bate com o peso, N manda (peso derivado);
        # senão é receita antiga (peso informado + unidades pelo chão).
        vista_n = resolver_valores(**kwargs, peso_final=None, unidades_rendimento=n)
        final_n = vista_n.get("peso_final_g")
        if final_n is not None and abs(float(final_n) - float(peso)) <= 1.5:
            return vista_n
    return resolver_valores(**kwargs, peso_final=peso, unidades_rendimento=None)


def _tem_padrao_geral(db: Session, organizacao_id: UUID, tipo: str) -> bool:
    return (
        db.scalar(
            select(PerdaPadrao.id).where(
                PerdaPadrao.organizacao_id == organizacao_id,
                PerdaPadrao.tipo == tipo,
                PerdaPadrao.familia_id.is_(None),
                PerdaPadrao.formato.is_(None),
                PerdaPadrao.peso_min_g.is_(None),
                PerdaPadrao.peso_max_g.is_(None),
                PerdaPadrao.ativo.is_(True),
            )
        )
        is not None
    )


def semear(db: Session, organizacao_id: UUID) -> None:
    """Organização nova: processo 5 % e cocção 14 %, qualquer formato/peso (padrão da casa)."""
    if not _tem_padrao_geral(db, organizacao_id, "processo"):
        db.add(
            PerdaPadrao(
                organizacao_id=organizacao_id,
                familia_id=None,
                formato=None,
                peso_min_g=None,
                peso_max_g=None,
                tipo="processo",
                percentual=Decimal(5),
                observacao=OBS_CASA,
                ativo=True,
            )
        )
    if not _tem_padrao_geral(db, organizacao_id, "coccao"):
        db.add(
            PerdaPadrao(
                organizacao_id=organizacao_id,
                familia_id=None,
                formato=None,
                peso_min_g=None,
                peso_max_g=None,
                tipo="coccao",
                percentual=Decimal(14),
                observacao=OBS_CASA,
                ativo=True,
            )
        )
    db.flush()


def _publicar_padrao(p: PerdaPadrao) -> dict:
    return {
        "id": str(p.id),
        "tipo": p.tipo,
        "tipo_rotulo": _ROTULO_TIPO.get(p.tipo, p.tipo),
        "formato": p.formato,
        "formato_rotulo": "Qualquer formato" if not p.formato else _ROTULO_FORMATO.get(p.formato, p.formato),
        "familia_id": str(p.familia_id) if p.familia_id else None,
        "peso_min_g": float(p.peso_min_g) if p.peso_min_g is not None else None,
        "peso_max_g": float(p.peso_max_g) if p.peso_max_g is not None else None,
        "faixa": _faixa_peso(p.peso_min_g, p.peso_max_g) or "Qualquer peso",
        "percentual": float(p.percentual),
        "rotulo": f"{_txt_pct(Decimal(p.percentual))} %",
        "observacao": p.observacao or "",
        "ativo": p.ativo,
    }


def listar_padroes(db: Session, organizacao_id: UUID) -> list[dict]:
    semear(db, organizacao_id)
    linhas = db.scalars(select(PerdaPadrao).order_by(PerdaPadrao.tipo, PerdaPadrao.peso_min_g))
    return [_publicar_padrao(p) for p in linhas]


def _aplicar_padrao(padrao: PerdaPadrao, dados: dict) -> None:
    tipo = dados.get("tipo") or padrao.tipo
    if tipo not in TIPOS_PERDA:
        raise ErroDeDominio("tipo_invalido", "O tipo é processo, cocção ou comercial.")
    formato = dados.get("formato") or None
    if formato == "":
        formato = None
    if formato is not None and formato not in FORMATOS:
        raise ErroDeDominio("formato_invalido", "O formato não é um dos formatos da casa.")
    percentual = _d(dados.get("percentual"))
    if percentual is None or percentual <= 0 or percentual >= 100:
        raise ErroDeDominio("percentual_invalido", "O percentual fica entre 0 e menos de 100.")
    padrao.tipo = tipo
    padrao.formato = formato
    padrao.peso_min_g = _d(dados.get("peso_min_g"))
    padrao.peso_max_g = _d(dados.get("peso_max_g"))
    padrao.percentual = percentual
    padrao.observacao = (dados.get("observacao") or "").strip() or None
    if "ativo" in dados and dados.get("ativo") is not None:
        padrao.ativo = bool(dados.get("ativo"))


def criar_padrao(db: Session, organizacao_id: UUID, dados: dict) -> dict:
    semear(db, organizacao_id)
    padrao = PerdaPadrao(organizacao_id=organizacao_id, tipo="processo", percentual=Decimal(0), ativo=True)
    _aplicar_padrao(padrao, dados)
    db.add(padrao)
    db.flush()
    return _publicar_padrao(padrao)


def alterar_padrao(db: Session, padrao_id: UUID, dados: dict) -> dict:
    padrao = db.get(PerdaPadrao, padrao_id)
    if padrao is None:
        raise ErroDeDominio("padrao_inexistente", "Esse padrão de perda não existe.", status=404)
    _aplicar_padrao(padrao, dados)
    db.flush()
    return _publicar_padrao(padrao)


def listar_referencia(db: Session) -> list[dict]:
    saida = []
    for r in db.scalars(select(PerdaReferencia).order_by(PerdaReferencia.tipo, PerdaReferencia.formato, PerdaReferencia.peso_min_g)):
        saida.append(
            {
                "id": str(r.id),
                "tipo": r.tipo,
                "tipo_rotulo": _ROTULO_TIPO.get(r.tipo, r.tipo),
                "formato": r.formato,
                "formato_rotulo": _ROTULO_FORMATO.get(r.formato, r.formato),
                "faixa": _faixa_peso(r.peso_min_g, r.peso_max_g) or "Qualquer peso",
                "sugerido": f"{_txt_pct(Decimal(r.sugerido))} %",
                "fonte": r.fonte_titulo,
                "fonte_url": r.fonte_url,
                "nota": r.nota,
            }
        )
    return saida


def ler_referencia(caminho: Path | str = CAMINHO_PADRAO) -> dict:
    caminho = Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReferenciaInvalida([f"não consegui ler {caminho}: {exc}"]) from None
    try:
        dados = yaml.safe_load(texto)
    except yaml.YAMLError as exc:
        raise ReferenciaInvalida([f"YAML inválido ({exc})"]) from None
    erros: list[str] = []
    if not isinstance(dados, dict):
        raise ReferenciaInvalida(["o arquivo precisa ser um mapa com versao, fontes e referencias"])
    versao = dados.get("versao")
    if not isinstance(versao, int):
        erros.append("versao precisa ser um inteiro")
    fontes = {}
    for fonte in dados.get("fontes") or []:
        if not isinstance(fonte, dict) or not fonte.get("id"):
            erros.append("cada fonte precisa de id")
            continue
        fontes[str(fonte["id"])] = fonte
    referencias = dados.get("referencias") or []
    if not isinstance(referencias, list) or not referencias:
        erros.append("referencias precisa ser uma lista")
    linhas = []
    for indice, item in enumerate(referencias, start=1):
        if not isinstance(item, dict):
            erros.append(f"referência {indice} não é um mapa")
            continue
        tipo = item.get("tipo")
        formato = item.get("formato")
        if tipo not in TIPOS_PERDA:
            erros.append(f"referência {indice}: tipo inválido")
        if formato not in _FORMATOS_REF:
            erros.append(f"referência {indice}: formato inválido")
        sugerido = item.get("sugerido")
        if not isinstance(sugerido, (int, float)) or sugerido < 0 or sugerido >= 100:
            erros.append(f"referência {indice}: sugerido inválido")
        peso = item.get("peso_g") or [None, None]
        faixa = item.get("faixa") or [None, None]
        if not isinstance(peso, list) or len(peso) != 2 or not isinstance(faixa, list) or len(faixa) != 2:
            erros.append(f"referência {indice}: peso_g e faixa são pares")
            continue
        fonte_id = str(item.get("fonte") or "")
        fonte = fontes.get(fonte_id)
        titulo = fonte.get("titulo") if fonte else "Prática"
        url = fonte.get("url") if fonte else None
        linhas.append(
            {
                "tipo": tipo,
                "formato": formato,
                "peso_min_g": None if peso[0] is None else Decimal(str(peso[0])),
                "peso_max_g": None if peso[1] is None else Decimal(str(peso[1])),
                "faixa_min": None if faixa[0] is None else Decimal(str(faixa[0])),
                "faixa_max": None if faixa[1] is None else Decimal(str(faixa[1])),
                "sugerido": Decimal(str(sugerido)),
                "confianca": item.get("confianca"),
                "fonte_id": fonte_id or "pratica",
                "fonte_titulo": titulo or fonte_id,
                "fonte_url": url,
                "nota": item.get("nota"),
            }
        )
    if erros:
        raise ReferenciaInvalida(erros)
    return {"versao": versao, "linhas": linhas}


def _chave(tipo, formato, minimo, maximo) -> tuple:
    return (tipo, formato, None if minimo is None else Decimal(str(minimo)), None if maximo is None else Decimal(str(maximo)))


def carregar(db: Session, caminho: Path | str = CAMINHO_PADRAO) -> ResultadoCarga:
    """Idempotente. Nunca apaga referência que já está no banco."""
    lido = ler_referencia(caminho)
    resultado = ResultadoCarga(versao=lido["versao"])
    atuais = {
        _chave(r.tipo, r.formato, r.peso_min_g, r.peso_max_g): r
        for r in db.scalars(select(PerdaReferencia))
    }
    vistas = set()
    for linha in lido["linhas"]:
        chave = _chave(linha["tipo"], linha["formato"], linha["peso_min_g"], linha["peso_max_g"])
        vistas.add(chave)
        atual = atuais.get(chave)
        if atual is None:
            db.add(PerdaReferencia(**linha))
            resultado.inseridos += 1
            continue
        mudou = False
        for campo in ("faixa_min", "faixa_max", "sugerido", "confianca", "fonte_id", "fonte_titulo", "fonte_url", "nota"):
            novo = linha[campo]
            velho = getattr(atual, campo)
            if isinstance(novo, Decimal) or isinstance(velho, Decimal):
                if _d(velho) != _d(novo):
                    setattr(atual, campo, novo)
                    mudou = True
            elif velho != novo:
                setattr(atual, campo, novo)
                mudou = True
        if mudou:
            resultado.alterados += 1
        else:
            resultado.iguais += 1
    resultado.fora_do_arquivo = len([chave for chave in atuais if chave not in vistas])
    db.flush()
    return resultado
