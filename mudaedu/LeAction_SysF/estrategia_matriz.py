"""Matriz canônica OKR PanelDX (dx_direcionadores → dx_objetivos → dx_krs)."""

from __future__ import annotations

import psycopg2.extras

# Ordem fixa alinhada ao Panorama Executivo / migration 014
SLUGS_DIRECIONADORES = (
    "digitalizacao_organizacional",
    "engajamento_comunidade",
    "capacitacao_docente",
    "prontidao_tecnologica",
    "novos_modelos_negocio",
)

META_POR_SLUG = {
    "digitalizacao_organizacional": ("reducao_custo", "Redução de Custo", "📉"),
    "engajamento_comunidade": ("aumento_receita", "Aumento de Receita", "💰"),
    "capacitacao_docente": ("reducao_custo", "Redução de Custo", "📉"),
    "prontidao_tecnologica": ("reducao_custo", "Redução de Custo", "📉"),
    "novos_modelos_negocio": ("aumento_receita", "Aumento de Receita", "💰"),
}

NIVEL_IMPLEMENTACAO_LABELS = {
    "nao_iniciado": "Não Iniciado",
    "em_andamento": "Em Andamento",
    "avancado": "Avançado",
}

NIVEL_IMPLEMENTACAO_PROGRESSO = {
    "nao_iniciado": 0,
    "em_andamento": 45,
    "avancado": 85,
}

STATUS_ATIVIDADE_CONCLUIDA = "Entregue"


def label_nivel(nivel: str | None) -> str:
    key = (nivel or "nao_iniciado").strip().lower()
    return NIVEL_IMPLEMENTACAO_LABELS.get(key, "Não Iniciado")


def progresso_nivel(nivel: str | None) -> int:
    key = (nivel or "nao_iniciado").strip().lower()
    return NIVEL_IMPLEMENTACAO_PROGRESSO.get(key, 0)


def derivar_nivel_implementacao(progresso_pct: int) -> str:
    """Deriva rótulo de nível a partir do progresso calculado (somente exibição)."""
    pct = int(progresso_pct or 0)
    if pct >= 80:
        return "avancado"
    if pct > 0:
        return "em_andamento"
    return "nao_iniciado"


def progresso_kr_de_atividades(cur, id_kr: int) -> dict:
    """Progresso bottom-up de um KR: atividades concluídas / total."""
    cur.execute(
        """
        SELECT COUNT(*)::int AS total,
               COUNT(*) FILTER (WHERE status_ativ = %s)::int AS concluidas
        FROM public.ctdi_okr_atividades
        WHERE id_kr = %s
        """,
        (STATUS_ATIVIDADE_CONCLUIDA, int(id_kr)),
    )
    row = cur.fetchone() or {}
    total = int(row.get("total") or 0)
    concluidas = int(row.get("concluidas") or 0)
    pct = int(round(concluidas / total * 100)) if total > 0 else 0
    return {
        "progresso_pct": pct,
        "total_atividades": total,
        "atividades_concluidas": concluidas,
    }


def calcular_progresso_objetivo_atividades(cur, id_obj_dt: int) -> tuple[int, list[dict]]:
    """Média do progresso dos KRs do objetivo com base nas atividades de sprint."""
    cur.execute(
        """
        SELECT id_kr, dx_kr_id, nome_kr, desc_kr
        FROM public.ctdi_okr_krs
        WHERE id_obj_dt = %s
        ORDER BY dx_kr_id NULLS LAST, id_kr
        """,
        (int(id_obj_dt),),
    )
    krs_rows = cur.fetchall()
    if not krs_rows:
        return 0, []

    progressos = []
    detalhes = []
    for kr in krs_rows:
        stats = progresso_kr_de_atividades(cur, kr["id_kr"])
        progressos.append(stats["progresso_pct"])
        detalhes.append({**dict(kr), **stats})

    media = int(round(sum(progressos) / len(progressos))) if progressos else 0
    return media, detalhes


def calcular_progresso_krs(krs: list[dict]) -> int:
    if not krs:
        return 0
    total = 0
    count = 0
    for kr in krs:
        vi = float(kr.get("valor_inicial") or 0)
        va = float(kr.get("valor_alvo") or 0)
        vat = float(kr.get("valor_atual") or 0)
        if va != vi:
            pct = min(100, max(0, abs(vat - vi) / abs(va - vi) * 100))
        elif kr.get("meta_cliente"):
            pct = 50
        else:
            pct = 0
        total += pct
        count += 1
    return int(round(total / count)) if count else 0


