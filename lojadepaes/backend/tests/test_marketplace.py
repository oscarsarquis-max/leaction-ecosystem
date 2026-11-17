"""Marketplace: regras, sessões separadas, fluxo de avaliação e chave desligada."""

import io
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.models.products import Product
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.admin_client import admin_client, login

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture
def market(db: Session) -> Session:
    db.execute(text("TRUNCATE marketplace.partners RESTART IDENTITY CASCADE"))
    db.commit()
    return db


def _ligar(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setenv("LOJADEPAES_MARKETPLACE_ENABLED", "true" if enabled else "false")
    get_settings.cache_clear()


def _csrf(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}


def _marca(email: str, slug: str, **extra) -> dict:
    body = {
        "partner_type": "producer",
        "brand_name": "Queijaria Serra",
        "brand_slug": slug,
        "city": "Fortaleza",
        "region": "Ceara",
        "highlight_hex": "#C4A35A",
        "document": "123",
        "contact": "contato@serra.test",
        "fee_cents": 250,
        "email": email,
        "story": "Coalhada de cabra",
    }
    body.update(extra)
    return body


def _produto(slug: str, **extra) -> dict:
    body = {
        "category": "queijos",
        "name": "Queijo coalho",
        "description": "Coalhada firme do sertao",
        "photos": ["https://exemplo.test/queijo.jpg"],
        "price_cents": 3200,
        "is_available": True,
        "delivery_cities": ["Fortaleza"],
        "delivery_districts": [],
        "delivery_cep_prefixes": [],
        "delivery_days": 2,
        "freight_cents": 900,
        "perishable": True,
        "pairings": [{"house_product_slug": slug, "reason": "acompanha o coalho"}],
    }
    body.update(extra)
    return body


def _pao(db: Session, status: str) -> str:
    slug = f"casa-{status}-{uuid4().hex[:8]}"
    db.add(
        Product(
            name="Pão da casa",
            slug=slug,
            short_description="crosta",
            editorial_status=status,
        )
    )
    db.commit()
    return slug


def _token(link: str) -> str:
    return link.split("token=", 1)[1]


def _criar(admin: TestClient, csrf: str, email: str, slug: str) -> dict:
    response = admin.post("/api/v1/admin/marketplace/partners", json=_marca(email, slug), headers=_csrf(csrf))
    assert response.status_code == 201, response.text
    return response.json()


def _aceitar(app, link: str) -> TestClient:
    partner = TestClient(app)
    response = partner.post(
        "/api/v1/partner/invite/accept",
        json={"token": _token(link), "password": "senha-segura"},
    )
    assert response.status_code == 200, response.text
    partner.csrf = response.json()["csrf_token"]  # type: ignore[attr-defined]
    return partner


def test_regras_recusam_categoria_pao_e_comissao(market: Session, admin_client: TestClient, monkeypatch):
    del market
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    alto = admin_client.post(
        "/api/v1/admin/marketplace/partners",
        json=_marca("alto@serra.test", "queijaria-alta", fee_cents=100001),
        headers=_csrf(csrf),
    )
    assert alto.status_code == 400
    created = _criar(admin_client, csrf, "ok@serra.test", "queijaria-ok")
    assert created["invite_link"].startswith("/parceiro/convite?token=")
    assert created["pay_recipient_id"] is None
    partner = _aceitar(admin_client.app, created["invite_link"])
    fora = partner.post(
        "/api/v1/partner/products",
        json=_produto("casa", category="batatas"),
        headers=_csrf(partner.csrf),
    )
    assert fora.status_code == 400
    pao = partner.post(
        "/api/v1/partner/products",
        json=_produto("casa", name="Focaccia de queijo"),
        headers=_csrf(partner.csrf),
    )
    assert pao.status_code == 400
    editado = admin_client.patch(
        f"/api/v1/admin/marketplace/partners/{created['id']}",
        json={"fee_cents": 400, "brand_name": "Queijaria da Serra"},
        headers=_csrf(csrf),
    )
    assert editado.status_code == 200
    assert editado.json()["fee_cents"] == 400
    pausa = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/pause",
        headers=_csrf(csrf),
    )
    assert pausa.status_code == 200
    assert pausa.json()["status"] == "paused"


