#!/usr/bin/env python3
"""128 — 3 aulas Dia a Dia com BNCC (demo). Não limpa."""
from __future__ import annotations

import json
from datetime import date

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"

AULAS = [
    {
        "data": "2026-09-17",
        "turma": "1ª Série A",
        "curso_ano": "1ª série",
        "codigo": "EM13MAT102",
        "tema": "Tabelas, gráficos e pesquisas estatísticas nas mídias",
        "texto": (
            "Analisar tabelas, gráficos e amostras de pesquisas estatísticas apresentadas "
            "em relatórios divulgados por diferentes meios de comunicação, identificando "
            "eventuais analogias e distorções."
        ),
        "met": "criativa_sala_invertida",
        "objetivo": "Ler um gráfico de mídia e apontar o que ele mostra e o que ele esconde.",
    },
    {
        "data": "2026-09-18",
        "turma": "9º Ano A",
        "curso_ano": "6º ano",
        "codigo": "EF06MA14",
        "tema": "Porcentagem: descontos, acréscimos e comparações",
        "texto": (
            "Resolver e elaborar problemas que envolvam porcentagens, com base na ideia de "
            "proporcionalidade, sem uso de fórmulas, relacionando representação percentual "
            "e decimal."
        ),
        "met": "agil_minute_paper",
        "objetivo": "Calcular um desconto e um acréscimo em preço de material escolar e registrar o raciocínio.",
        "nota": "Catálogo curado não tem 9º ano; tema EF06MA14 (porcentagem) é o encaixe didático no 9º.",
    },
    {
        "data": "2026-09-19",
        "turma": "1ª Série A",
        "curso_ano": "1ª série",
        "codigo": "EM13MAT104",
        "tema": "Taxas e índices socioeconômicos (inflação, IDH)",
        "texto": (
            "Interpretar taxas e índices de natureza socioeconômica (índice de desenvolvimento "
            "humano, taxas de inflação, entre outros), investigando os processos de cálculo."
        ),
        "met": "criativa_design_thinking_express",
        "objetivo": "Ler um índice (inflação ou IDH) e explicar, em linguagem leiga, o que o número representa.",
    },
]


def login():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": HOMOLOG}, timeout=30)
    data = r.json() if r.content else {}
    if data.get("status") not in ("granted", "ok"):
        raise SystemExit(data)
    return s


def j(r):
    try:
        return r.json() if r.content else {}
    except Exception:
        return {"raw": (r.text or "")[:500]}


def pick_tema(s, disciplina, curso_ano, codigo_pref, fallback_tema, fallback_texto):
    g = s.get(
        f"{BASE}/api/daily/bncc-temas",
        params={"disciplina": disciplina, "curso_ano": curso_ano},
        timeout=30,
    )
    items = (j(g).get("items") or []) if g.ok else []
    hit = next(
        (
            t
            for t in items
            if isinstance(t, dict)
            and str(t.get("habilidade_codigo") or t.get("codigo") or "").upper() == codigo_pref
        ),
        None,
    )
    if not hit and items:
        hit = next(
            (
                t
                for t in items
                if isinstance(t, dict)
                and str(t.get("habilidade_codigo") or t.get("codigo") or "").upper() != "EF06MA25"
            ),
            items[0] if isinstance(items[0], dict) else None,
        )
    if not hit:
        return codigo_pref, fallback_tema, fallback_texto
    codigo = str(hit.get("habilidade_codigo") or hit.get("codigo") or codigo_pref)
    tema = str(hit.get("tema") or hit.get("titulo") or fallback_tema)
    texto = str(hit.get("texto") or hit.get("texto_oficial") or hit.get("descricao") or fallback_texto)
    if tema.lower().startswith("competência") or tema.lower().startswith("competencia"):
        tema = fallback_tema
    return codigo, tema, texto


def main():
    s = login()
    created = []
    bugs = []
    for spec in AULAS:
        disc = "Matemática"
        codigo, tema, texto = pick_tema(s, disc, spec["curso_ano"], spec["codigo"], spec["tema"], spec["texto"])
        payload = {
            "data_planejada": spec["data"],
            "turma_nome": spec["turma"],
            "tema_aula": f"{codigo} — {tema}",
            "ementa_topico": tema,
            "habilidades_bncc": [codigo],
            "objetivo_aprendizagem": spec["objetivo"],
            "acolhida": "Abertura em 3 minutos: o que este número/gráfico já diz antes da aula.",
            "conteudo_essencial": texto,
            "fechamento_checkout": "Um registro escrito do que ficou claro e de uma dúvida que resta.",
            "dinamica_ativa_id": spec["met"],
            "dinamica_ativa_fonte": "inove_local",
            "tipo_registro": "aula",
            "origem": "manual",
        }
        r = s.post(f"{BASE}/api/daily/planejar", json=payload, timeout=40)
        body = j(r)
        aula = body.get("aula") or {}
        aula_id = body.get("id") or aula.get("id")
        status_put = None
        if r.status_code == 409:
            bugs.append({"turma": spec["turma"], "data": spec["data"], "http": 409, "error": body.get("error"), "code": body.get("code")})
            alt = str(date.fromisoformat(spec["data"]).replace(day=min(28, date.fromisoformat(spec["data"]).day + 3)))
            payload["data_planejada"] = alt
            r = s.post(f"{BASE}/api/daily/planejar", json=payload, timeout=40)
            body = j(r)
            aula = body.get("aula") or {}
            aula_id = body.get("id") or aula.get("id")
            spec = {**spec, "data": payload["data_planejada"], "retentativa": True}
        if aula_id and r.ok:
            rp = s.put(f"{BASE}/api/daily/{aula_id}", json={"status": "planejado"}, timeout=20)
            status_put = (j(rp).get("aula") or {}).get("status")
        row = {
            "http_planejar": r.status_code,
            "error": body.get("error"),
            "code": body.get("code"),
            "aula_id": aula_id,
            "id_evento": aula.get("id_evento_agenda"),
            "turma": spec["turma"],
            "disciplina": disc,
            "codigo": codigo,
            "tema": tema,
            "data": spec["data"],
            "horario": f"{spec['data']}T12:00:00",
            "metodologia": spec["met"],
            "status": status_put or aula.get("status"),
            "nota": spec.get("nota"),
        }
        created.append(row)
        if r.status_code != 201:
            bugs.append(row)
    agenda = s.get(f"{BASE}/api/agenda-eventos", params={"mes": "2026-09"}, timeout=20)
    evs = []
    for e in j(agenda).get("eventos") or []:
        de = str(e.get("data_evento") or "")
        if de[:10] in {c["data"] for c in created} and e.get("tipo") == "aula_dia":
            evs.append({"id": e.get("id_evento"), "quando": de, "turma": e.get("turma"), "titulo": (e.get("titulo") or "")[:90], "status": e.get("status")})
    print(json.dumps({"criadas": created, "conflitos": bugs, "agenda_novas": evs}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