def carregar_arvore_matriz_okr(conn) -> list[dict]:
    """Retorna Direcionadores → Objetivos → KRs do catálogo global."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT d.id, d.nome, d.descricao,
                   o.id AS objetivo_id, o.titulo AS objetivo_titulo,
                   k.id AS kr_id, k.descricao AS kr_descricao,
                   k.metrica_alvo_placeholder
            FROM public.dx_direcionadores d
            LEFT JOIN public.dx_objetivos o ON o.direcionador_id = d.id
            LEFT JOIN public.dx_krs k ON k.objetivo_id = o.id
            ORDER BY d.id, o.id, k.id
            """
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    tree: dict[int, dict] = {}
    for row in rows:
        did = row["id"]
        if did not in tree:
            slug = SLUGS_DIRECIONADORES[did - 1] if did <= len(SLUGS_DIRECIONADORES) else None
            tree[did] = {
                "id": did,
                "nome": row["nome"],
                "descricao": row["descricao"],
                "slug": slug,
                "objetivos": {},
            }
        oid = row.get("objetivo_id")
        if oid and oid not in tree[did]["objetivos"]:
            tree[did]["objetivos"][oid] = {
                "id": oid,
                "titulo": row["objetivo_titulo"],
                "krs": [],
            }
        kid = row.get("kr_id")
        if kid and oid:
            tree[did]["objetivos"][oid]["krs"].append(
                {
                    "id": kid,
                    "descricao": row["kr_descricao"],
                    "metrica_alvo_placeholder": row["metrica_alvo_placeholder"],
                }
            )

    result = []
    for did in sorted(tree.keys()):
        d = tree[did]
        d["objetivos"] = [d["objetivos"][k] for k in sorted(d["objetivos"].keys())]
        result.append(d)
    return result


def formatar_catalogo_objetivos_prompt(arvore: list[dict]) -> str:
    """Texto para o prompt da Gênese IA — lista objetivos canônicos com IDs."""
    linhas = [
        "\n--- MATRIZ CANÔNICA DE OKRs (associe CADA sprint a um id_objetivo exato) ---\n"
    ]
    for d in arvore:
        linhas.append(f"DIRECIONADOR {d['id']}: {d['nome']}")
        for o in d.get("objetivos") or []:
            linhas.append(f"  id_objetivo={o['id']} | {o['titulo']}")
    linhas.append(
        "\nREGRA: todo item em roadmap_estrategico e sprints_resolucao DEVE incluir "
        "'id_objetivo' (inteiro da lista acima) e justificar o impacto no objetivo escolhido.\n"
    )
    return "\n".join(linhas)


