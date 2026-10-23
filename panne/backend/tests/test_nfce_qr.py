"""QR de NFC-e: só a URL. Não grava e não consulta a rede."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.fiscal_inbound.qr_code import access_key_valid, read_nfce_qr


def _key() -> str:
    base = "35" + "2510" + "00000000000191" + "65" + "001" + "000000001" + "1" + "00000001"
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
    assert "importação automática indisponível" in result["message"]


def test_versao_2_online_e_homologacao():
    key = _key()
    url = f"https://nfce.svrs.rs.gov.br/qrcode?p={key}|2|2|000001|{'a' * 40}"
    result = read_nfce_qr(_principal(), url)
    assert result["qr_version"] == "2"
    assert result["environment"] == "homologacao"
    assert result["emission"] == "online"
    assert result["import_available"] is False


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
        f"http://www.nfce.fazenda.sp.gov.br/qrcode?p={key}|3|1",
        f"https://127.0.0.1/qrcode?p={key}|3|1",
        f"https://localhost/qrcode?p={key}|3|1",
        f"https://evil.example/qrcode?p={key}|3|1",
        f"https://user:secret@www.nfce.fazenda.sp.gov.br/qrcode?p={key}|3|1",
        f"https://10.0.0.8/qrcode?p={key}|3|1",
    ]
    for url in blocked:
        result = read_nfce_qr(_principal(), url)
        assert result["recognized"] is False
        assert result["consultation_url"] is None


def test_sem_permissao():
    with pytest.raises(Exception):
        read_nfce_qr(SimpleNamespace(permissions=set()), f"https://www.nfce.fazenda.sp.gov.br/qrcode?p={_key()}|3|1")
