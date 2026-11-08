"""GESTAO-014A: a foto enviada fica no banco e vence a URL da Loja."""

import io
from uuid import UUID

import pytest
from app.db.session import get_engine
from app.main import create_app
from app.models.produtos import Produto
from fastapi.testclient import TestClient
from PIL import Image
from pillow_heif import register_heif_opener
from sqlalchemy.orm import Session

from tests.conftest import entrar
from tests.test_estoque import Api

register_heif_opener()


@pytest.fixture()
def api(client):
    return Api(client, entrar(client, "padeiro-foto", "dono"))


@pytest.fixture()
def duas_orgs(client):
    dona = Api(client, entrar(client, "dona-foto", "dono", org="org-foto-a"))
    with TestClient(create_app(), base_url="http://testserver") as outro:
        yield dona, Api(outro, entrar(outro, "dono-foto-b", "dono", org="org-foto-b", fonte_loja=False))


def _produto(api, **extra):
    corpo = {
        "nome": "Bolo de chocolate",
        "modalidade": "produzido",
        "uso_venda": True,
        "uso_componente": False,
        "unidade_venda": "un",
    }
    corpo.update(extra)
    return api.post("/produtos", corpo)


def _jpeg_grande() -> bytes:
    base = Image.linear_gradient("L").resize((4000, 3000))
    imagem = Image.merge(
        "RGB",
        (base, base.transpose(Image.Transpose.FLIP_LEFT_RIGHT), base),
    )
    exif = imagem.getexif()
    exif[305] = "GESTAO-FOTO-EXIF"
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85, exif=exif)
    return saida.getvalue()


def _heic() -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", (80, 60), (12, 40, 80)).save(saida, format="HEIF")
    return saida.getvalue()


def _enviar(api, produto_id: str, nome: str, conteudo: bytes, tipo: str):
    return api.c.post(
        f"/api/v1/produtos/{produto_id}/foto",
        files={"arquivo": (nome, conteudo, tipo)},
        headers=api.h,
    )


def test_foto_grande_vira_webp_sem_exif(api):
    produto = _produto(api, nome="Levain").json()["id"]
    bruto = _jpeg_grande()
    assert b"GESTAO-FOTO-EXIF" in bruto
    enviado = _enviar(api, produto, "grande.jpg", bruto, "image/jpeg")
    assert enviado.status_code == 200, enviado.text
    assert enviado.json()["tem_foto"] is True

    foto = api.get(f"/produtos/{produto}/foto")
    assert foto.status_code == 200
    assert foto.headers["content-type"].startswith("image/webp")
    assert len(foto.content) < 250_000
    assert b"GESTAO-FOTO-EXIF" not in foto.content
    aberta = Image.open(io.BytesIO(foto.content))
    assert aberta.size == (1200, 900)
    assert 305 not in aberta.getexif()

    de_novo = api.c.get(
        f"/api/v1/produtos/{produto}/foto",
        headers={"If-None-Match": foto.headers["etag"]},
    )
    assert de_novo.status_code == 304

    mini = Image.open(io.BytesIO(api.get(f"/produtos/{produto}/foto/mini").content))
    assert max(mini.size) == 96


def test_heic_entra_e_arquivo_grande_ou_pdf_nao(api):
    produto = _produto(api, nome="Pão de forma").json()["id"]
    heic = _enviar(api, produto, "celular.heic", _heic(), "image/heic")
    assert heic.status_code == 200, heic.text
    assert heic.json()["tem_foto"] is True

    onze = b"\xff\xd8\xff" + b"0" * (11 * 1024 * 1024)
    grande = _enviar(api, produto, "grande.jpg", onze, "image/jpeg")
    assert grande.status_code == 413
    assert grande.json()["detail"]["mensagem"] == "Arquivo maior que 10 MB"

    pdf = _enviar(api, produto, "nota.pdf", b"%PDF-1.4\n1 0 obj\n", "application/pdf")
    assert pdf.status_code == 415
    assert pdf.json()["detail"]["mensagem"] == "Formato não aceito"


def test_enviada_vence_a_loja_e_remover_volta(api):
    produto_id = _produto(api, nome="Focaccia").json()["id"]
    with Session(get_engine()) as sessao:
        produto = sessao.get(Produto, UUID(produto_id))
        assert produto is not None
        produto.foto_url = "https://lojadepaes.com.br/api/v1/catalog/media/focaccia"
        sessao.commit()

    antes = api.get(f"/produtos/{produto_id}").json()
    assert antes["tem_foto"] is False
    assert antes["foto_url"].endswith("/focaccia")

    enviado = _enviar(api, produto_id, "forno.jpg", _jpeg_grande(), "image/jpeg")
    assert enviado.status_code == 200, enviado.text
    assert enviado.json()["tem_foto"] is True
    assert enviado.json()["foto_url"].endswith("/focaccia")
    assert api.get(f"/produtos/{produto_id}/foto").headers["content-type"].startswith("image/webp")

    apagou = api.c.delete(f"/api/v1/produtos/{produto_id}/foto", headers=api.h)
    assert apagou.status_code == 200, apagou.text
    assert apagou.json()["tem_foto"] is False
    assert apagou.json()["foto_url"].endswith("/focaccia")
    assert api.get(f"/produtos/{produto_id}/foto").status_code == 404


def test_outra_organizacao_nao_le_a_foto(duas_orgs):
    dona, outra = duas_orgs
    produto = _produto(dona, nome="Brioche").json()["id"]
    assert _enviar(dona, produto, "brioche.jpg", _jpeg_grande(), "image/jpeg").status_code == 200
    assert outra.get(f"/produtos/{produto}/foto").status_code == 404
    assert outra.get(f"/produtos/{produto}/foto/mini").status_code == 404
