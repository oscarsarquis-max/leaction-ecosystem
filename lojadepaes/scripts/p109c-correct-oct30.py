"""Seção E do 109C: corrige os registros de 30/10 pela API de administração.

Roda dentro do contêiner da API (`python - <fase>`): abre uma sessão administrativa
curta, chama as rotas novas em 127.0.0.1:8080 e apaga a sessão ao final. Nenhum SQL de
escrita; o banco só é lido para contar a caixa de saída. A saída mostra referências,
status, datas e contagens, sem nome, e-mail, telefone nem endereço.

Fases: before (só leitura), apply (reschedule e anulação), after (só leitura).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.admin_auth import SESSION_COOKIE, _issue_session
from app.models.admin import AdminSession
from app.models.email_outbox import EmailOutbox

BASE = os.environ.get("P109C_BASE", "http://127.0.0.1:8080")
REAL = os.environ.get("P109C_REAL", "LP331354282E")
DUPLICATE = os.environ.get("P109C_DUP", "LP398E6E6AC4")
PAIR = ("LP063F5ED6C6", "LPACD780ADB3")
FRIDAY = os.environ.get("P109C_DATE", "2026-10-30")
SUNDAY = os.environ.get("P109C_OTHER_DATE", "2026-11-01")
RESCHEDULE_REASON = "Antecipação combinada com o cliente pelo WhatsApp; produzido e entregue na sexta"
VOID_REASON = "Criado pelo aceite da solicitação de data; a encomenda real é LP331354282E, paga e entregue"


def main(phase: str) -> None:
    settings = get_settings()
    db = sessionmaker(bind=get_engine())()
    token, csrf, row = _issue_session(
        db,
        settings,
        username=(settings.admin_username or "leitura").strip() or "leitura",
        client_host="127.0.0.1",
    )
    session_id = row.id
    db.commit()
    headers = {"Cookie": f"{SESSION_COOKIE}={token}", "X-CSRF-Token": csrf, "Content-Type": "application/json"}

    def call(method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            try:
                payload = json.load(error)
            except Exception:
                payload = {}
            return error.code, payload

    def find(reference: str) -> str | None:
        # Pedido anulado só aparece na lente de auditoria; os demais, na busca comum.
        for query in (
            f"reference={reference}&status=all&page_size=5",
            f"lens=audit:duplicates&reference={reference}&page_size=5",
        ):
            _status, listing = call("GET", f"/api/v1/admin/orders?{query}")
            for item in listing.get("items", []):
                if item.get("public_reference") == reference:
                    return item["id"]
        return None

    def refs(lens: str) -> list[str]:
        out: list[str] = []
        page = 1
        while True:
            _s, listing = call("GET", f"/api/v1/admin/orders?lens={lens}&page={page}&page_size=50")
            out += [i.get("public_reference") or "" for i in listing.get("items", [])]
            if len(out) >= listing.get("total", 0) or not listing.get("items"):
                return out
            page += 1

    def outbox() -> dict:
        by_ref = {REAL: find(REAL), DUPLICATE: find(DUPLICATE)}
        known = [oid for oid in by_ref.values() if oid]
        rows = db.execute(
            select(EmailOutbox.order_id, EmailOutbox.kind, func.count())
            .where(EmailOutbox.order_id.in_(known))
            .group_by(EmailOutbox.order_id, EmailOutbox.kind)
        ).all()
        total = db.scalar(select(func.count()).select_from(EmailOutbox)) or 0
        changed = (
            db.scalar(select(func.count()).select_from(EmailOutbox).where(EmailOutbox.kind == "order_date_changed")) or 0
        )
        detail = {
            ref: {kind: n for (oid, kind, n) in rows if str(oid) == str(order_id)}
            for ref, order_id in by_ref.items()
        }
        return {"outbox_total": total, "order_date_changed_total": changed, "por_pedido": detail}

    def day(date_iso: str) -> dict:
        _s, view = call("GET", f"/api/v1/admin/schedule/days/{date_iso}")
        return {"data": date_iso, "paes_ocupados": view.get("committed_physical"), "limite": view.get("daily_physical_limit"), "aberto": view.get("is_open")}

    def snapshot(reference: str) -> dict:
        order_id = find(reference)
        if order_id is None:
            return {"ref": reference, "encontrado": False}
        _s, d = call("GET", f"/api/v1/admin/orders/{order_id}")
        return {
            "ref": reference,
            "status": d.get("status"),
            "data_operacional": d.get("production_local_date"),
            "data_solicitada": d.get("requested_date"),
            "ocupa_vaga": d.get("holds_capacity"),
            "excecao": (d.get("schedule_exception") or {}).get("label"),
            "etapa_visivel": ((d.get("tracks") or {}).get("commercial") or {}).get("label"),
            "pagamentos_locais": [r.get("financial_status") for r in d.get("payment_records", [])],
            "faixa_anulado": bool(d.get("void_banner")),
            "ligacoes_de_anulados": [x.get("public_reference") for x in d.get("duplicate_links", [])],
        }

    def report(title: str) -> None:
        print(f"== {title}")
        print(json.dumps({
            "pedido_real": snapshot(REAL),
            "pedido_duplicado": snapshot(DUPLICATE),
            "dias": [day(FRIDAY), day(SUNDAY)],
            "caixa_de_saida": outbox(),
            "lente_anulados": [r for r in refs("audit:duplicates") if r in {REAL, DUPLICATE, *PAIR}],
            "lente_possivel_duplicidade": refs("pending:possible_duplicate"),
            "par_pendente_na_lente_de_duplicidade": [r for r in refs("pending:possible_duplicate") if r in PAIR],
            "entregues_entre_os_dois": [r for r in refs("stage:delivered") if r in {REAL, DUPLICATE}],
            "vigentes_entre_os_dois": [r for r in refs("vigentes") if r in {REAL, DUPLICATE}],
            "par_063_acd": [snapshot(PAIR[0]).get("status"), snapshot(PAIR[1]).get("status")],
        }, ensure_ascii=False, indent=2))

    try:
        if phase in {"before", "after"}:
            report("antes" if phase == "before" else "depois")
        elif phase == "apply":
            real_id, dup_id = find(REAL), find(DUPLICATE)
            if not real_id or not dup_id:
                raise SystemExit("pedido não encontrado; nada foi alterado")
            status, body = call(
                "POST",
                f"/api/v1/admin/orders/{real_id}/reschedule",
                {"date": FRIDAY, "reason": RESCHEDULE_REASON, "origin": "customer", "notify_customer": False, "allow_closed_day": False},
            )
            print("reschedule", REAL, status, (body.get("action_notice") or body.get("detail") or ""))
            if status != 200:
                raise SystemExit("reschedule falhou; a anulação não foi tentada")
            status, body = call(
                "POST",
                f"/api/v1/admin/orders/{dup_id}/void-duplicate",
                {"original_order_id": real_id, "reason": VOID_REASON},
            )
            print("void-duplicate", DUPLICATE, status, (body.get("detail") or "ok"))
        else:
            raise SystemExit("fase desconhecida")
    finally:
        cleanup = sessionmaker(bind=get_engine())()
        stored = cleanup.get(AdminSession, session_id)
        if stored is not None:
            cleanup.delete(stored)
        cleanup.commit()
        cleanup.close()
        db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "before")