def resolver_hierarquia_objetivo(conn, objetivo_id: int | None) -> dict | None:
    """Direcionador + objetivo + KRs canônicos para uma sprint."""
    if not objetivo_id:
        return None
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT o.id AS objetivo_id, o.titulo AS objetivo_titulo,
                   d.id AS direcionador_id, d.nome AS direcionador_nome, d.descricao AS direcionador_descricao
            FROM public.dx_objetivos o
            JOIN public.dx_direcionadores d ON d.id = o.direcionador_id
            WHERE o.id = %s
            """,
            (int(objetivo_id),),
        )
        base = cur.fetchone()
        if not base:
            return None
        cur.execute(
            """
            SELECT id, descricao, metrica_alvo_placeholder
            FROM public.dx_krs
            WHERE objetivo_id = %s
            ORDER BY id
            """,
            (int(objetivo_id),),
        )
        krs = [dict(r) for r in cur.fetchall()]
        slug = None
        did = base["direcionador_id"]
        if did and did <= len(SLUGS_DIRECIONADORES):
            slug = SLUGS_DIRECIONADORES[did - 1]
        return {
            **dict(base),
            "slug": slug,
            "krs": krs,
        }
    finally:
        cur.close()


def garantir_okr_cliente_desde_matriz(conn, id_clie: int) -> None:
    """Instancia a matriz canônica em ctdi_okr_* para o cliente (idempotente)."""
    arvore = carregar_arvore_matriz_okr(conn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for d in arvore:
            slug = d.get("slug") or ""
            meta = META_POR_SLUG.get(slug, ("reducao_custo", "Redução de Custo", "📉"))
            meta_fin, meta_label, icone = meta

            cur.execute(
                """
                SELECT id_direc FROM public.ctdi_okr_direcionadores
                WHERE id_clie = %s AND (dx_direcionador_id = %s OR slug_catalogo = %s)
                LIMIT 1
                """,
                (id_clie, d["id"], slug),
            )
            row_d = cur.fetchone()
            if row_d:
                id_direc = row_d["id_direc"]
                cur.execute(
                    """
                    UPDATE public.ctdi_okr_direcionadores
                    SET dx_direcionador_id = %s, slug_catalogo = COALESCE(slug_catalogo, %s)
                    WHERE id_direc = %s
                    """,
                    (d["id"], slug, id_direc),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO public.ctdi_okr_direcionadores
                        (id_clie, nome_direc, desc_direc, kpi_descricao,
                         meta_receita_alvo, meta_custo_alvo, status_direc,
                         slug_catalogo, meta_financeira, icone, dx_direcionador_id)
                    VALUES (%s, %s, %s, %s, 0, 0, 'Ativo', %s, %s, %s, %s)
                    RETURNING id_direc
                    """,
                    (
                        id_clie,
                        d["nome"],
                        d.get("descricao") or f"Pilar estratégico — {meta_label}.",
                        f"Indicador-guia: {meta_label}",
                        slug,
                        meta_fin,
                        icone,
                        d["id"],
                    ),
                )
                id_direc = cur.fetchone()["id_direc"]

            for o in d.get("objetivos") or []:
                cur.execute(
                    """
                    SELECT id_obj_dt FROM public.ctdi_okr_objetivos_dt
                    WHERE id_direc = %s AND dx_objetivo_id = %s
                    LIMIT 1
                    """,
                    (id_direc, o["id"]),
                )
                row_o = cur.fetchone()
                if row_o:
                    id_obj_dt = row_o["id_obj_dt"]
                else:
                    cur.execute(
                        """
                        INSERT INTO public.ctdi_okr_objetivos_dt
                            (id_direc, nome_obj, desc_obj, status_obj, dx_objetivo_id, nivel_implementacao)
                        VALUES (%s, %s, %s, 'Ativo', %s, 'nao_iniciado')
                        RETURNING id_obj_dt
                        """,
                        (id_direc, o["titulo"], o["titulo"], o["id"]),
                    )
                    id_obj_dt = cur.fetchone()["id_obj_dt"]

                for kr in o.get("krs") or []:
                    cur.execute(
                        """
                        SELECT id_kr FROM public.ctdi_okr_krs
                        WHERE id_obj_dt = %s AND dx_kr_id = %s
                        LIMIT 1
                        """,
                        (id_obj_dt, kr["id"]),
                    )
                    if cur.fetchone():
                        continue
                    cur.execute(
                        """
                        INSERT INTO public.ctdi_okr_krs
                            (id_obj_dt, nome_kr, desc_kr, kpi_nome,
                             valor_inicial, valor_alvo, valor_atual, status_kr, dx_kr_id)
                        VALUES (%s, %s, %s, %s, 0, 100, 0, 'Em Andamento', %s)
                        """,
                        (
                            id_obj_dt,
                            kr["descricao"][:200],
                            kr["descricao"],
                            kr.get("metrica_alvo_placeholder") or "Meta",
                            kr["id"],
                        ),
                    )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def carregar_resumo_okr_cliente(conn, id_clie: int) -> list[dict]:
    """Linhas planas para tabela mestre (todos os objetivos, canônicos e personalizados)."""
    painel = carregar_painel_okr_cliente(conn, int(id_clie))
    return painel.get("rows") or []


def _enriquecer_direcionador_painel(row: dict) -> dict:
    slug = (row.get("slug_catalogo") or "").strip()
    meta = META_POR_SLUG.get(slug, ("reducao_custo", "Redução de Custo", "🎯"))
    meta_fin, meta_label, icone_default = meta
    is_fixo = bool(slug or row.get("dx_direcionador_id"))
    mf = row.get("meta_financeira") or meta_fin
    if slug:
        label = meta_label
    elif mf == "aumento_receita":
        label = "Aumento de Receita"
    else:
        label = "Redução de Custo"
    ordem = SLUGS_DIRECIONADORES.index(slug) if slug in SLUGS_DIRECIONADORES else 999
    return {
        **row,
        "is_catalogo_fixo": is_fixo,
        "icone": row.get("icone") or icone_default,
        "meta_financeira": mf,
        "meta_label": label,
        "ordem_catalogo": ordem,
    }


