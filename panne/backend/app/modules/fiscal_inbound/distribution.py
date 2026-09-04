"""Distribuição DF-e/NF-e do destinatário.

Interface estável + adaptador oficial (desligado) + provedor sintético da demo.
Nunca consulta a Fazenda com PANNE_FISCAL_LIVE!=1. Certificado/senha nunca
transitam aqui — só secret_ref e metadados sanitizados.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.modules.fiscal_inbound.constants import (
    CERT_ACTIVE,
    CERT_ERROR,
    CERT_EXPIRED,
    CERT_NOT_CONFIGURED,
    CERT_REVOKED,
    CERT_VALIDATING,
    DEMO_ACCESS_KEY_PREFIX,
    DEMO_EMITTER_TAX_ID,
    DEMO_LABEL,
    DEMO_RECIPIENT_TAX_ID,
    DISTRIBUTION_BACKOFF_SECONDS,
    DISTRIBUTION_RATE_LIMIT_PER_MINUTE,
    ENV_HOMOLOGATION,
    FISCAL_LIVE_FLAG,
)
from app.modules.production_planning.errors import InvalidStateError, ValidationError

# Respostas oficiais do DistDFe (contrato SEFAZ — sem rede nesta fase).
CSTAT_DOCUMENT_FOUND = "138"
CSTAT_NO_DOCUMENTS = "137"
CSTAT_CONSUMED = "656"
CSTAT_TEMPORARY = "108"
CSTAT_CANCELLED_EVENT = "101"


@dataclass(frozen=True)
class DistDocument:
    nsu: str
    schema: str
    access_key: str | None
    xml_payload: bytes | None
    summary: dict
    cancelled: bool = False
    label: str = DEMO_LABEL


@dataclass(frozen=True)
class DistResult:
    c_stat: str
    x_motivo: str
    max_nsu: str | None
    last_nsu: str | None
    documents: tuple[DistDocument, ...] = ()
    temporary_failure: bool = False
    retry_after_seconds: int | None = None
    synthetic: bool = False


@dataclass
class CertificateConfigView:
    """Metadados públicos do certificado — sem material criptográfico."""

    establishment_id: UUID
    status: str
    tax_id: str | None
    environment: str
    distribution_enabled: bool
    secret_ref_present: bool
    not_before: datetime | None
    not_after: datetime | None
    last_consultation_at: datetime | None
    last_nsu: str | None
    diagnosis: str | None
    live_global_enabled: bool


class FiscalDocumentDistributionProvider(Protocol):
    """Contrato estável — domínio Panne não conhece UF, biblioteca ou vendor."""

    def distribute(
        self,
        *,
        tax_id: str,
        last_nsu: str | None,
        environment: str,
    ) -> DistResult: ...

    def download(self, *, nsu: str, schema: str) -> DistDocument: ...

    def consult_access_key(self, *, access_key: str) -> DistDocument | None: ...


def fiscal_live_enabled() -> bool:
    return os.environ.get(FISCAL_LIVE_FLAG, "0").strip() == "1"


def assert_live_disabled() -> None:
    if fiscal_live_enabled():
        # Mesmo com flag global, o adaptador oficial ainda exige cert ativo
        # e habilitação por estabelecimento — ver NFeDistribuicaoDFe.
        return
    raise InvalidStateError("integracao_fazenda_desativada")


def sanitize_diagnosis(raw: str | None) -> str | None:
    if not raw:
        return None
    lowered = raw.lower()
    for banned in ("private key", "senha", "password", "-----begin", "pfx", "pkcs12"):
        if banned in lowered:
            return "diagnostico_sanitizado"
    return raw[:500]


def validate_certificate_config(view: CertificateConfigView) -> list[str]:
    """Teste de configuração sem consulta fiscal real."""
    problems: list[str] = []
    if view.status == CERT_NOT_CONFIGURED or not view.secret_ref_present:
        problems.append("certificado_nao_configurado")
    if view.status == CERT_EXPIRED:
        problems.append("certificado_expirado")
    if view.status == CERT_REVOKED:
        problems.append("certificado_revogado")
    if view.status == CERT_ERROR:
        problems.append("certificado_com_erro")
    if view.not_after and view.not_after < datetime.now(UTC):
        problems.append("certificado_expirado")
    if view.tax_id and view.tax_id != DEMO_RECIPIENT_TAX_ID and len(view.tax_id) not in {11, 14}:
        problems.append("cnpj_incompativel")
    if not view.distribution_enabled:
        problems.append("distribuicao_desabilitada_no_estabelecimento")
    if not view.live_global_enabled:
        problems.append("flag_global_desligada")
    return problems


class DisabledLiveGuard:
    """Bloqueia qualquer tentativa de I/O real enquanto a flag global estiver off."""

    def guard(self) -> None:
        if not fiscal_live_enabled():
            raise InvalidStateError("integracao_fazenda_desativada")


_SYNTHETIC_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{DEMO_ACCESS_KEY_PREFIX}0000000000000000000000000000000000000000" versao="4.00">
      <ide>
        <cUF>35</cUF><mod>55</mod><serie>1</serie><nNF>99001</nNF>
        <dhEmi>2026-08-20T10:00:00-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>{DEMO_EMITTER_TAX_ID}</CNPJ>
        <xNome>FORNECEDOR {DEMO_LABEL} LTDA</xNome>
      </emit>
      <dest>
        <CNPJ>{DEMO_RECIPIENT_TAX_ID}</CNPJ>
        <xNome>PADARIA {DEMO_LABEL}</xNome>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>FAR-DEMO-01</cProd><cEAN>SEM GTIN</cEAN>
          <xProd>Farinha de trigo tipo 1 — {DEMO_LABEL}</xProd>
          <NCM>11010010</NCM><CFOP>5102</CFOP><uCom>KG</uCom>
          <qCom>25.0000</qCom><vUnCom>3.200000</vUnCom><vProd>80.00</vProd>
        </prod>
        <imposto/>
      </det>
      <det nItem="2">
        <prod>
          <cProd>ITEM-PENDENTE</cProd><cEAN>SEM GTIN</cEAN>
          <xProd>Insumo sem correspondência — {DEMO_LABEL}</xProd>
          <NCM>21069090</NCM><CFOP>5102</CFOP><uCom>UN</uCom>
          <qCom>10.0000</qCom><vUnCom>1.500000</vUnCom><vProd>15.00</vProd>
        </prod>
        <imposto/>
      </det>
      <total>
        <ICMSTot>
          <vProd>95.00</vProd><vFrete>5.00</vFrete><vDesc>0.00</vDesc>
          <vNF>100.00</vNF><vICMS>0.00</vICMS>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
  <protNFe>
    <infProt>
      <chNFe>{DEMO_ACCESS_KEY_PREFIX}0000000000000000000000000000000000000000</chNFe>
      <nProt>999999999999999</nProt>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e — {DEMO_LABEL}</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>
""".encode("utf-8")


