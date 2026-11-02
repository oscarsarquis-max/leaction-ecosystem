from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, exigir
from app.domain.auth import Principal
from app.models.usuarios import Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioOut(BaseModel):
    id: UUID
    usuario: str
    nome: str
    papel: str
    ativo: bool


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(
    db: DbSession,
    _principal: Annotated[Principal, Depends(exigir("gerenciar_usuarios"))],
) -> list[UsuarioOut]:
    """Só o dono vê quem tem acesso. Nunca devolve hash de senha."""
    linhas = db.scalars(select(Usuario).order_by(Usuario.usuario)).all()
    return [
        UsuarioOut(id=u.id, usuario=u.usuario, nome=u.nome, papel=u.papel, ativo=u.ativo)
        for u in linhas
    ]
