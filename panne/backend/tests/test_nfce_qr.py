"""QR de NFC-e: só a URL. Não grava e não consulta a rede."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.fiscal_inbound.qr_code import access_key_valid, read_nfce_qr


def _key(tp_emis: str = "1") -> str:
    base = "35" + "2510" + "00000000000191" + "65" + "001" + "000000001" + tp_emis + "00000001"
    assert len(base) == 43
    total = 0
    weight = 2
    for char in reversed(base):
        total += int(char) * weight
        weight = 2 if weight == 9 else weight + 1
    mod = total % 11
    digit = "0" if mod < 2 else str(11 - mod)
    return base + digit


def _principal():
    return SimpleNamespace(permissions={"fiscal.document.capture"})


def test_chave_de_nfce_tem_digito():
    key = _key()
    assert access_key_valid(key)
    assert not access_key_valid(key[:-1] + ("0" if key[-1] != "0" else "1"))


def test_versao_3_online_nao_importa_itens():
    key = _key()
    url = f"https://www.nfce.fazenda.sp.gov.br/qrcode?p={key}|3|1"
    result = read_nfce_qr(_principal(), url)
    assert result["recognized"] is True
    assert result["model"] == "65"
    assert result["uf"] == "SP"
    assert result["environment"] == "producao"
    assert result["number"] == "1"
    assert result["series"] == "1"
    assert result["items"] == []
    assert result["import_available"] is False
    assert result["modality"] == "leitura_chave"
    assert result["network_request"] is False
    assert result["emission_label"] == "online"
    assert result["environment_label"] == "produção"
    assert "certificado digital" in result["dependency"]
    assert "importação automática indisponível" in result["message"]


def test_versao_2_online_e_homologacao():
    key = _key()
    url = f"https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p={key}|2|2|000001|{'a' * 40}"
    result = read_nfce_qr(_principal(), url)
    assert result["qr_version"] == "2"
    assert result["environment"] == "homologacao"
    assert result["environment_label"] == "homologação"
    assert result["emission"] == "online"
    assert result["emission_label"] == "online"
    assert result["import_available"] is False
    assert result["items"] == []


def test_modelo_55_nao_vira_nfce():
    base = "35" + "2510" + "00000000000191" + "55" + "001" + "000000001" + "1" + "00000001"
    assert len(base) == 43
    total = 0
    weight = 2
    for char in reversed(base):
        total += int(char) * weight
        weight = 2 if weight == 9 else weight + 1
    mod = total % 11
    digit = "0" if mod < 2 else str(11 - mod)
    nfe = base + digit
    result = read_nfce_qr(_principal(), f"https://www.nfce.fazenda.sp.gov.br/qrcode?p={nfe}|3|1")
    assert result["recognized"] is False
    assert result["reason"] == "modelo_nao_e_nfce"
    assert result["items"] == []


def test_enderecos_nao_oficiais_nao_sao_seguidos():
    key = _key()
    blocked = [
        f"https://127.0.0.1/qrcode?p={key}|3|1",
        f"https://localhost/qrcode?p={key}|3|1",
        f"https://evil.example/qrcode?p={key}|3|1",
        f"https://sefaz.fazenda.sp.gov.br/qrcode?p={key}|3|1",
        f"https://www.nfce.fazenda.sp.gov.br.evil.gov.br/qrcode?p={key}|3|1",
        f"https://user:secret@www.nfce.fazenda.sp.gov.br/qrcode?p={key}|3|1",
        f"https://10.0.0.8/qrcode?p={key}|3|1",
        f"https://nfce.svrs.rs.gov.br/qrcode?p={key}|3|1",
    ]
    for url in blocked:
        result = read_nfce_qr(_principal(), url)
        assert result["recognized"] is False
        assert result["consultation_url"] is None


def test_http_oficial_nao_e_chamado():
    key = _key()
    result = read_nfce_qr(
        _principal(),
        f"http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx?p={key}|3|1",
    )
    assert result["recognized"] is True
    assert result["modality"] == "leitura_chave"
    assert result["consultation_url"] is None
    assert result["network_request"] is False
    assert result["items"] == []


def test_contingencia_e_homologacao_sao_rotuladas():
    key = _key("9")
    url = f"https://www.nfce.fazenda.sp.gov.br/qrcode?p={key}|3|2|15|10.00|1|00000000000191|assinatura"
    result = read_nfce_qr(_principal(), url)
    assert result["emission"] == "contingencia"
    assert result["emission_label"] == "contingência"
    assert result["environment_label"] == "homologação"
    assert result["qr_layout"] == "contingencia"
    assert result["import_available"] is False
    assert result["items"] == []


def test_duplicata_nao_sai_da_organizacao():
    from uuid import uuid4

    from app.modules.fiscal_inbound.qr_code import same_organization_document_id

    org_a, org_b, doc = uuid4(), uuid4(), uuid4()
    key = _key()

    class Memoria:
        def scalar(self, stmt):
            blob = " ".join(str(value) for value in stmt.compile().params.values())
            if str(org_a) in blob and key in blob:
                return doc
            return None

        def add(self, *_args, **_kwargs):
            raise AssertionError("leitura gravou")

    def principal(org):
        return SimpleNamespace(
            permissions={"fiscal.document.capture"},
            selected=SimpleNamespace(organization_id=org),
        )

    assert same_organization_document_id(Memoria(), principal(org_a), key) == str(doc)
    assert same_organization_document_id(Memoria(), principal(org_b), key) is None


def test_sem_permissao():
    with pytest.raises(Exception):
        read_nfce_qr(SimpleNamespace(permissions=set()), f"https://www.nfce.fazenda.sp.gov.br/qrcode?p={_key()}|3|1")