def _synthetic_key(suffix: str) -> str:
    body = (suffix + "0" * 40)[:40]
    return f"{DEMO_ACCESS_KEY_PREFIX}{body}"


class FixtureDistributionProvider:
    """Provedor sintético compatível com a mesma interface do adaptador oficial."""

    def __init__(self) -> None:
        self._calls = 0
        self._fail_once = False
        self._documents: dict[str, DistDocument] = {}
        self._seed()

    def _seed(self) -> None:
        key_ok = _synthetic_key("1111111111111111111111111111111111111111")
        key_cancel = _synthetic_key("2222222222222222222222222222222222222222")
        key_partial = _synthetic_key("3333333333333333333333333333333333333333")
        self._documents = {
            "000000000000001": DistDocument(
                nsu="000000000000001",
                schema="procNFe_v4.00",
                access_key=key_ok,
                xml_payload=_SYNTHETIC_XML,
                summary={
                    "scenario": "found",
                    "emitter": f"FORNECEDOR {DEMO_LABEL}",
                    "matched_item": True,
                    "pending_match": True,
                    "qty_divergence": False,
                    "price_divergence": False,
                },
                label=DEMO_LABEL,
            ),
            "000000000000002": DistDocument(
                nsu="000000000000002",
                schema="procEventoNFe_v1.00",
                access_key=key_cancel,
                xml_payload=None,
                summary={"scenario": "cancelled_after_distribution", "cStat": CSTAT_CANCELLED_EVENT},
                cancelled=True,
                label=DEMO_LABEL,
            ),
            "000000000000003": DistDocument(
                nsu="000000000000003",
                schema="procNFe_v4.00",
                access_key=key_partial,
                xml_payload=_SYNTHETIC_XML.replace(b"99001", b"99002"),
                summary={
                    "scenario": "partial_and_divergence",
                    "qty_divergence": True,
                    "price_divergence": True,
                    "partial_receipt": True,
                },
                label=DEMO_LABEL,
            ),
        }

    def arm_temporary_failure(self) -> None:
        self._fail_once = True

    def distribute(
        self,
        *,
        tax_id: str,
        last_nsu: str | None,
        environment: str,
    ) -> DistResult:
        self._calls += 1
        if tax_id != DEMO_RECIPIENT_TAX_ID:
            raise ValidationError("cnpj_incompativel")
        if self._fail_once:
            self._fail_once = False
            backoff = DISTRIBUTION_BACKOFF_SECONDS[min(self._calls % 5, 4)]
            return DistResult(
                c_stat=CSTAT_TEMPORARY,
                x_motivo=f"Serviço temporariamente indisponível — {DEMO_LABEL}",
                max_nsu=last_nsu,
                last_nsu=last_nsu,
                temporary_failure=True,
                retry_after_seconds=backoff,
                synthetic=True,
            )
        cursor = last_nsu or "000000000000000"
        pending = [doc for nsu, doc in sorted(self._documents.items()) if nsu > cursor]
        if not pending:
            return DistResult(
                c_stat=CSTAT_NO_DOCUMENTS,
                x_motivo=f"Nenhum documento localizado — {DEMO_LABEL}",
                max_nsu=cursor,
                last_nsu=cursor,
                synthetic=True,
            )
        batch = pending[:2]
        return DistResult(
            c_stat=CSTAT_DOCUMENT_FOUND,
            x_motivo=f"Documento(s) localizado(s) — {DEMO_LABEL}",
            max_nsu=batch[-1].nsu,
            last_nsu=batch[-1].nsu,
            documents=tuple(batch),
            synthetic=True,
        )

    def download(self, *, nsu: str, schema: str) -> DistDocument:
        doc = self._documents.get(nsu)
        if doc is None:
            raise ValidationError("documento_distribuicao_nao_encontrado")
        return doc

    def consult_access_key(self, *, access_key: str) -> DistDocument | None:
        digits = "".join(ch for ch in access_key if ch.isdigit())
        if not digits.startswith(DEMO_ACCESS_KEY_PREFIX) or len(digits) != 44:
            raise ValidationError("chave_acesso_sintetica_invalida")
        for doc in self._documents.values():
            if doc.access_key == digits:
                return doc
        # Chave sintética válida sem documento pré-semeado → monta um stub.
        return DistDocument(
            nsu="000000000000099",
            schema="procNFe_v4.00",
            access_key=digits,
            xml_payload=_SYNTHETIC_XML.replace(
                f"{DEMO_ACCESS_KEY_PREFIX}0000000000000000000000000000000000000000".encode(),
                digits.encode(),
            ),
            summary={"scenario": "access_key_lookup", "label": DEMO_LABEL},
            label=DEMO_LABEL,
        )