def test_envio_exige_foto_e_pao_publicado(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    published = _pao(market, "published")
    draft = _pao(market, "draft")
    created = _criar(admin_client, csrf, f"envio-{uuid4().hex[:6]}@serra.test", f"envio-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    sem_foto = partner.post(
        "/api/v1/partner/products",
        json=_produto(published, photos=[]),
        headers=_csrf(partner.csrf),
    )
    assert sem_foto.status_code == 201, sem_foto.text
    recusa = partner.post(
        f"/api/v1/partner/products/{sem_foto.json()['id']}/submit",
        headers=_csrf(partner.csrf),
    )
    assert recusa.status_code == 400
    assert sem_foto.json()["status"] == "draft"
    falso = partner.post(
        "/api/v1/partner/products",
        json=_produto(draft),
        headers=_csrf(partner.csrf),
    )
    assert falso.status_code == 201, falso.text
    slug_ruim = partner.post(
        f"/api/v1/partner/products/{falso.json()['id']}/submit",
        headers=_csrf(partner.csrf),
    )
    assert slug_ruim.status_code == 400
    ajustado = partner.patch(
        f"/api/v1/partner/products/{falso.json()['id']}",
        json={"pairings": [{"house_product_slug": published, "reason": "acompanha o coalho"}]},
        headers=_csrf(partner.csrf),
    )
    assert ajustado.status_code == 200, ajustado.text
    enviado = partner.post(
        f"/api/v1/partner/products/{falso.json()['id']}/submit",
        headers=_csrf(partner.csrf),
    )
    assert enviado.status_code == 200, enviado.text
    assert enviado.json()["status"] == "pending"


def test_fluxo_avaliacao_e_edicao_volta_a_pendente(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    created = _criar(admin_client, csrf, f"fluxo-{uuid4().hex[:6]}@serra.test", f"fluxo-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    product = partner.post("/api/v1/partner/products", json=_produto(slug), headers=_csrf(partner.csrf))
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert product.json()["status"] == "draft"
    pending = partner.post(f"/api/v1/partner/products/{product_id}/submit", headers=_csrf(partner.csrf))
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "pending"
    fila = admin_client.get("/api/v1/admin/marketplace/products", params={"status": "pending"}, headers=_csrf(csrf))
    assert fila.status_code == 200
    assert product_id in {item["id"] for item in fila.json()}
    sem_nota = admin_client.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 4, "visual": 3, "complementarity": 5, "decision": "return", "note": ""},
        headers=_csrf(csrf),
    )
    assert sem_nota.status_code == 400
    devolvido = admin_client.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 4, "visual": 3, "complementarity": 5, "decision": "return", "note": "A foto está escura."},
        headers=_csrf(csrf),
    )
    assert devolvido.status_code == 200, devolvido.text
    assert devolvido.json()["status"] == "returned"
    avaliacoes = partner.get(f"/api/v1/partner/products/{product_id}/reviews", headers=_csrf(partner.csrf))
    assert avaliacoes.status_code == 200
    assert avaliacoes.json()[0]["decision"] == "return"
    de_novo = partner.post(f"/api/v1/partner/products/{product_id}/submit", headers=_csrf(partner.csrf))
    assert de_novo.status_code == 200, de_novo.text
    assert de_novo.json()["status"] == "pending"
    aprovado = admin_client.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 5, "visual": 5, "complementarity": 4, "decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert aprovado.status_code == 200, aprovado.text
    assert aprovado.json()["status"] == "approved"
    editado = partner.patch(
        f"/api/v1/partner/products/{product_id}",
        json={"name": "Queijo coalho curado"},
        headers=_csrf(partner.csrf),
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["status"] == "pending"
    assert editado.json()["name"] == "Queijo coalho curado"


def test_parceiro_nao_ve_o_outro(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    primeiro = _criar(admin_client, csrf, f"um-{uuid4().hex[:6]}@serra.test", f"um-{uuid4().hex[:6]}")
    segundo = _criar(admin_client, csrf, f"dois-{uuid4().hex[:6]}@serra.test", f"dois-{uuid4().hex[:6]}")
    dono = _aceitar(admin_client.app, primeiro["invite_link"])
    outro = _aceitar(admin_client.app, segundo["invite_link"])
    product = dono.post("/api/v1/partner/products", json=_produto(slug), headers=_csrf(dono.csrf))
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    leitura = outro.get(f"/api/v1/partner/products/{product_id}/reviews", headers=_csrf(outro.csrf))
    assert leitura.status_code == 404
    edicao = outro.patch(
        f"/api/v1/partner/products/{product_id}",
        json={"name": "Queijo alheio"},
        headers=_csrf(outro.csrf),
    )
    assert edicao.status_code == 404
    lista = outro.get("/api/v1/partner/products")
    assert product_id not in {item["id"] for item in lista.json()}


def test_sessoes_nao_se_misturam(market: Session, admin_client: TestClient, monkeypatch):
    del market
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    created = _criar(admin_client, csrf, f"sessao-{uuid4().hex[:6]}@serra.test", f"sessao-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    assert partner.get("/api/v1/partner/me").status_code == 200
    assert partner.get("/api/v1/admin/marketplace/partners").status_code == 401
    assert admin_client.get("/api/v1/partner/me").status_code == 401
    assert admin_client.get("/api/v1/admin/marketplace/partners", headers=_csrf(csrf)).status_code == 200

    partner_token = partner.cookies.get("lojadepaes_partner_session")
    admin_token = admin_client.cookies.get("lojadepaes_admin_session")
    assert partner_token and admin_token
    como_admin = TestClient(admin_client.app)
    como_admin.cookies.set("lojadepaes_admin_session", partner_token)
    assert como_admin.get("/api/v1/admin/marketplace/partners").status_code == 401
    como_parceiro = TestClient(admin_client.app)
    como_parceiro.cookies.set("lojadepaes_partner_session", admin_token)
    assert como_parceiro.get("/api/v1/partner/me").status_code == 401


def test_exclusividade_por_categoria_e_periodo(market: Session, admin_client: TestClient, monkeypatch):
    del market
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    primeiro = _criar(admin_client, csrf, f"ex1-{uuid4().hex[:6]}@serra.test", f"ex1-{uuid4().hex[:6]}")
    segundo = _criar(admin_client, csrf, f"ex2-{uuid4().hex[:6]}@serra.test", f"ex2-{uuid4().hex[:6]}")
    inicio = (date.today() - timedelta(days=10)).isoformat()
    aberto = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{primeiro['id']}/links",
        json={"category": "queijos", "link_type": "exclusive", "starts_on": inicio},
        headers=_csrf(csrf),
    )
    assert aberto.status_code == 201, aberto.text
    conflito = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{segundo['id']}/links",
        json={"category": "queijos", "link_type": "exclusive", "starts_on": date.today().isoformat()},
        headers=_csrf(csrf),
    )
    assert conflito.status_code == 409
    ontem = (date.today() - timedelta(days=1)).isoformat()
    fim = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{primeiro['id']}/links/{aberto.json()['id']}/end",
        json={"ends_on": ontem},
        headers=_csrf(csrf),
    )
    assert fim.status_code == 200, fim.text
    liberado = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{segundo['id']}/links",
        json={"category": "queijos", "link_type": "exclusive", "starts_on": date.today().isoformat()},
        headers=_csrf(csrf),
    )
    assert liberado.status_code == 201, liberado.text
    parcial = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{primeiro['id']}/links",
        json={"category": "vinhos", "link_type": "partial", "starts_on": date.today().isoformat()},
        headers=_csrf(csrf),
    )
    assert parcial.status_code == 201, parcial.text