def _objetivo_painel_from_row(cur, row: dict, direc: dict) -> dict:
    progresso, _ = calcular_progresso_objetivo_atividades(cur, row["id_obj_dt"])
    cur.execute(
        """
        SELECT COUNT(*)::int AS total_krs
        FROM public.ctdi_okr_krs
        WHERE id_obj_dt = %s
        """,
        (row["id_obj_dt"],),
    )
    total_krs = int((cur.fetchone() or {}).get("total_krs") or 0)
    nivel = derivar_nivel_implementacao(progresso)
    titulo = row.get("titulo_canonico") or row["nome_obj"]
    return {
        "id_obj_dt": row["id_obj_dt"],
        "dx_objetivo_id": row.get("dx_objetivo_id"),
        "objetivo_titulo": titulo,
        "nome_obj": row["nome_obj"],
        "is_canonico": row.get("dx_objetivo_id") is not None,
        "nivel_implementacao": nivel,
        "nivel_label": label_nivel(nivel),
        "progresso_pct": progresso,
        "total_krs": total_krs,
        "direcionador_id": direc["id_direc"],
        "direcionador_nome": direc["nome_direc"],
        "direcionador_slug": direc.get("slug_catalogo"),
        "direcionador_icone": direc.get("icone"),
    }


def carregar_painel_okr_cliente(conn, id_clie: int) -> dict:
    """Painel agrupado por direcionador — inclui pilares vazios e objetivos personalizados."""
    garantir_okr_cliente_desde_matriz(conn, int(id_clie))
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id_direc, nome_direc, desc_direc, kpi_descricao, slug_catalogo,
                   meta_financeira, icone, dx_direcionador_id,
                   meta_receita_alvo, meta_custo_alvo, status_direc
            FROM public.ctdi_okr_direcionadores
            WHERE id_clie = %s
            ORDER BY
                CASE WHEN slug_catalogo IS NOT NULL OR dx_direcionador_id IS NOT NULL THEN 0 ELSE 1 END,
                dx_direcionador_id NULLS LAST,
                id_direc ASC
            """,
            (id_clie,),
        )
        direc_rows = [_enriquecer_direcionador_painel(dict(r)) for r in cur.fetchall()]
        direcionadores = []
        flat_rows = []
        soma_progresso = 0
        total_obj = 0

        for d in direc_rows:
            cur.execute(
                """
                SELECT o.id_obj_dt, o.dx_objetivo_id, o.nome_obj, o.nivel_implementacao,
                       dxo.titulo AS titulo_canonico
                FROM public.ctdi_okr_objetivos_dt o
                LEFT JOIN public.dx_objetivos dxo ON dxo.id = o.dx_objetivo_id
                WHERE o.id_direc = %s
                ORDER BY o.dx_objetivo_id NULLS LAST, o.id_obj_dt ASC
                """,
                (d["id_direc"],),
            )
            objetivos = []
            soma_direc = 0
            for o_row in cur.fetchall():
                obj = _objetivo_painel_from_row(cur, dict(o_row), d)
                objetivos.append(obj)
                flat_rows.append(obj)
                soma_direc += obj["progresso_pct"]
                soma_progresso += obj["progresso_pct"]
                total_obj += 1

            progresso_direc = round(soma_direc / len(objetivos)) if objetivos else 0
            direcionadores.append({
                "id_direc": d["id_direc"],
                "nome_direc": d["nome_direc"],
                "desc_direc": d.get("desc_direc") or "",
                "kpi_descricao": d.get("kpi_descricao") or "",
                "slug_catalogo": d.get("slug_catalogo"),
                "meta_financeira": d.get("meta_financeira"),
                "meta_label": d.get("meta_label"),
                "icone": d.get("icone"),
                "is_catalogo_fixo": d["is_catalogo_fixo"],
                "meta_receita_alvo": float(d.get("meta_receita_alvo") or 0),
                "meta_custo_alvo": float(d.get("meta_custo_alvo") or 0),
                "progresso_pct": progresso_direc,
                "total_objetivos": len(objetivos),
                "objetivos": objetivos,
                "ordem_catalogo": d.get("ordem_catalogo", 999),
            })

        direcionadores.sort(
            key=lambda x: (
                0 if x["is_catalogo_fixo"] else 1,
                x.get("ordem_catalogo", 999),
                x["id_direc"],
            )
        )

        stats = {
            "total_direcionadores": len(direcionadores),
            "total_objetivos": total_obj,
            "pilares_fixos": sum(1 for d in direcionadores if d["is_catalogo_fixo"]),
            "pilares_custom": sum(1 for d in direcionadores if not d["is_catalogo_fixo"]),
            "progresso_medio": round(soma_progresso / total_obj) if total_obj else 0,
        }
        return {"direcionadores": direcionadores, "rows": flat_rows, "stats": stats}
    finally:
        cur.close()


def _titulo_kr_cliente(kr: dict) -> str:
    """Preferência: texto editado no cliente → canônico → nome."""
    for key in ("desc_kr", "nome_kr", "desc_canonica"):
        val = (kr.get(key) or "").strip()
        if val:
            return val
    return f"KR {kr.get('id_kr') or ''}".strip()


def carregar_detalhe_objetivo_cliente(conn, id_obj_dt: int) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT o.id_obj_dt, o.dx_objetivo_id, o.nome_obj, o.nivel_implementacao,
                   d.id_direc, d.nome_direc, d.id_clie, dxo.titulo AS titulo_canonico
            FROM public.ctdi_okr_objetivos_dt o
            JOIN public.ctdi_okr_direcionadores d ON d.id_direc = o.id_direc
            LEFT JOIN public.dx_objetivos dxo ON dxo.id = o.dx_objetivo_id
            WHERE o.id_obj_dt = %s
            """,
            (id_obj_dt,),
        )
        obj = cur.fetchone()
        if not obj:
            return None
        cur.execute(
            """
            SELECT k.id_kr, k.nome_kr, k.desc_kr, k.kpi_nome, k.meta_cliente,
                   k.valor_inicial, k.valor_alvo, k.valor_atual, k.dx_kr_id,
                   COALESCE(k.ativo, true) AS ativo,
                   dxk.descricao AS desc_canonica,
                   dxk.metrica_alvo_placeholder
            FROM public.ctdi_okr_krs k
            LEFT JOIN public.dx_krs dxk ON dxk.id = k.dx_kr_id
            WHERE k.id_obj_dt = %s
            ORDER BY COALESCE(k.ativo, true) DESC, k.dx_kr_id NULLS LAST, k.id_kr
            """,
            (id_obj_dt,),
        )
        # fetchall ANTES do cálculo de progresso — o progresso reutiliza o mesmo cursor
        kr_rows = list(cur.fetchall())
        progresso_obj, kr_stats = calcular_progresso_objetivo_atividades(cur, id_obj_dt)
        stats_by_kr = {s["id_kr"]: s for s in kr_stats}
        krs = []
        for kr in kr_rows:
            extra = stats_by_kr.get(kr["id_kr"], {})
            krs.append({
                "id_kr": kr["id_kr"],
                "dx_kr_id": kr.get("dx_kr_id"),
                "ativo": bool(kr.get("ativo", True)),
                "is_canonico": kr.get("dx_kr_id") is not None,
                "nome_kr": kr.get("nome_kr") or "",
                "desc_kr": kr.get("desc_kr") or "",
                "descricao": _titulo_kr_cliente(kr),
                "meta_placeholder": kr.get("metrica_alvo_placeholder") or kr.get("kpi_nome"),
                "meta_cliente": kr.get("meta_cliente") or "",
                "valor_inicial": float(kr["valor_inicial"] or 0),
                "valor_alvo": float(kr["valor_alvo"] or 100),
                "valor_atual": float(kr["valor_atual"] or 0),
                "progresso_pct": extra.get("progresso_pct", 0),
                "total_atividades": extra.get("total_atividades", 0),
                "atividades_concluidas": extra.get("atividades_concluidas", 0),
            })
        nivel = derivar_nivel_implementacao(progresso_obj)
        return {
            "id_obj_dt": obj["id_obj_dt"],
            "id_clie": obj["id_clie"],
            "direcionador_nome": obj["nome_direc"],
            "objetivo_titulo": obj.get("titulo_canonico") or obj["nome_obj"],
            "nivel_implementacao": nivel,
            "nivel_label": label_nivel(nivel),
            "progresso_pct": progresso_obj,
            "krs": krs,
        }
    finally:
        cur.close()


