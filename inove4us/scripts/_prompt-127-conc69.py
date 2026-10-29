#!/usr/bin/env python3
"""Concluir aula 69 do Campus 2.0 com sugestão e imprimir school_sync."""
import json
import requests

BASE = "https://inove4us.com.br"
s = requests.Session()
s.post(f"{BASE}/api/auth/check-email", json={"email": "homologador@leaction.com.br"}, timeout=20)
r = s.post(
    f"{BASE}/api/agenda-eventos/69/concluir-aula",
    json={
        "relato_sala": (
            "1ª Série A trabalhou inflação da construção e hipóteses de paginação. "
            "Mariana Duarte (TDAH) alternou medição e registro em dupla."
        ),
        "participantes": "1ª Série A — 6 alunos",
        "has_teacher_adaptations": True,
        "sugestao_coordenacao": (
            "Na Auditoria de Divergência, o Minute Paper de saída funcionou melhor em duplas "
            "heterogêneas: um aluno mede, o outro registra na planta. Sugiro formalizar esse "
            "pareamento na diretriz da escola para a Abordagem Problematizadora."
        ),
        "metodologia_usada": "Abordagem Problematizadora",
        "aula_contexto": "Operação Campus 2.0 — noite, 1ª Série A",
    },
    timeout=40,
)
body = r.json() if r.content else {}
ss = body.get("school_sync") or {}
print(json.dumps({
    "http": r.status_code,
    "ok": r.ok,
    "error": body.get("error"),
    "school_sync": ss,
    "evento_status": (body.get("evento") or {}).get("status"),
}, ensure_ascii=False, indent=2, default=str))
