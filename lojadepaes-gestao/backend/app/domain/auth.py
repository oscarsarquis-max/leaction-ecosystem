from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import AuthDisabledError, AuthError, RateLimitError
from app.models.usuarios import Sessao, TentativaLogin, Usuario

COOKIE_SESSAO = "gestao_session"
CABECALHO_CSRF = "X-CSRF-Token"
SENHA_MINIMA = 12
_hasher = PasswordHasher()


def agora() -> datetime:
    return datetime.now(UTC)


def normalizar_usuario(valor: str) -> str:
    return valor.strip().lower()[:80]


def digest(secret: str, valor: str) -> str:
    return hmac.new(secret.encode("utf-8"), valor.encode("utf-8"), hashlib.sha256).hexdigest()


def gerar_hash_senha(senha: str) -> str:
    if len(senha) < SENHA_MINIMA:
        raise ValueError(f"a senha precisa ter pelo menos {SENHA_MINIMA} caracteres")
    if len(senha) > 200:
        raise ValueError("a senha é longa demais (máximo de 200 caracteres)")
    return _hasher.hash(senha)


def _conferir_senha(senha_hash: str, senha: str) -> bool:
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@lru_cache(maxsize=1)
def _hash_falso() -> str:
    # Mesma ordem de custo de um hash real, para não revelar por tempo se o usuário existe.
    return _hasher.hash("gestao-hash-falso-nao-e-senha")


def registrar_tentativa(db: Session, *, usuario: str, cliente: str, sucesso: bool) -> None:
    db.add(TentativaLogin(usuario=usuario[:80], cliente=cliente, sucesso=sucesso))


def conferir_limite(db: Session, settings: Settings, usuario: str, cliente: str) -> None:
    janela = agora() - timedelta(minutes=settings.login_window_minutes)
    falhas = db.scalar(
        select(func.count())
        .select_from(TentativaLogin)
        .where(
            TentativaLogin.usuario == usuario[:80],
            TentativaLogin.cliente == cliente,
            TentativaLogin.sucesso.is_(False),
            TentativaLogin.criada_em >= janela,
        )
    )
    if int(falhas or 0) >= settings.login_max_failures:
        raise RateLimitError("muitas tentativas; aguarde alguns minutos")


def _emitir_sessao(
    db: Session, settings: Settings, usuario: Usuario, cliente: str
) -> tuple[str, str, Sessao]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    agora_ = agora()
    sessao = Sessao(
        token_hash=digest(settings.session_secret, token),
        csrf_hash=digest(settings.session_secret, csrf),
        usuario_id=usuario.id,
        expira_em=agora_ + timedelta(hours=settings.session_ttl_hours),
        ultimo_uso_em=agora_,
        cliente=cliente,
    )
    db.add(sessao)
    usuario.ultimo_acesso_em = agora_
    registrar_tentativa(db, usuario=usuario.usuario, cliente=cliente, sucesso=True)
    db.flush()
    return token, csrf, sessao


def entrar(
    db: Session, settings: Settings, *, usuario: str, senha: str, cliente: str
) -> tuple[str, str, Usuario]:
    if not settings.session_ready:
        raise AuthDisabledError("o acesso está desabilitado: falta configurar o segredo de sessão")
    nome = normalizar_usuario(usuario)
    conferir_limite(db, settings, nome, cliente)
    registro = db.scalar(select(Usuario).where(Usuario.usuario == nome))
    existe = registro is not None and registro.ativo
    senha_ok = _conferir_senha(registro.senha_hash if existe and registro else _hash_falso(), senha)
    if not existe or not senha_ok or registro is None:
        registrar_tentativa(db, usuario=nome, cliente=cliente, sucesso=False)
        db.flush()
        raise AuthError("usuário ou senha inválidos")
    token, csrf, _sessao = _emitir_sessao(db, settings, registro, cliente)
    return token, csrf, registro


@dataclass(frozen=True)
class Principal:
    usuario_id: object
    usuario: str
    nome: str
    papel: str
    csrf: str


def carregar_sessao(
    db: Session,
    settings: Settings,
    token: str | None,
    *,
    rotacionar_csrf: bool = False,
) -> tuple[Principal, Sessao] | None:
    if not settings.session_ready or not token:
        return None
    token_hash = digest(settings.session_secret, token)
    consulta = select(Sessao, Usuario).join(Usuario, Usuario.id == Sessao.usuario_id).where(
        Sessao.token_hash == token_hash
    )
    if rotacionar_csrf:
        consulta = consulta.with_for_update(of=Sessao)
    linha = db.execute(consulta).first()
    if linha is None:
        return None
    sessao, usuario = linha
    agora_ = agora()
    if sessao.revogada_em is not None or sessao.expira_em <= agora_ or not usuario.ativo:
        return None
    csrf = ""
    if rotacionar_csrf:
        csrf = secrets.token_urlsafe(32)
        sessao.csrf_hash = digest(settings.session_secret, csrf)
    sessao.ultimo_uso_em = agora_
    db.flush()
    principal = Principal(
        usuario_id=usuario.id,
        usuario=usuario.usuario,
        nome=usuario.nome,
        papel=usuario.papel,
        csrf=csrf,
    )
    return principal, sessao


def csrf_valido(settings: Settings, sessao: Sessao, apresentado: str | None) -> bool:
    if not apresentado:
        return False
    return hmac.compare_digest(sessao.csrf_hash, digest(settings.session_secret, apresentado))


def revogar(db: Session, sessao: Sessao) -> None:
    if sessao.revogada_em is None:
        sessao.revogada_em = agora()
        db.flush()