def carregar_cascata_okr_atividade(
    conn, id_clie: int, id_sprn: int | None = None
) -> list[dict]:
    """Direcionadores → objetivos → KRs para o modal de atividades (filtro opcional por sprint)."""
    painel = carregar_painel_okr_cliente(conn, int(id_clie))
    objetivo_sprint_dx = None
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if id_sprn:
            cur.execute(
                "SELECT objetivo_id FROM public.ctdi_sprn WHERE id_sprn = %s",
                (int(id_sprn),),
            )
            sp = cur.fetchone()
            raw_obj = sp.get("objetivo_id") if sp else None
            objetivo_sprint_dx = int(raw_obj) if raw_obj is not None else None

        cur.execute(
            """
            SELECT o.id_direc, o.id_obj_dt,
                   k.id_kr, k.nome_kr, k.desc_kr,
                   dxk.descricao AS desc_canonica
            FROM public.ctdi_okr_objetivos_dt o
            JOIN public.ctdi_okr_krs k
              ON k.id_obj_dt = o.id_obj_dt
             AND COALESCE(k.ativo, true) = true
            LEFT JOIN public.dx_krs dxk ON dxk.id = k.dx_kr_id
            JOIN public.ctdi_okr_direcionadores d ON d.id_direc = o.id_direc
            WHERE d.id_clie = %s
            ORDER BY k.dx_kr_id NULLS LAST, k.id_kr
            """,
            (int(id_clie),),
        )
        krs_por_obj: dict[int, list[dict]] = {}
        for row in cur.fetchall():
            oid = int(row["id_obj_dt"])
            krs_por_obj.setdefault(oid, []).append({
                "id_kr": row["id_kr"],
                "titulo": _titulo_kr_cliente(row),
            })
    finally:
        cur.close()

    saida: list[dict] = []
    for d in painel.get("direcionadores") or []:
        objetivos_out: list[dict] = []
        for obj in d.get("objetivos") or []:
            dx_raw = obj.get("dx_objetivo_id")
            dx_obj_id = int(dx_raw) if dx_raw is not None else None
            if objetivo_sprint_dx is not None and dx_obj_id != objetivo_sprint_dx:
                continue
            oid = int(obj["id_obj_dt"])
            krs_obj = krs_por_obj.get(oid, [])
            if not krs_obj:
                continue
            objetivos_out.append({
                "id_obj_dt": oid,
                "titulo": obj.get("objetivo_titulo") or obj.get("nome_obj") or f"Objetivo {oid}",
                "dx_objetivo_id": dx_obj_id,
                "krs": krs_obj,
            })
        # Com filtro de sprint, esconde direcionadores vazios (evita "nenhum KR" ao escolher pilar errado)
        if objetivo_sprint_dx is not None and not objetivos_out:
            continue
        saida.append({
            "id_direc": d["id_direc"],
            "nome": d.get("nome_direc") or "Direcionador",
            "slug": d.get("slug_catalogo"),
            "is_catalogo_fixo": bool(d.get("is_catalogo_fixo")),
            "ordem_catalogo": d.get("ordem_catalogo", 999),
            "objetivos": objetivos_out,
            "objetivo_sprint_filtrado": objetivo_sprint_dx is not None,
        })
    return saida


