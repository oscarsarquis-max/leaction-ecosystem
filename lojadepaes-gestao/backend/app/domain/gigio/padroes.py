"""Padrões da padaria. As sementes nascem com a organização; o Oscar edita."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ErroDeDominio
from app.models.estoque import Ingrediente
from app.models.gigio import PadraoPadaria

SEMENTES: tuple[tuple[str, str, str, str, int], ...] = (
    ("Hidratação", "água", "60", "Água da massa, sobre a farinha.", 1),
    (
        "Água residual do fermento",
        "água residual do fermento",
        "6",
        "Cerca de 30 g para 500 g de farinha, além da hidratação.",
        2,
    ),
    ("Leite em pó ou farinha láctea", "leite em pó", "10", "Ou farinha láctea.", 3),
    ("Levain", "levain", "20", "Fermento natural.", 4),
    ("PFF", "PFF", "20", "Prefermento.", 5),
)


def semear(db: Session, organizacao_id: UUID) -> None:
    nomes = {p.nome for p in db.scalars(select(PadraoPadaria).where(PadraoPadaria.organizacao_id == organizacao_id))}
    for nome, termo, percentual, observacao, ordem in SEMENTES:
        if nome in nomes:
            continue
        db.add(
            PadraoPadaria(
                organizacao_id=organizacao_id,
                nome=nome,
                termo=termo,
                percentual=Decimal(percentual),
                observacao=observacao,
                ativo=True,
                ordem=ordem,
            )
        )
    db.flush()


def listar(db: Session, organizacao_id: UUID) -> list[dict]:
    semear(db, organizacao_id)
    linhas = db.scalars(select(PadraoPadaria).order_by(PadraoPadaria.ordem, PadraoPadaria.nome))
    return [_linha(db, p) for p in linhas]


def criar(db: Session, organizacao_id: UUID, dados: dict) -> dict:
    padrao = PadraoPadaria(organizacao_id=organizacao_id, ordem=99, ativo=True)
    _aplicar(db, padrao, dados)
    db.add(padrao)
    db.flush()
    return _linha(db, padrao)


def alterar(db: Session, padrao_id: UUID, dados: dict) -> dict:
    padrao = db.get(PadraoPadaria, padrao_id)
    if padrao is None:
        raise ErroDeDominio("padrao_inexistente", "Esse padrão não existe.", status=404)
    _aplicar(db, padrao, dados)
    db.flush()
    return _linha(db, padrao)


def ativos(db: Session, organizacao_id: UUID) -> list[PadraoPadaria]:
    semear(db, organizacao_id)
    return list(
        db.scalars(
            select(PadraoPadaria).where(PadraoPadaria.ativo.is_(True)).order_by(PadraoPadaria.ordem)
        )
    )


def _aplicar(db: Session, padrao: PadraoPadaria, dados: dict) -> None:
    nome = (dados.get("nome") or "").strip()
    termo = (dados.get("termo") or "").strip()
    if not nome:
        raise ErroDeDominio("nome_vazio", "Dê um nome ao padrão.")
    if not termo and not dados.get("ingrediente_id"):
        raise ErroDeDominio("termo_vazio", "Escolha um ingrediente ou escreva um termo.")
    percentual = Decimal(str(dados.get("percentual")))
    if percentual < 0:
        raise ErroDeDominio("percentual_invalido", "A porcentagem não pode ser negativa.")
    ingrediente_id = dados.get("ingrediente_id")
    if ingrediente_id:
        ing = db.get(Ingrediente, ingrediente_id)
        if ing is None or not ing.ativo:
            raise ErroDeDominio("ingrediente_inexistente", "O ingrediente desse padrão não existe.")
        if not termo:
            termo = ing.nome
        padrao.ingrediente_id = ing.id
    else:
        padrao.ingrediente_id = None
    padrao.nome = nome[:80]
    padrao.termo = termo[:80]
    padrao.percentual = percentual
    padrao.observacao = (dados.get("observacao") or "").strip() or None
    if "ativo" in dados and dados["ativo"] is not None:
        padrao.ativo = bool(dados["ativo"])


def _linha(db: Session, padrao: PadraoPadaria) -> dict:
    ing = db.get(Ingrediente, padrao.ingrediente_id) if padrao.ingrediente_id else None
    return {
        "id": str(padrao.id),
        "nome": padrao.nome,
        "termo": padrao.termo,
        "ingrediente_id": str(padrao.ingrediente_id) if padrao.ingrediente_id else None,
        "ingrediente": ing.nome if ing else None,
        "percentual": float(padrao.percentual),
        "observacao": padrao.observacao,
        "ativo": padrao.ativo,
    }