def test_chave_desligada_responde_404(db: Session, admin_client: TestClient, monkeypatch):
    del db
    _ligar(monkeypatch, False)
    csrf = login(admin_client)
    parceiros = admin_client.get("/api/v1/admin/marketplace/partners", headers=_csrf(csrf))
    assert parceiros.status_code == 404
    login_parceiro = admin_client.post(
        "/api/v1/partner/login",
        json={"email": "a@b.co", "password": "senha-segura"},
    )
    assert login_parceiro.status_code == 404


def test_taxa_padrao_duzentos_e_cinquenta(market: Session, admin_client: TestClient, monkeypatch):
    del market
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    body = _marca(f"taxa-{uuid4().hex[:6]}@serra.test", f"taxa-{uuid4().hex[:6]}")
    del body["fee_cents"]
    criado = admin_client.post("/api/v1/admin/marketplace/partners", json=body, headers=_csrf(csrf))
    assert criado.status_code == 201, criado.text
    assert criado.json()["fee_cents"] == 250
    teto = admin_client.patch(
        f"/api/v1/admin/marketplace/partners/{criado.json()['id']}",
        json={"fee_cents": 100000},
        headers=_csrf(csrf),
    )
    assert teto.status_code == 200, teto.text
    assert teto.json()["fee_cents"] == 100000
    zero = admin_client.patch(
        f"/api/v1/admin/marketplace/partners/{criado.json()['id']}",
        json={"fee_cents": 0},
        headers=_csrf(csrf),
    )
    assert zero.status_code == 200, zero.text
    assert zero.json()["fee_cents"] == 0


def test_lista_de_parceiros_traz_os_vinculos(market: Session, admin_client: TestClient, monkeypatch):
    del market
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    created = _criar(admin_client, csrf, f"lista-{uuid4().hex[:6]}@serra.test", f"lista-{uuid4().hex[:6]}")
    inicio = date.today().isoformat()
    link = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/links",
        json={"category": "queijos", "link_type": "partial", "starts_on": inicio},
        headers=_csrf(csrf),
    )
    assert link.status_code == 201, link.text
    lista = admin_client.get("/api/v1/admin/marketplace/partners", headers=_csrf(csrf))
    assert lista.status_code == 200, lista.text
    row = next(item for item in lista.json() if item["id"] == created["id"])
    detalhe = admin_client.get(f"/api/v1/admin/marketplace/partners/{created['id']}", headers=_csrf(csrf))
    assert row["links"] == detalhe.json()["links"]
    assert row["links"][0]["category"] == "queijos"
    assert row["links"][0]["link_type"] == "partial"
    assert row["links"][0]["starts_on"] == inicio
    assert row["links"][0]["ends_on"] is None