def carregar_krs_para_sprint(conn, id_sprn: int, id_clie: int) -> list[dict]:
    """KRs do cliente filtrados pelo objetivo canônico da sprint (para dropdown de atividades)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT s.objetivo_id, s.name_sprn
            FROM public.ctdi_sprn s
            WHERE s.id_sprn = %s
            """,
            (int(id_sprn),),
        )
        sprint = cur.fetchone()
        objetivo_id = sprint.get("objetivo_id") if sprint else None

        base_sql = """
            SELECT k.id_kr, k.nome_kr, k.desc_kr, k.dx_kr_id,
                   dxk.descricao AS desc_canonica,
                   dxk.metrica_alvo_placeholder,
                   o.nome_obj, o.dx_objetivo_id,
                   d.nome_direc
            FROM public.ctdi_okr_krs k
            JOIN public.ctdi_okr_objetivos_dt o ON o.id_obj_dt = k.id_obj_dt
            JOIN public.ctdi_okr_direcionadores d ON d.id_direc = o.id_direc
            LEFT JOIN public.dx_krs dxk ON dxk.id = k.dx_kr_id
            WHERE d.id_clie = %s
              AND COALESCE(k.ativo, true) = true
        """
        params: list = [int(id_clie)]
        if objetivo_id:
            base_sql += " AND o.dx_objetivo_id = %s"
            params.append(int(objetivo_id))
        base_sql += " ORDER BY k.dx_kr_id NULLS LAST, k.id_kr"
        cur.execute(base_sql, params)
        rows = []
        for r in cur.fetchall():
            stats = progresso_kr_de_atividades(cur, r["id_kr"])
            rows.append({
                "id_kr": r["id_kr"],
                "dx_kr_id": r["dx_kr_id"],
                "nome_kr": r.get("nome_kr"),
                "descricao": _titulo_kr_cliente(r),
                "meta_placeholder": r.get("metrica_alvo_placeholder"),
                "objetivo_titulo": r.get("nome_obj"),
                "direcionador_nome": r.get("nome_direc"),
                "dx_objetivo_id": r.get("dx_objetivo_id"),
                **stats,
            })
        return rows
    finally:
        cur.close()


