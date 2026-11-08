"""Foto do produto gravada no banco.

A entrada aceita JPG, PNG, WEBP e HEIC até 10 MB. O que fica guardado é WEBP,
no máximo 1200 px no lado maior, sem EXIF, e uma miniatura de 96 px.
A foto enviada vence a URL da Loja. Apagar a enviada devolve a da Loja.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from uuid import UUID

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import ErroDeDominio
from app.models.produtos import Produto, ProdutoFoto

register_heif_opener()

LIMITE_ENTRADA = 10 * 1024 * 1024
LADO_MAXIMO = 1200
LADO_MINI = 96
TETO_BYTES = 250_000
QUALIDADE = 80
FORMATOS = {"JPEG", "PNG", "WEBP", "HEIF"}

_GRANDE = "Arquivo maior que 10 MB"
_FORMATO = "Formato não aceito"


def preparar(bruto: bytes) -> tuple[bytes, int, int, bytes, int, int]:
    """Devolve a foto e a miniatura, já em WEBP, com largura e altura de cada uma."""
    if len(bruto) > LIMITE_ENTRADA:
        raise ErroDeDominio("arquivo_grande", _GRANDE, status=413)
    if bruto.startswith(b"%PDF"):
        raise ErroDeDominio("formato_recusado", _FORMATO, status=415)
    try:
        imagem = Image.open(io.BytesIO(bruto))
        imagem.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ErroDeDominio("formato_recusado", _FORMATO, status=415) from exc
    if (imagem.format or "").upper() not in FORMATOS:
        raise ErroDeDominio("formato_recusado", _FORMATO, status=415)
    limpa = _sem_metadados(imagem)
    limpa.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)
    cheia = _webp_ate(limpa, TETO_BYTES)
    mini = limpa.copy()
    mini.thumbnail((LADO_MINI, LADO_MINI), Image.Resampling.LANCZOS)
    mini_bytes = _webp(mini, QUALIDADE)
    return cheia, limpa.width, limpa.height, mini_bytes, mini.width, mini.height


def gravar(ctx, produto_id: UUID, bruto: bytes) -> dict:
    produto = _produto(ctx.db, produto_id)
    cheia, largura, altura, mini, mini_l, mini_a = preparar(bruto)
    agora = datetime.now(UTC)
    atual = ctx.db.scalar(select(ProdutoFoto).where(ProdutoFoto.produto_id == produto.id))
    if atual is None:
        atual = ProdutoFoto(
            organizacao_id=ctx.org_id,
            produto_id=produto.id,
            tipo="image/webp",
            largura=largura,
            altura=altura,
            bytes=len(cheia),
            conteudo=cheia,
            mini_largura=mini_l,
            mini_altura=mini_a,
            mini_bytes=len(mini),
            mini_conteudo=mini,
            enviado_por=ctx.principal.nome[:120],
            enviado_em=agora,
        )
        ctx.db.add(atual)
    else:
        atual.tipo = "image/webp"
        atual.largura = largura
        atual.altura = altura
        atual.bytes = len(cheia)
        atual.conteudo = cheia
        atual.mini_largura = mini_l
        atual.mini_altura = mini_a
        atual.mini_bytes = len(mini)
        atual.mini_conteudo = mini
        atual.enviado_por = ctx.principal.nome[:120]
        atual.enviado_em = agora
    ctx.db.flush()
    from app.domain.produtos import detalhe_produto

    return detalhe_produto(ctx.db, produto.id)


def apagar(ctx, produto_id: UUID) -> dict:
    produto = _produto(ctx.db, produto_id)
    atual = ctx.db.scalar(select(ProdutoFoto).where(ProdutoFoto.produto_id == produto.id))
    if atual is None:
        raise ErroDeDominio("foto_inexistente", "Este produto não tem foto enviada.", status=404)
    ctx.db.delete(atual)
    ctx.db.flush()
    from app.domain.produtos import detalhe_produto

    return detalhe_produto(ctx.db, produto.id)


def ler(db: Session, produto_id: UUID, *, mini: bool) -> tuple[bytes, str]:
    """Bytes da foto e o ETag. 404 se o produto não é desta organização ou não tem foto enviada."""
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    atual = db.scalar(select(ProdutoFoto).where(ProdutoFoto.produto_id == produto.id))
    if atual is None:
        raise ErroDeDominio("foto_inexistente", "Este produto não tem foto enviada.", status=404)
    conteudo = atual.mini_conteudo if mini else atual.conteudo
    marca = f'"{produto_id.hex}-{int(atual.enviado_em.timestamp())}-{len(conteudo)}"'
    return conteudo, marca


def quando_por_produto(db: Session) -> dict[UUID, datetime]:
    linhas = db.execute(select(ProdutoFoto.produto_id, ProdutoFoto.enviado_em)).all()
    return {produto_id: enviado for produto_id, enviado in linhas}


def _produto(db: Session, produto_id: UUID) -> Produto:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise ErroDeDominio("produto_inexistente", "Esse produto não existe.", status=404)
    return produto


def _sem_metadados(imagem: Image.Image) -> Image.Image:
    girada = ImageOps.exif_transpose(imagem) or imagem
    if girada.mode == "P":
        girada = girada.convert("RGBA" if "transparency" in girada.info else "RGB")
    if girada.mode not in ("RGB", "RGBA"):
        girada = girada.convert("RGB")
    limpa = Image.new(girada.mode, girada.size)
    limpa.paste(girada)
    return limpa


def _webp(imagem: Image.Image, qualidade: int) -> bytes:
    saida = io.BytesIO()
    imagem.save(saida, format="WEBP", quality=qualidade, method=6)
    return saida.getvalue()


def _webp_ate(imagem: Image.Image, teto: int) -> bytes:
    qualidade = QUALIDADE
    cheia = _webp(imagem, qualidade)
    while len(cheia) >= teto and qualidade > 50:
        qualidade -= 5
        cheia = _webp(imagem, qualidade)
    return cheia
