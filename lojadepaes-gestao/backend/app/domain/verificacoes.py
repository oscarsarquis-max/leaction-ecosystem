"""Conta e salvaguardas da padaria. O modelo sugere o %; o servidor faz a conta."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

import yaml

from app.domain.normalizacao import normalizar

_CEM = Decimal(100)
_GRAMA = Decimal("1")
_DECIMO = Decimal("0.1")
_SAL_MIN = Decimal("1.5")
_SAL_MAX = Decimal("2.5")


def _q(valor: Decimal, passo: Decimal) -> Decimal:
    return valor.quantize(passo, rounding=ROUND_HALF_UP)


def _d(valor) -> Decimal | None:
    if valor is None or valor == "":
        return None
    return Decimal(str(valor))


def percentual_dos_gramas(gramas, farinha) -> Decimal | None:
    """O % que se mostra. 390 g de água em 625 g de farinha são 62,4 %, não o % que o modelo afirmou."""
    massa = _d(gramas)
    base = _d(farinha)
    if massa is None or base is None or base <= 0:
        return None
    return _q(massa / base * _CEM, _DECIMO)


def gramas_do_percentual(percentual, farinha) -> Decimal:
    pct = _d(percentual) or Decimal(0)
    base = _d(farinha) or Decimal(0)
    return _q(pct * base / _CEM, _GRAMA)


def apertar_faixa(percentual: Decimal, minima, maxima) -> tuple[Decimal, str | None]:
    piso = _d(minima)
    teto = _d(maxima)
    if piso is not None and percentual < piso:
        return piso, f"O { _txt(percentual) } % ficou abaixo da faixa. Usei { _txt(piso) } %."
    if teto is not None and percentual > teto:
        return teto, f"O { _txt(percentual) } % passou da faixa. Usei { _txt(teto) } %."
    return percentual, None


def _txt(valor: Decimal) -> str:
    return f"{valor:f}".rstrip("0").rstrip(".").replace(".", ",")


def e_farinha(nome: str | None, categoria: str | None) -> bool:
    if categoria == "Farinhas":
        return True
    n = normalizar(nome or "")
    if "leite" in n or "lactea" in n or "lacteo" in n:
        return False
    return "farinha" in n or "semola" in n or "semolina" in n


def e_agua(nome: str | None, categoria: str | None = None) -> bool:
    n = normalizar(nome or "")
    if "residual" in n:
        return False
    return n == "agua" or n.startswith("agua ")


def e_sal(nome: str | None, categoria: str | None = None) -> bool:
    n = normalizar(nome or "")
    return n == "sal" or n.startswith("sal ")


def e_fermento(nome: str | None, categoria: str | None = None) -> bool:
    if categoria == "Fermentos":
        return True
    n = normalizar(nome or "")
    return any(termo in n for termo in ("fermento", "levain", "pff", "ferment"))


def essencial(nome: str | None) -> bool:
    n = normalizar(nome or "")
    return e_fermento(n) or e_sal(n) or "levain" in n or n == "pff"


def na_descricao(nome: str | None, descricao: str | None) -> bool:
    texto = normalizar(descricao or "")
    palavras = [p for p in normalizar(nome or "").split() if len(p) > 3]
    return any(p in texto for p in palavras)


def pede_fermento_natural(descricao: str | None) -> bool:
    texto = normalizar(descricao or "")
    return "longa maturacao" in texto or "fermentacao natural" in texto


def calibrar_confianca(confianca: str | None, *, fixa: bool, padrao: bool, descrita: bool) -> str:
    """Alta só na linha fixa ou no padrão da casa. O resto desce."""
    if fixa or padrao:
        return "alta"
    if not descrita:
        return "baixa"
    if confianca == "baixa":
        return "baixa"
    return "media"


def casa_com_padrao(nome: str | None, motivo: str | None, percentual, padroes) -> bool:
    n = normalizar(nome or "")
    for padrao in padroes or []:
        termo = normalizar(getattr(padrao, "termo", None) or padrao.get("termo") or "")
        if not termo or termo not in n:
            continue
        alvo = _d(getattr(padrao, "percentual", None) if not isinstance(padrao, dict) else padrao.get("percentual"))
        atual = _d(percentual)
        if alvo is not None and atual is not None and abs(atual - alvo) <= Decimal("0.5"):
            return True
    return False


def aplicar_substituicao(folhas: list[dict], nome: str, percentual) -> list[dict]:
    """Troca uma parte da farinha da base. A farinha total não muda."""
    pct = _d(percentual) or Decimal(0)
    if pct <= 0:
        return [dict(f) for f in folhas]
    indices = [i for i, f in enumerate(folhas) if e_farinha(f.get("nome"), f.get("categoria"))]
    if not indices:
        return [dict(f) for f in folhas]
    total = sum(Decimal(str(folhas[i]["quantidade_g"])) for i in indices)
    troca = gramas_do_percentual(pct, total)
    maior = max(indices, key=lambda i: Decimal(str(folhas[i]["quantidade_g"])))
    atual = Decimal(str(folhas[maior]["quantidade_g"]))
    if troca > atual:
        troca = _q(atual, _GRAMA)
    saida = []
    for i, folha in enumerate(folhas):
        copia = dict(folha)
        if i == maior:
            copia["quantidade_g"] = atual - troca
        saida.append(copia)
    saida.append(
        {
            "nome": nome,
            "categoria": "Farinhas",
            "quantidade_g": troca,
            "ingrediente_id": None,
        }
    )
    return saida


@lru_cache(maxsize=1)
def _faixas() -> tuple[dict, ...]:
    caminho = Path(__file__).with_name("faixas_familia.yaml")
    bruto = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return tuple(bruto.get("familias") or [])


def faixa_da_familia(familia: str | None) -> dict | None:
    texto = normalizar(familia or "")
    if not texto:
        return None
    for faixa in _faixas():
        if any(normalizar(termo) in texto for termo in faixa.get("termos") or []):
            return faixa
    return None


def _gramas(linha: dict) -> Decimal:
    if linha.get("quantidade_g") is not None:
        return Decimal(str(linha["quantidade_g"]))
    return Decimal(str(linha.get("quantidade") or 0))


def verificar(linhas: list[dict], *, farinha, familia: str | None, componentes: list[dict] | None = None) -> dict:
    """Pendências e avisos da sugestão ou da receita. Não grava nada."""
    componentes = componentes or []
    base = _d(farinha) or Decimal(0)
    folhas = []
    for componente in componentes:
        for folha in componente.get("folhas") or []:
            folhas.append({**folha, "componente": componente.get("nome")})
    pendencias = []
    avisos = []
    tem_fermento = any(
        e_fermento(linha.get("nome"), linha.get("categoria")) for linha in linhas if not linha.get("componente")
    )
    tem_fermento = tem_fermento or any(e_fermento(folha.get("nome"), folha.get("categoria")) for folha in folhas)
    if not tem_fermento:
        pendencias.append({"codigo": "sem_fermento", "mensagem": "Falta o fermento."})

    sal = sum(
        (_gramas(linha) for linha in linhas if not linha.get("componente") and e_sal(linha.get("nome"), linha.get("categoria"))),
        Decimal(0),
    )
    sal += sum((_gramas(folha) for folha in folhas if e_sal(folha.get("nome"), folha.get("categoria"))), Decimal(0))
    if base > 0 and sal > 0:
        pct = percentual_dos_gramas(sal, base)
        if pct is not None and (pct < _SAL_MIN or pct > _SAL_MAX):
            avisos.append(
                {
                    "codigo": "sal",
                    "mensagem": f"O sal está em {_txt(pct)} % da farinha. A faixa usual é 1,5–2,5 %.",
                }
            )

    agua = sum((_gramas(linha) for linha in linhas if not linha.get("componente") and e_agua(linha.get("nome"))), Decimal(0))
    agua += sum((_gramas(folha) for folha in folhas if e_agua(folha.get("nome"))), Decimal(0))
    faixa = faixa_da_familia(familia)
    if base > 0 and agua > 0 and faixa is not None:
        pct = percentual_dos_gramas(agua, base)
        piso = Decimal(str(faixa["hidratacao_min"]))
        teto = Decimal(str(faixa["hidratacao_max"]))
        if pct is not None and (pct < piso or pct > teto):
            avisos.append(
                {
                    "codigo": "hidratacao",
                    "mensagem": (
                        f"A hidratação está em {_txt(pct)} %, fora da faixa da {faixa['nome']} "
                        f"({_txt(piso)}–{_txt(teto)} %)."
                    ),
                }
            )

    for linha in linhas:
        if linha.get("componente") or not linha.get("nome"):
            continue
        for folha in folhas:
            if normalizar(linha["nome"]) == normalizar(folha.get("nome") or ""):
                avisos.append(
                    {
                        "codigo": "repetido",
                        "mensagem": f"{linha['nome']} já está na {folha['componente']}. Somar mesmo assim?",
                    }
                )
                break
    return {"pendencias": pendencias, "avisos": avisos, "tem_fermento": tem_fermento}