def test_produto_traz_atualizacao_e_nome_do_pao(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    created = _criar(admin_client, csrf, f"nome-{uuid4().hex[:6]}@serra.test", f"nome-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    product = partner.post("/api/v1/partner/products", json=_produto(slug), headers=_csrf(partner.csrf))
    assert product.status_code == 201, product.text
    body = product.json()
    assert body["updated_at"]
    assert "T" in body["updated_at"]
    assert body["pairings"][0]["house_product_name"] == "Pão da casa"
    sem_nome = partner.post(
        "/api/v1/partner/products",
        json=_produto("pao-que-nao-existe"),
        headers=_csrf(partner.csrf),
    )
    assert sem_nome.status_code == 201, sem_nome.text
    assert sem_nome.json()["pairings"][0]["house_product_name"] is None


def test_admin_ve_avaliacoes_da_mais_recente(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    created = _criar(admin_client, csrf, f"rev-{uuid4().hex[:6]}@serra.test", f"rev-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    product = partner.post("/api/v1/partner/products", json=_produto(slug), headers=_csrf(partner.csrf))
    product_id = product.json()["id"]
    enviado = partner.post(f"/api/v1/partner/products/{product_id}/submit", headers=_csrf(partner.csrf))
    assert enviado.status_code == 200, enviado.text
    primeira = admin_client.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 3, "visual": 3, "complementarity": 3, "decision": "return", "note": "Foto escura."},
        headers=_csrf(csrf),
    )
    assert primeira.status_code == 200, primeira.text
    de_novo = partner.post(f"/api/v1/partner/products/{product_id}/submit", headers=_csrf(partner.csrf))
    assert de_novo.status_code == 200, de_novo.text
    segunda = admin_client.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 5, "visual": 5, "complementarity": 5, "decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert segunda.status_code == 200, segunda.text
    avaliacoes = admin_client.get(
        f"/api/v1/admin/marketplace/products/{product_id}/reviews",
        headers=_csrf(csrf),
    )
    assert avaliacoes.status_code == 200, avaliacoes.text
    decisoes = [item["decision"] for item in avaliacoes.json()]
    assert decisoes == ["approve", "return"]
    assert set(avaliacoes.json()[0]) == {
        "id",
        "quality",
        "visual",
        "complementarity",
        "note",
        "decision",
        "reviewer_ref",
        "reviewed_at",
    }
    ausente = admin_client.get(
        "/api/v1/admin/marketplace/products/00000000-0000-0000-0000-000000000000/reviews",
        headers=_csrf(csrf),
    )
    assert ausente.status_code == 404


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (48, 32), (200, 160, 80)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _pasta_de_midia(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LOJADEPAES_MEDIA_DIR", str(tmp_path))


def test_envio_de_foto_aceito(market: Session, admin_client: TestClient, monkeypatch, tmp_path):
    _pasta_de_midia(monkeypatch, tmp_path)
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    email = f"foto-{uuid4().hex[:6]}@serra.test"
    created = _criar(admin_client, csrf, email, f"foto-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    response = partner.post(
        "/api/v1/partner/media",
        files={"file": ("queijo.jpg", _jpeg(), "image/jpeg")},
        headers=_csrf(partner.csrf),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id", "url"}
    assert body["url"] == f"/api/v1/marketplace/media/{body['id']}"


def test_foto_recusada_por_formato_e_tamanho(market: Session, admin_client: TestClient, monkeypatch, tmp_path):
    _pasta_de_midia(monkeypatch, tmp_path)
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    created = _criar(admin_client, csrf, f"formato-{uuid4().hex[:6]}@serra.test", f"formato-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    formato = partner.post(
        "/api/v1/partner/media",
        files={"file": ("nota.txt", b"nao-e-imagem", "text/plain")},
        headers=_csrf(partner.csrf),
    )
    assert formato.status_code == 400
    assert formato.json()["detail"] == "envie JPEG, PNG ou WebP"
    monkeypatch.setenv("LOJADEPAES_MEDIA_MAX_BYTES", "20")
    get_settings.cache_clear()
    tamanho = partner.post(
        "/api/v1/partner/media",
        files={"file": ("queijo.jpg", _jpeg(), "image/jpeg")},
        headers=_csrf(partner.csrf),
    )
    assert tamanho.status_code == 400
    assert tamanho.json()["detail"] == "a imagem excede o limite de 8 MB"


def test_foto_de_outro_parceiro_recusada(market: Session, admin_client: TestClient, monkeypatch, tmp_path):
    _pasta_de_midia(monkeypatch, tmp_path)
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    published = _pao(market, "published")
    dono = _criar(admin_client, csrf, f"dono-{uuid4().hex[:6]}@serra.test", f"dono-{uuid4().hex[:6]}")
    outro = _criar(admin_client, csrf, f"outro-{uuid4().hex[:6]}@serra.test", f"outro-{uuid4().hex[:6]}")
    parceiro = _aceitar(admin_client.app, dono["invite_link"])
    alheio = _aceitar(admin_client.app, outro["invite_link"])
    enviada = parceiro.post(
        "/api/v1/partner/media",
        files={"file": ("queijo.jpg", _jpeg(), "image/jpeg")},
        headers=_csrf(parceiro.csrf),
    )
    assert enviada.status_code == 201, enviada.text
    recusa = alheio.post(
        "/api/v1/partner/products",
        json=_produto(published, photos=[enviada.json()["url"]]),
        headers=_csrf(alheio.csrf),
    )
    assert recusa.status_code == 400
    assert recusa.json()["detail"] == "a foto não pertence a este parceiro"
    propria = parceiro.post(
        "/api/v1/partner/products",
        json=_produto(published, photos=[enviada.json()["url"]]),
        headers=_csrf(parceiro.csrf),
    )
    assert propria.status_code == 201, propria.text
    assert propria.json()["photos"] == [enviada.json()["url"]]


def test_midia_servida_e_404_com_a_chave_desligada(
    market: Session, admin_client: TestClient, monkeypatch, tmp_path
):
    _pasta_de_midia(monkeypatch, tmp_path)
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    created = _criar(admin_client, csrf, f"serve-{uuid4().hex[:6]}@serra.test", f"serve-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    enviada = partner.post(
        "/api/v1/partner/media",
        files={"file": ("queijo.jpg", _jpeg(), "image/jpeg")},
        headers=_csrf(partner.csrf),
    )
    assert enviada.status_code == 201, enviada.text
    url = enviada.json()["url"]
    servida = admin_client.get(url)
    assert servida.status_code == 200
    assert servida.headers["content-type"].startswith("image/jpeg")
    assert servida.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert servida.content.startswith(b"\xff\xd8\xff")
    _ligar(monkeypatch, False)
    desligada = admin_client.get(url)
    assert desligada.status_code == 404
    assert desligada.json()["detail"] == "não encontrado"
    qualquer = admin_client.get("/api/v1/marketplace/media/11111111-1111-1111-1111-111111111111")
    assert qualquer.status_code == 404
    assert qualquer.json()["detail"] == "não encontrado"


def test_link_novo_de_acesso(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    email = f"acesso-{uuid4().hex[:6]}@serra.test"
    created = _criar(admin_client, csrf, email, f"acesso-{uuid4().hex[:6]}")
    _aceitar(admin_client.app, created["invite_link"])
    pausa = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/access-link",
        headers=_csrf(csrf),
    )
    admin_client.post(f"/api/v1/admin/marketplace/partners/{created['id']}/pause", headers=_csrf(csrf))
    pausado = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/access-link",
        headers=_csrf(csrf),
    )
    assert pausado.status_code == 409
    admin_client.post(f"/api/v1/admin/marketplace/partners/{created['id']}/activate", headers=_csrf(csrf))
    novo = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/access-link",
        headers=_csrf(csrf),
    )
    assert novo.status_code == 200, novo.text
    body = novo.json()
    assert set(body) == {"invite_link", "invite_expires_at", "email"}
    assert body["email"] == email
    assert body["invite_link"].startswith("/parceiro/convite?token=")
    assert body["invite_link"] != created["invite_link"]
    expires = datetime.fromisoformat(body["invite_expires_at"])
    assert timedelta(days=6, hours=23) < expires - datetime.now(UTC) < timedelta(days=7, hours=1)
    ainda = TestClient(admin_client.app)
    senha = ainda.post("/api/v1/partner/login", json={"email": email, "password": "senha-segura"})
    assert senha.status_code == 200, senha.text
    assert pausa.status_code == 200


def test_aceite_derruba_sessoes_antigas(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    email = f"sessao-{uuid4().hex[:6]}@serra.test"
    created = _criar(admin_client, csrf, email, f"sessao-{uuid4().hex[:6]}")
    primeira = _aceitar(admin_client.app, created["invite_link"])
    segunda = TestClient(admin_client.app)
    entrada = segunda.post("/api/v1/partner/login", json={"email": email, "password": "senha-segura"})
    assert entrada.status_code == 200, entrada.text
    novo = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/access-link",
        headers=_csrf(csrf),
    )
    assert novo.status_code == 200, novo.text
    ainda = TestClient(admin_client.app)
    segue = ainda.post("/api/v1/partner/login", json={"email": email, "password": "senha-segura"})
    assert segue.status_code == 200, segue.text
    aceite = TestClient(admin_client.app)
    resposta = aceite.post(
        "/api/v1/partner/invite/accept",
        json={"token": _token(novo.json()["invite_link"]), "password": "senha-nova1"},
    )
    assert resposta.status_code == 200, resposta.text
    assert primeira.get("/api/v1/partner/me").status_code == 401
    assert segunda.get("/api/v1/partner/me").status_code == 401
    assert ainda.get("/api/v1/partner/me").status_code == 401
    assert aceite.get("/api/v1/partner/me").status_code == 200


def test_reativacao_do_parceiro(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    email = f"reativa-{uuid4().hex[:6]}@serra.test"
    created = _criar(admin_client, csrf, email, f"reativa-{uuid4().hex[:6]}")
    cedo = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/activate",
        headers=_csrf(csrf),
    )
    assert cedo.status_code == 409
    admin_client.post(f"/api/v1/admin/marketplace/partners/{created['id']}/pause", headers=_csrf(csrf))
    convite = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/activate",
        headers=_csrf(csrf),
    )
    assert convite.status_code == 200, convite.text
    assert convite.json()["status"] == "invited"
    assert "invite_link" not in convite.json()
    _aceitar(admin_client.app, created["invite_link"])
    admin_client.post(f"/api/v1/admin/marketplace/partners/{created['id']}/pause", headers=_csrf(csrf))
    ativo = admin_client.post(
        f"/api/v1/admin/marketplace/partners/{created['id']}/activate",
        headers=_csrf(csrf),
    )
    assert ativo.status_code == 200, ativo.text
    assert ativo.json()["status"] == "active"
    assert ativo.json()["email"] == email


def _produto_aprovado(admin: TestClient, csrf: str, partner: TestClient, slug: str) -> str:
    product = partner.post("/api/v1/partner/products", json=_produto(slug), headers=_csrf(partner.csrf))
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    sent = partner.post(f"/api/v1/partner/products/{product_id}/submit", headers=_csrf(partner.csrf))
    assert sent.status_code == 200, sent.text
    approved = admin.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 5, "visual": 5, "complementarity": 4, "decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    return product_id


def test_combinacao_valida_e_duplicada(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    created = _criar(admin_client, csrf, f"combo-{uuid4().hex[:6]}@serra.test", f"combo-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    product_id = _produto_aprovado(admin_client, csrf, partner, slug)
    body = {"partner_product_id": product_id, "house_product_slug": slug, "reason": "O pão corta o sal."}
    first = partner.post("/api/v1/partner/combos", json=body, headers=_csrf(partner.csrf))
    assert first.status_code == 201, first.text
    combo = first.json()
    assert combo["status"] == "pending"
    assert combo["partner_product_name"] == "Queijo coalho"
    assert combo["house_product_name"] == "Pão da casa"
    assert combo["house_product_slug"] == slug
    assert set(combo) == {
        "id",
        "partner_id",
        "partner_product_id",
        "partner_product_name",
        "house_product_slug",
        "house_product_name",
        "reason",
        "status",
        "review_note",
        "reviewed_at",
        "updated_at",
    }
    other = _pao(market, "published")
    second = partner.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": other, "reason": "Outro pão."},
        headers=_csrf(partner.csrf),
    )
    assert second.status_code == 201, second.text
    lista = partner.get("/api/v1/partner/combos", headers=_csrf(partner.csrf))
    assert [item["id"] for item in lista.json()] == [second.json()["id"], combo["id"]]
    dupla = partner.post("/api/v1/partner/combos", json=body, headers=_csrf(partner.csrf))
    assert dupla.status_code == 409


def test_combinacao_recusa_produto_alheio_nao_aprovado_e_pao_oculto(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    oculto = _pao(market, "draft")
    dono = _criar(admin_client, csrf, f"dono-c-{uuid4().hex[:6]}@serra.test", f"dono-c-{uuid4().hex[:6]}")
    outro = _criar(admin_client, csrf, f"outro-c-{uuid4().hex[:6]}@serra.test", f"outro-c-{uuid4().hex[:6]}")
    parceiro = _aceitar(admin_client.app, dono["invite_link"])
    alheio = _aceitar(admin_client.app, outro["invite_link"])
    product_id = _produto_aprovado(admin_client, csrf, parceiro, slug)
    rascunho = alheio.post("/api/v1/partner/products", json=_produto(slug), headers=_csrf(alheio.csrf))
    assert rascunho.status_code == 201, rascunho.text
    de_outro = alheio.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": slug, "reason": "Não é meu."},
        headers=_csrf(alheio.csrf),
    )
    assert de_outro.status_code == 404
    sem_aprovar = alheio.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": rascunho.json()["id"], "house_product_slug": slug, "reason": "Ainda em rascunho."},
        headers=_csrf(alheio.csrf),
    )
    assert sem_aprovar.status_code == 400
    sem_pao = parceiro.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": oculto, "reason": "Pão escondido."},
        headers=_csrf(parceiro.csrf),
    )
    assert sem_pao.status_code == 400
    sem_motivo = parceiro.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": slug, "reason": "   "},
        headers=_csrf(parceiro.csrf),
    )
    assert sem_motivo.status_code == 400