class RateLimiter:
    def __init__(self, limit_per_minute: int = DISTRIBUTION_RATE_LIMIT_PER_MINUTE) -> None:
        self.limit = limit_per_minute
        self._hits: list[float] = []

    def check(self) -> None:
        now = time.monotonic()
        self._hits = [t for t in self._hits if now - t < 60]
        if len(self._hits) >= self.limit:
            raise InvalidStateError("distribuicao_rate_limit")
        self._hits.append(now)


class NFeDistribuicaoDFe:
    """Adaptador oficial DistDFe do destinatário.

    Nesta fase: fixtures/mocks apenas. Rede real permanece atrás de
    PANNE_FISCAL_LIVE=1 + distribution_enabled + certificado ativo.
    """

    def __init__(
        self,
        *,
        fixtures: FixtureDistributionProvider | None = None,
        guard: DisabledLiveGuard | None = None,
        limiter: RateLimiter | None = None,
        certificate: CertificateConfigView | None = None,
    ) -> None:
        self._fixtures = fixtures or FixtureDistributionProvider()
        self._guard = guard or DisabledLiveGuard()
        self._limiter = limiter or RateLimiter()
        self._certificate = certificate
        self._processed_keys: set[str] = set()

    def with_certificate(self, view: CertificateConfigView) -> NFeDistribuicaoDFe:
        return NFeDistribuicaoDFe(
            fixtures=self._fixtures,
            guard=self._guard,
            limiter=self._limiter,
            certificate=view,
        )

    def _assert_ready_for_live(self) -> None:
        self._guard.guard()
        if self._certificate is None:
            raise InvalidStateError("certificado_nao_configurado")
        problems = validate_certificate_config(self._certificate)
        # Remove flag_global da lista se já passou no guard.
        problems = [p for p in problems if p != "flag_global_desligada"]
        if problems:
            raise InvalidStateError(problems[0])

    def distribute(
        self,
        *,
        tax_id: str,
        last_nsu: str | None,
        environment: str,
    ) -> DistResult:
        self._limiter.check()
        if not fiscal_live_enabled():
            # Modo demo / preparação: só o provedor sintético.
            return self._fixtures.distribute(
                tax_id=tax_id or DEMO_RECIPIENT_TAX_ID,
                last_nsu=last_nsu,
                environment=environment or ENV_HOMOLOGATION,
            )
        self._assert_ready_for_live()
        # Ativação real ainda não implementada — nunca abre socket.
        raise InvalidStateError("integracao_fazenda_ainda_nao_ativada")

    def download(self, *, nsu: str, schema: str) -> DistDocument:
        self._limiter.check()
        if not fiscal_live_enabled():
            return self._fixtures.download(nsu=nsu, schema=schema)
        self._assert_ready_for_live()
        raise InvalidStateError("integracao_fazenda_ainda_nao_ativada")

    def consult_access_key(self, *, access_key: str) -> DistDocument | None:
        self._limiter.check()
        digits = "".join(ch for ch in access_key if ch.isdigit())
        if digits in self._processed_keys:
            # Idempotência: mesma chave não gera segundo documento.
            raise ValidationError("documento_ja_processado")
        if not fiscal_live_enabled():
            doc = self._fixtures.consult_access_key(access_key=digits)
            if doc and doc.access_key:
                self._processed_keys.add(doc.access_key)
            return doc
        self._assert_ready_for_live()
        raise InvalidStateError("integracao_fazenda_ainda_nao_ativada")


