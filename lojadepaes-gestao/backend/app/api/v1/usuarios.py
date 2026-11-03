"""Usuários da organização (Gestão › Usuários). Só o dono vê e altera. Nunca devolve hash de senha."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import erro, exigir
from app.domain.auth import gerar_hash_senha, normalizar_usuario
from app.domain.contexto import Contexto
from app.models.organizacao import Membro
from app.models.usuarios import Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

Dono = Annotated[Contexto, Depends(exigir("gerenciar_usuarios"))]
Papel = Literal["dono", "operador", "somente_leitura"]


class MembroOut(BaseModel):
    id: UUID  # id do vínculo (membro), não do usuário
    usuario: str
    nome: str
    papel: str
    ativo: bool
    email_contato: str | None
    voce: bool


class NovoMembroIn(BaseModel):
    usuario: str = Field(min_length=3, max_length=80)
    nome: str = Field(min_length=1, max_length=120)
    papel: Papel
    senha: str = Field(min_length=1, max_length=200)
    email_contato: str | None = Field(default=None, max_length=200)


class MembroPatch(BaseModel):
    papel: Papel | None = None
    ativo: bool | None = None


def _saida(m: Membro, u: Usuario, ctx: Contexto) -> MembroOut:
    return MembroOut(
        id=m.id,
        usuario=u.usuario,
        nome=u.nome,
        papel=m.papel,
        ativo=m.ativo and u.ativo,
        email_contato=u.email_contato,
        voce=u.id == ctx.principal.usuario_id,
    )


def _donos_ativos(ctx: Contexto) -> int:
    return int(
        ctx.db.scalar(
            select(func.count())
            .select_from(Membro)
            .where(
                Membro.organizacao_id == ctx.org_id, Membro.papel == "dono", Membro.ativo.is_(True)
            )
        )
        or 0
    )


@router.get("", response_model=list[MembroOut])
def listar_membros(ctx: Dono) -> list[MembroOut]:
    linhas = ctx.db.execute(
        select(Membro, Usuario)
        .join(Usuario, Usuario.id == Membro.usuario_id)
        .where(Membro.organizacao_id == ctx.org_id)
        .order_by(Usuario.nome, Usuario.usuario)
    ).all()
    return [_saida(m, u, ctx) for m, u in linhas]


@router.post("", response_model=MembroOut, status_code=201)
def criar_membro(dados: NovoMembroIn, ctx: Dono) -> MembroOut:
    """Cria uma pessoa nova já vinculada a esta organização. Nenhuma mensagem é enviada a ninguém."""
    login = normalizar_usuario(dados.usuario)
    if ctx.db.scalar(select(Usuario).where(Usuario.usuario == login)) is not None:
        raise erro(
            409,
            "usuario_ja_existe",
            "Esse login já está em uso. Escolha outro; para vincular uma conta existente, fale com quem administra a plataforma.",
        )
    try:
        senha_hash = gerar_hash_senha(dados.senha)
    except ValueError as exc:
        raise erro(422, "senha_invalida", str(exc)) from None
    usuario = Usuario(
        usuario=login,
        nome=dados.nome.strip(),
        senha_hash=senha_hash,
        email_contato=(dados.email_contato or "").strip() or None,
    )
    ctx.db.add(usuario)
    ctx.db.flush()
    membro = Membro(usuario_id=usuario.id, organizacao_id=ctx.org_id, papel=dados.papel)
    ctx.db.add(membro)
    ctx.db.flush()
    return _saida(membro, usuario, ctx)


@router.patch("/{membro_id}", response_model=MembroOut)
def alterar_membro(membro_id: UUID, dados: MembroPatch, ctx: Dono) -> MembroOut:
    membro = ctx.db.scalar(
        select(Membro).where(Membro.id == membro_id, Membro.organizacao_id == ctx.org_id)
    )
    if membro is None:
        raise erro(404, "membro_inexistente", "Essa pessoa não faz parte desta organização.")
    novo_papel = dados.papel if dados.papel is not None else membro.papel
    novo_ativo = dados.ativo if dados.ativo is not None else membro.ativo
    perde_dono = (
        membro.papel == "dono" and membro.ativo and (novo_papel != "dono" or not novo_ativo)
    )
    if perde_dono and _donos_ativos(ctx) <= 1:
        raise erro(409, "ultimo_dono", "A organização precisa de pelo menos um dono ativo.")
    membro.papel, membro.ativo = novo_papel, novo_ativo
    ctx.db.flush()
    usuario = ctx.db.scalar(select(Usuario).where(Usuario.id == membro.usuario_id))
    assert usuario is not None
    return _saida(membro, usuario, ctx)