def test_reenvio_so_de_devolvida_e_avaliacao_so_de_pendente(
    market: Session, admin_client: TestClient, monkeypatch
):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    slug = _pao(market, "published")
    created = _criar(admin_client, csrf, f"rev-c-{uuid4().hex[:6]}@serra.test", f"rev-c-{uuid4().hex[:6]}")
    partner = _aceitar(admin_client.app, created["invite_link"])
    product_id = _produto_aprovado(admin_client, csrf, partner, slug)
    combo = partner.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": slug, "reason": "Primeira proposta."},
        headers=_csrf(partner.csrf),
    )
    assert combo.status_code == 201, combo.text
    combo_id = combo.json()["id"]
    cedo = partner.patch(
        f"/api/v1/partner/combos/{combo_id}",
        json={"house_product_slug": slug, "reason": "Ainda não devolveu."},
        headers=_csrf(partner.csrf),
    )
    assert cedo.status_code == 409
    sem_nota = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo_id}/review",
        json={"decision": "return", "note": ""},
        headers=_csrf(csrf),
    )
    assert sem_nota.status_code == 400
    recusa = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo_id}/review",
        json={"decision": "reject", "note": ""},
        headers=_csrf(csrf),
    )
    assert recusa.status_code == 400
    devolvida = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo_id}/review",
        json={"decision": "return", "note": "Explique o pão."},
        headers=_csrf(csrf),
    )
    assert devolvida.status_code == 200, devolvida.text
    assert devolvida.json()["status"] == "returned"
    assert devolvida.json()["review_note"] == "Explique o pão."
    assert devolvida.json()["reviewed_at"]
    de_novo = partner.patch(
        f"/api/v1/partner/combos/{combo_id}",
        json={"house_product_slug": slug, "reason": "O miolo acompanha o queijo."},
        headers=_csrf(partner.csrf),
    )
    assert de_novo.status_code == 200, de_novo.text
    assert de_novo.json()["status"] == "pending"
    assert de_novo.json()["reason"] == "O miolo acompanha o queijo."
    fila = admin_client.get("/api/v1/admin/marketplace/combos", headers=_csrf(csrf))
    assert fila.status_code == 200
    assert fila.json()[0]["id"] == combo_id
    aprovada = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo_id}/review",
        json={"decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert aprovada.status_code == 200, aprovada.text
    assert aprovada.json()["status"] == "approved"
    outra = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo_id}/review",
        json={"decision": "reject", "note": "Tarde demais."},
        headers=_csrf(csrf),
    )
    assert outra.status_code == 409
    travada = partner.patch(
        f"/api/v1/partner/combos/{combo_id}",
        json={"house_product_slug": slug, "reason": "Já aprovada."},
        headers=_csrf(partner.csrf),
    )
    assert travada.status_code == 409