_DEFAULT_PROVIDER = NFeDistribuicaoDFe()


def default_distribution_provider() -> FiscalDocumentDistributionProvider:
    return _DEFAULT_PROVIDER


def establishment_distribution_ready(view: CertificateConfigView | None) -> dict:
    """Payload seguro para a UI — nunca promete consulta automática se não estiver pronta."""
    live = fiscal_live_enabled()
    if view is None:
        return {
            "ready": False,
            "live": live,
            "message": (
                "Consulta automática preparada, mas ainda não ativada para este estabelecimento."
            ),
            "simulation_available": True,
            "status": CERT_NOT_CONFIGURED,
        }
    problems = validate_certificate_config(
        CertificateConfigView(
            establishment_id=view.establishment_id,
            status=view.status,
            tax_id=view.tax_id,
            environment=view.environment,
            distribution_enabled=view.distribution_enabled,
            secret_ref_present=view.secret_ref_present,
            not_before=view.not_before,
            not_after=view.not_after,
            last_consultation_at=view.last_consultation_at,
            last_nsu=view.last_nsu,
            diagnosis=sanitize_diagnosis(view.diagnosis),
            live_global_enabled=live,
        )
    )
    ready = live and not problems
    return {
        "ready": ready,
        "live": live,
        "message": (
            "Consulta automática disponível."
            if ready
            else "Consulta automática preparada, mas ainda não ativada para este estabelecimento."
        ),
        "simulation_available": True,
        "status": view.status,
        "problems": problems,
        "last_nsu": view.last_nsu,
        "last_consultation_at": (
            view.last_consultation_at.isoformat() if view.last_consultation_at else None
        ),
        "diagnosis": sanitize_diagnosis(view.diagnosis),
    }