def atualizar_objetivo_cliente(conn, id_obj_dt: int, *, nivel_implementacao: str | None = None) -> bool:
    """Nível de implementação é calculado (bottom-up) — não persiste alteração manual."""
    _ = nivel_implementacao
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM public.ctdi_okr_objetivos_dt WHERE id_obj_dt = %s",
            (id_obj_dt,),
        )
        ok = cur.fetchone() is not None
        return ok
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def atualizar_kr_cliente(
    conn,
    id_kr: int,
    *,
    meta_cliente: str | None = None,
    valor_alvo: float | None = None,
    valor_atual: float | None = None,
    nome_kr: str | None = None,
    desc_kr: str | None = None,
    kpi_nome: str | None = None,
    ativo: bool | None = None,
) -> bool:
    cur = conn.cursor()
    try:
        sets = []
        params = []
        if meta_cliente is not None:
            sets.append("meta_cliente = %s")
            params.append(meta_cliente.strip())
        if valor_alvo is not None:
            sets.append("valor_alvo = %s")
            params.append(valor_alvo)
        if valor_atual is not None:
            sets.append("valor_atual = %s")
            params.append(valor_atual)
        if nome_kr is not None:
            nome = nome_kr.strip()[:200]
            sets.append("nome_kr = %s")
            params.append(nome)
            # Mantém desc alinhado ao título quando o cliente edita
            if desc_kr is None:
                sets.append("desc_kr = %s")
                params.append(nome)
        if desc_kr is not None:
            sets.append("desc_kr = %s")
            params.append(desc_kr.strip())
        if kpi_nome is not None:
            sets.append("kpi_nome = %s")
            params.append(kpi_nome.strip()[:150] or "Meta")
        if ativo is not None:
            sets.append("ativo = %s")
            params.append(bool(ativo))
        if not sets:
            return False
        sets.append("data_revisao = CURRENT_TIMESTAMP")
        params.append(id_kr)
        cur.execute(
            f"UPDATE public.ctdi_okr_krs SET {', '.join(sets)} WHERE id_kr = %s",
            params,
        )
        ok = cur.rowcount > 0
        conn.commit()
        return ok
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def criar_kr_cliente(
    conn,
    id_obj_dt: int,
    *,
    nome_kr: str,
    kpi_nome: str | None = None,
    meta_cliente: str | None = None,
    valor_alvo: float = 100,
) -> int | None:
    """Cria KR personalizado do cliente (sem dx_kr_id — elegível a atividades)."""
    nome = (nome_kr or "").strip()
    if not nome:
        return None
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT 1 FROM public.ctdi_okr_objetivos_dt WHERE id_obj_dt = %s",
            (int(id_obj_dt),),
        )
        if not cur.fetchone():
            return None
        cur.execute(
            """
            INSERT INTO public.ctdi_okr_krs
                (id_obj_dt, nome_kr, desc_kr, kpi_nome,
                 valor_inicial, valor_alvo, valor_atual, status_kr, meta_cliente, ativo)
            VALUES (%s, %s, %s, %s, 0, %s, 0, 'Em Andamento', %s, true)
            RETURNING id_kr
            """,
            (
                int(id_obj_dt),
                nome[:200],
                nome,
                (kpi_nome or "Meta personalizada").strip()[:150],
                float(valor_alvo or 100),
                (meta_cliente or "").strip() or None,
            ),
        )
        new_id = int(cur.fetchone()["id_kr"])
        conn.commit()
        return new_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