_CAMPOS_SENSIVEIS = {
    "document",
    "contact",
    "email",
    "fee",
    "fee_cents",
    "status",
    "review_note",
    "reviewer_ref",
    "pay_recipient_id",
    "password",
    "password_hash",
    "invite_link",
    "csrf_token",
}


def _chaves(value, found: set[str]) -> None:
    if isinstance(value, dict):
        found.update(str(key) for key in value)
        for item in value.values():
            _chaves(item, found)
    elif isinstance(value, list):
        for item in value:
            _chaves(item, found)


def _sem_sensiveis(body: dict) -> None:
    found: set[str] = set()
    _chaves(body, found)
    assert found.isdisjoint(_CAMPOS_SENSIVEIS)
    assert "@serra.test" not in str(body)


def _vincular(admin: TestClient, csrf: str, partner_id: str, category: str, link_type: str) -> None:
    response = admin.post(
        f"/api/v1/admin/marketplace/partners/{partner_id}/links",
        json={"category": category, "link_type": link_type, "starts_on": date.today().isoformat()},
        headers=_csrf(csrf),
    )
    assert response.status_code == 201, response.text


def _aprovar(admin: TestClient, csrf: str, partner: TestClient, slug: str, **extra) -> str:
    created = partner.post("/api/v1/partner/products", json=_produto(slug, **extra), headers=_csrf(partner.csrf))
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    pending = partner.post(f"/api/v1/partner/products/{product_id}/submit", headers=_csrf(partner.csrf))
    assert pending.status_code == 200, pending.text
    approved = admin.post(
        f"/api/v1/admin/marketplace/products/{product_id}/review",
        json={"quality": 5, "visual": 5, "complementarity": 5, "decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert approved.status_code == 200, approved.text
    return product_id


def _abrir(admin: TestClient, csrf: str, slug: str, name: str) -> tuple[dict, TestClient]:
    response = admin.post(
        "/api/v1/admin/marketplace/partners",
        json=_marca(f"{slug}@serra.test", slug, brand_name=name),
        headers=_csrf(csrf),
    )
    assert response.status_code == 201, response.text
    created = response.json()
    return created, _aceitar(admin.app, created["invite_link"])


def test_vitrine_publica_404_com_a_chave_desligada(db: Session, admin_client: TestClient, monkeypatch):
    del db
    _ligar(monkeypatch, False)
    pao = admin_client.get("/api/v1/marketplace/public/breads/qualquer")
    marca = admin_client.get("/api/v1/marketplace/public/partners/qualquer")
    assert pao.status_code == 404
    assert marca.status_code == 404


def test_vitrine_filtra_exclusividade_e_esconde_campos(market: Session, admin_client: TestClient, monkeypatch):
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    publicado = _pao(market, "published")
    oculto = _pao(market, "draft")
    alfa, alfa_portal = _abrir(admin_client, csrf, f"alfa-{uuid4().hex[:6]}", "Alfa Queijo")
    zulu, zulu_portal = _abrir(admin_client, csrf, f"zulu-{uuid4().hex[:6]}", "Zulu Parcial")
    bravo, bravo_portal = _abrir(admin_client, csrf, f"bravo-{uuid4().hex[:6]}", "Bravo Azeite")
    mudo, mudo_portal = _abrir(admin_client, csrf, f"mudo-{uuid4().hex[:6]}", "Mudo Vinho")
    fila, fila_portal = _abrir(admin_client, csrf, f"fila-{uuid4().hex[:6]}", "Fila Frios")
    solto, solto_portal = _abrir(admin_client, csrf, f"solto-{uuid4().hex[:6]}", "Solto Manteiga")
    pausa, pausa_portal = _abrir(admin_client, csrf, f"pausa-{uuid4().hex[:6]}", "Pausa Cerveja")
    viva, viva_portal = _abrir(admin_client, csrf, f"viva-{uuid4().hex[:6]}", "Viva Cerveja")
    _vincular(admin_client, csrf, alfa["id"], "queijos", "exclusive")
    _vincular(admin_client, csrf, zulu["id"], "queijos", "partial")
    _vincular(admin_client, csrf, bravo["id"], "azeites", "none")
    _vincular(admin_client, csrf, mudo["id"], "vinhos", "partial")
    _vincular(admin_client, csrf, fila["id"], "frios", "partial")
    _vincular(admin_client, csrf, pausa["id"], "cervejas", "exclusive")
    _vincular(admin_client, csrf, viva["id"], "cervejas", "partial")
    alfa_id = _aprovar(
        admin_client,
        csrf,
        alfa_portal,
        publicado,
        name="Queijo alfa",
        pairings=[{"house_product_slug": publicado, "reason": "A acidez equilibra o sal."}],
    )
    _aprovar(admin_client, csrf, zulu_portal, publicado, name="Queijo zulu", category="queijos")
    _aprovar(admin_client, csrf, bravo_portal, publicado, name="Azeite bravo", category="azeites")
    _aprovar(admin_client, csrf, mudo_portal, publicado, name="Vinho mudo", category="vinhos", is_available=False)
    pendente = fila_portal.post(
        "/api/v1/partner/products",
        json=_produto(publicado, name="Frio na fila", category="frios"),
        headers=_csrf(fila_portal.csrf),
    )
    assert pendente.status_code == 201, pendente.text
    enviado = fila_portal.post(
        f"/api/v1/partner/products/{pendente.json()['id']}/submit",
        headers=_csrf(fila_portal.csrf),
    )
    assert enviado.status_code == 200, enviado.text
    _aprovar(admin_client, csrf, solto_portal, publicado, name="Manteiga solta", category="manteigas")
    _aprovar(admin_client, csrf, pausa_portal, publicado, name="Cerveja pausada", category="cervejas")
    _aprovar(admin_client, csrf, viva_portal, publicado, name="Cerveja viva", category="cervejas")
    pausado = admin_client.post(f"/api/v1/admin/marketplace/partners/{pausa['id']}/pause", headers=_csrf(csrf))
    assert pausado.status_code == 200, pausado.text
    combo = alfa_portal.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": alfa_id, "house_product_slug": publicado, "reason": "Para a mesa do domingo."},
        headers=_csrf(alfa_portal.csrf),
    )
    assert combo.status_code == 201, combo.text
    aprovado = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo.json()['id']}/review",
        json={"decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert aprovado.status_code == 200, aprovado.text

    vitrine = admin_client.get(f"/api/v1/marketplace/public/breads/{publicado}")
    assert vitrine.status_code == 200, vitrine.text
    body = vitrine.json()
    _sem_sensiveis(body)
    nomes = [item["name"] for item in body["products"]]
    assert nomes == ["Queijo alfa", "Cerveja viva", "Azeite bravo"]
    assert body["covered_categories"] == ["queijos", "cervejas", "azeites"]
    primeiro = body["products"][0]
    assert primeiro["why_pairs"] == "A acidez equilibra o sal."
    assert set(primeiro) == {
        "id",
        "name",
        "description",
        "photos",
        "price_cents",
        "category",
        "why_pairs",
        "delivery",
        "partner",
    }
    assert set(primeiro["delivery"]) == {"cities", "districts", "days", "freight_cents", "perishable"}
    assert set(primeiro["partner"]) == {"brand_name", "brand_slug", "highlight_hex", "logo_url"}
    assert body["combos"][0]["product_name"] == "Queijo alfa"
    assert body["combos"][0]["reason"] == "Para a mesa do domingo."
    assert set(body["combos"][0]) == {
        "id",
        "product_id",
        "product_name",
        "reason",
        "price_cents",
        "freight_cents",
        "partner",
    }
    assert admin_client.get(f"/api/v1/marketplace/public/breads/{oculto}").status_code == 404


def test_pagina_publica_do_parceiro(market: Session, admin_client: TestClient, monkeypatch):
    from uuid import UUID

    from app.marketplace.models import ProductPairing

    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    publicado = _pao(market, "published")
    oculto = _pao(market, "draft")
    criado, portal = _abrir(admin_client, csrf, f"marca-{uuid4().hex[:6]}", "Queijaria Serra de Teste")
    _vincular(admin_client, csrf, criado["id"], "queijos", "none")
    product_id = _aprovar(
        admin_client,
        csrf,
        portal,
        publicado,
        name="Queijo coalho de teste",
        pairings=[{"house_product_slug": publicado, "reason": "acompanha o coalho"}],
    )
    market.add(
        ProductPairing(
            product_id=UUID(product_id),
            house_product_slug=oculto,
            reason="este pao nao esta publicado",
        )
    )
    market.commit()
    combo = portal.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": product_id, "house_product_slug": publicado, "reason": "Para o cafe."},
        headers=_csrf(portal.csrf),
    )
    assert combo.status_code == 201, combo.text
    aprovado = admin_client.post(
        f"/api/v1/admin/marketplace/combos/{combo.json()['id']}/review",
        json={"decision": "approve", "note": ""},
        headers=_csrf(csrf),
    )
    assert aprovado.status_code == 200, aprovado.text
    pagina = admin_client.get(f"/api/v1/marketplace/public/partners/{criado['brand_slug']}")
    assert pagina.status_code == 200, pagina.text
    body = pagina.json()
    _sem_sensiveis(body)
    assert set(body["partner"]) == {
        "brand_name",
        "brand_slug",
        "highlight_hex",
        "logo_url",
        "photo_url",
        "story",
        "city",
        "region",
    }
    assert body["partner"]["brand_name"] == "Queijaria Serra de Teste"
    assert body["products"][0]["name"] == "Queijo coalho de teste"
    assert body["products"][0]["pairings"] == [
        {
            "house_product_slug": publicado,
            "house_product_name": "Pão da casa",
            "reason": "acompanha o coalho",
        }
    ]
    assert body["combos"][0]["house_product_slug"] == publicado
    assert body["combos"][0]["house_product_name"] == "Pão da casa"
    pausa = admin_client.post(f"/api/v1/admin/marketplace/partners/{criado['id']}/pause", headers=_csrf(csrf))
    assert pausa.status_code == 200, pausa.text
    assert admin_client.get(f"/api/v1/marketplace/public/partners/{criado['brand_slug']}").status_code == 404
    assert admin_client.get("/api/v1/marketplace/public/partners/marca-inexistente").status_code == 404


def test_midia_acima_de_8_mb_recusada(market: Session, admin_client: TestClient, monkeypatch, tmp_path):
    del market
    _pasta_de_midia(monkeypatch, tmp_path)
    _ligar(monkeypatch, True)
    csrf = login(admin_client)
    criado = _criar(admin_client, csrf, f"peso-{uuid4().hex[:6]}@serra.test", f"peso-{uuid4().hex[:6]}")
    portal = _aceitar(admin_client.app, criado["invite_link"])
    grande = portal.post(
        "/api/v1/partner/media",
        files={"file": ("grande.jpg", b"x" * (8 * 1024 * 1024 + 1), "image/jpeg")},
        headers=_csrf(portal.csrf),
    )
    assert grande.status_code == 400
    assert grande.json()["detail"] == "a imagem excede o limite de 8 MB"


def test_combinacoes_404_com_a_chave_desligada(db: Session, admin_client: TestClient, monkeypatch):
    del db
    _ligar(monkeypatch, False)
    csrf = login(admin_client)
    admin = admin_client.get("/api/v1/admin/marketplace/combos", headers=_csrf(csrf))
    assert admin.status_code == 404
    partner = admin_client.get("/api/v1/partner/combos")
    assert partner.status_code == 404
    proposta = admin_client.post(
        "/api/v1/partner/combos",
        json={"partner_product_id": "00000000-0000-0000-0000-000000000000", "house_product_slug": "pao", "reason": "x"},
    )
    assert proposta.status_code == 404

