"""
Estruturação Pedagógica — Etapa 4/4: importação em lote de aulas/eventos.

Escrita: serviço único upsert (agenda canônica + espelho Dia a Dia para tipo=aula).
Não aciona Wizard/IA.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from datetime import date, datetime, time, timedelta
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor, Json

from aulas_simples_models import ensure_aulas_simples_table
from db import get_conn
from import_friendly import (
    CAMPOS_DESTINO,
    format_data_br,
    make_id_externo,
    msg,
    sugerir_mapeamento,
    tipo_from_label,
    tipo_label,
)

importacoes_bp = Blueprint("importacoes", __name__)

DEFAULT_DURACAO_MIN = 50
TIPOS_ARQUIVO = frozenset({"aula", "evento"})
MAX_ROWS = 2000

_HEADER_ALIASES = {
    "id_externo": {"id_externo", "id", "external_id", "codigo"},
    "titulo": {"titulo", "title", "tema_aula", "nome", "titulo_da_aula"},
    "tipo": {"tipo", "type", "tipo_registro", "aula_ou_evento"},
    "data": {"data", "date", "data_planejada", "data_evento", "data_da_aula"},
    "hora_inicio": {"hora_inicio", "inicio", "hora", "start", "start_time"},
    "hora_fim": {"hora_fim", "fim", "end", "end_time"},
    "instituicao": {"instituicao", "instituicao_nome", "escola", "instituição"},
    "curso": {"curso", "curso_nome"},
    "disciplina": {"disciplina", "disciplina_nome", "materia", "matéria"},
    "assunto": {"assunto", "tema", "theme", "sequencia", "sequência", "unidade"},
    "vinculo_pai_id_externo": {
        "vinculo_pai_id_externo",
        "pai_id_externo",
        "id_pai_externo",
        "parent_id",
        "vinculo_pai",
    },
    "observacoes": {"observacoes", "obs", "nota", "notas", "descricao", "observações"},
}


def require_session(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user or not user.get("id_clie"):
            return jsonify({"error": msg("sem_sessao"), "code": "sem_sessao"}), 401
        return view(*args, **kwargs)

    return wrapped


def _id_clie() -> int:
    return int(session["user"]["id_clie"])


def _norm_key(raw: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(raw or "").strip().lower())


def _map_headers(keys: list[str]) -> dict[str, str]:
    """Mapa campo_canonico → chave original no dict da linha."""
    reverse: dict[str, str] = {}
    for k in keys:
        nk = _norm_key(k)
        for canon, aliases in _HEADER_ALIASES.items():
            if nk in aliases and canon not in reverse:
                reverse[canon] = k
                break
    return reverse


def _cell(row: dict, mapping: dict[str, str], field: str) -> str:
    key = mapping.get(field)
    if not key:
        return ""
    val = row.get(key)
    if val is None:
        return ""
    return str(val).strip()


def _parse_date(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text, fmt).date()
        except ValueError:
            continue
    # ISO datetime
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_time(raw: str) -> time | None:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _parse_csv(text: str) -> list[dict]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []
    return [dict(r) for r in reader]


def _parse_json(text: str) -> list[dict]:
    data = json.loads(text)
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("registros", "aulas", "eventos", "items", "data"):
            arr = data.get(key)
            if isinstance(arr, list):
                return [r for r in arr if isinstance(r, dict)]
    raise ValueError("JSON deve ser um array de objetos ou conter chave registros/aulas/eventos.")


def _extract_rows_from_request() -> tuple[list[dict], str, str]:
    """Retorna (rows, nome_arquivo, formato)."""
    if request.files:
        f = request.files.get("file") or request.files.get("arquivo")
        if f and f.filename:
            name = f.filename
            raw = f.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            lower = name.lower()
            if lower.endswith(".csv"):
                return _parse_csv(text), name, "csv"
            if lower.endswith(".json"):
                return _parse_json(text), name, "json"
            # sniff
            stripped = text.lstrip()
            if stripped.startswith("[") or stripped.startswith("{"):
                return _parse_json(text), name, "json"
            return _parse_csv(text), name, "csv"

    body = request.get_json(silent=True)
    if isinstance(body, dict):
        nome = str(body.get("nome_arquivo") or "payload.json")
        if "registros" in body or "aulas" in body or "eventos" in body:
            rows = _parse_json(json.dumps(body))
            return rows, nome, "json"
        if isinstance(body.get("conteudo"), str):
            fmt = str(body.get("formato") or "json").lower()
            text = body["conteudo"]
            if fmt == "csv":
                return _parse_csv(text), nome, "csv"
            return _parse_json(text), nome, "json"
    if isinstance(body, list):
        return [r for r in body if isinstance(r, dict)], "payload.json", "json"

    raise ValueError("Envie multipart (file) ou JSON com registros.")


def _normalize_row(
    raw: dict, line_no: int, *, id_clie: int | None = None
) -> tuple[dict | None, str | None]:
    mapping = _map_headers(list(raw.keys()))
    id_externo = _cell(raw, mapping, "id_externo")
    titulo = _cell(raw, mapping, "titulo")
    data_raw = _cell(raw, mapping, "data")
    if not titulo:
        return None, msg("titulo_ausente")
    data_val = _parse_date(data_raw)
    if not data_val:
        return None, msg("data_ausente") if not data_raw else msg("data_invalida")

    tipo = tipo_from_label(_cell(raw, mapping, "tipo") or "aula")
    if tipo not in TIPOS_ARQUIVO:
        tipo = "aula"

    instituicao = _cell(raw, mapping, "instituicao")
    disciplina = _cell(raw, mapping, "disciplina")
    assunto = _cell(raw, mapping, "assunto")
    if not id_externo:
        id_externo = make_id_externo(
            int(id_clie or 0),
            instituicao=instituicao,
            data_iso=data_val.isoformat(),
            titulo=titulo,
            disciplina=disciplina,
        )

    return {
        "line": line_no,
        "id_externo": id_externo[:160],
        "titulo": titulo[:200],
        "tipo": tipo,
        "data": data_val,
        "hora_inicio": _parse_time(_cell(raw, mapping, "hora_inicio")),
        "hora_fim": _parse_time(_cell(raw, mapping, "hora_fim")),
        "instituicao": instituicao,
        "curso": _cell(raw, mapping, "curso"),
        "disciplina": disciplina,
        "assunto": assunto[:200] if assunto else None,
        "vinculo_pai_id_externo": _cell(raw, mapping, "vinculo_pai_id_externo")[:160],
        "observacoes": _cell(raw, mapping, "observacoes")[:4000] or None,
    }, None


def _resolve_disciplina(
    cur, id_clie: int, instituicao: str, curso: str, disciplina: str
) -> tuple[int | None, int | None, list[str]]:
    """Best-effort por nome. Retorna (disciplina_id, duracao_min, avisos)."""
    avisos: list[str] = []
    if not disciplina and not curso and not instituicao:
        return None, None, avisos

    if not disciplina:
        if instituicao or curso:
            avisos.append(msg("vinculo_parcial"))
        return None, None, avisos

    sql = """
        SELECT d.id AS disciplina_id,
               c.id AS curso_id,
               i.id AS instituicao_id,
               p.duracao_padrao_aula_min,
               d.nome AS disciplina_nome,
               c.nome AS curso_nome,
               i.nome AS instituicao_nome
          FROM public.inove_disciplinas d
          JOIN public.inove_cursos c ON c.id = d.curso_id
          JOIN public.inove_periodos_letivos p ON p.id = c.periodo_letivo_id
          JOIN public.inove_instituicoes i ON i.id = p.instituicao_id
         WHERE i.id_clie = %s
           AND d.ativo = TRUE AND c.ativo = TRUE
           AND p.ativo = TRUE AND i.ativo = TRUE
           AND lower(trim(d.nome)) = lower(trim(%s))
    """
    params: list[Any] = [id_clie, disciplina]
    if curso:
        sql += " AND lower(trim(c.nome)) = lower(trim(%s))"
        params.append(curso)
    if instituicao:
        sql += " AND lower(trim(i.nome)) = lower(trim(%s))"
        params.append(instituicao)
    sql += " ORDER BY p.em_curso DESC, d.id ASC LIMIT 5"
    cur.execute(sql, params)
    rows = cur.fetchall() or []
    if not rows:
        avisos.append(msg("disciplina_nao_encontrada", nome=disciplina))
        return None, None, avisos
    row = rows[0]
    dur = row.get("duracao_padrao_aula_min")
    try:
        dur_i = int(dur) if dur is not None else None
    except (TypeError, ValueError):
        dur_i = None
    return int(row["disciplina_id"]), dur_i, avisos


def _apply_mapping(raw: dict, mapeamento: dict[str, str]) -> dict[str, str]:
    """Aplica coluna_arquivo → campo destino; retorna dict de campos canônicos."""
    out: dict[str, str] = {}
    for col, campo in (mapeamento or {}).items():
        if not campo:
            continue
        val = raw.get(col)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            out[campo] = text
    return out


def _linha_preview_from_fields(
    fields: dict[str, str],
    line_no: int,
    *,
    cur=None,
    id_clie: int | None = None,
) -> dict:
    titulo = (fields.get("titulo") or "").strip()
    data_raw = (fields.get("data") or "").strip()
    data_val = _parse_date(data_raw) if data_raw else None
    tipo = tipo_from_label(fields.get("tipo") or "aula")
    mensagens: list[str] = []
    status = "ok"

    if not titulo:
        mensagens.append(msg("titulo_ausente"))
        status = "pendente"
    if not data_raw:
        mensagens.append(msg("data_ausente"))
        status = "pendente"
    elif not data_val:
        mensagens.append(msg("data_invalida"))
        status = "pendente"

    disc_id = None
    avisos: list[str] = []
    if cur is not None and id_clie is not None and status != "pendente":
        disc_id, _dur, avisos = _resolve_disciplina(
            cur,
            id_clie,
            fields.get("instituicao") or "",
            fields.get("curso") or "",
            fields.get("disciplina") or "",
        )
        if avisos:
            status = "aviso"
            mensagens.extend(avisos)

    return {
        "linha": line_no,
        "titulo": titulo[:200],
        "data": format_data_br(data_val) if data_val else data_raw,
        "data_iso": data_val.isoformat() if data_val else "",
        "hora_inicio": (fields.get("hora_inicio") or "").strip()[:8],
        "hora_fim": (fields.get("hora_fim") or "").strip()[:8],
        "tipo": tipo,
        "tipo_label": tipo_label(tipo),
        "instituicao": (fields.get("instituicao") or "").strip()[:200],
        "curso": (fields.get("curso") or "").strip()[:200],
        "disciplina": (fields.get("disciplina") or "").strip()[:200],
        "assunto": (fields.get("assunto") or "").strip()[:200],
        "observacoes": (fields.get("observacoes") or "").strip()[:4000],
        "disciplina_id": disc_id,
        "status": status,
        "mensagens": mensagens,
    }


def _resumo_linhas(linhas: list[dict]) -> dict:
    prontas = sum(1 for L in linhas if L.get("status") in ("ok", "aviso"))
    pendentes = sum(1 for L in linhas if L.get("status") == "pendente")
    aulas = sum(1 for L in linhas if L.get("tipo") == "aula" and L.get("status") != "pendente")
    eventos = sum(
        1 for L in linhas if L.get("tipo") == "evento" and L.get("status") != "pendente"
    )
    return {
        "prontas": prontas,
        "pendentes": pendentes,
        "aulas": aulas,
        "eventos": eventos,
        "total": len(linhas),
    }


def _chain_by_assunto(cur, id_clie: int, gravados: list[dict]) -> None:
    """Encadeia por Assunto (+ disciplina) ordenando por data."""
    groups: dict[tuple, list[dict]] = {}
    for item in gravados:
        assunto = (item.get("assunto") or "").strip().lower()
        if not assunto:
            continue
        key = (assunto, item.get("disciplina_id") or 0)
        groups.setdefault(key, []).append(item)

    for items in groups.values():
        items.sort(
            key=lambda x: (
                x.get("data") or date.min,
                x.get("linha") or 0,
                x.get("id_evento") or 0,
            )
        )
        if len(items) < 2:
            continue
        pai = items[0]["id_evento"]
        for child in items[1:]:
            cid = child["id_evento"]
            if cid == pai:
                continue
            cur.execute(
                """
                UPDATE public.inove_agenda_eventos
                   SET id_evento_pai = %s
                 WHERE id_evento = %s AND id_clie = %s
                """,
                (pai, cid, id_clie),
            )
            child["id_evento_pai"] = pai


def _build_data_evento(d: date, hora_inicio: time | None) -> datetime:
    if hora_inicio:
        return datetime.combine(d, hora_inicio)
    return datetime.combine(d, time(12, 0, 0))


def _compute_hora_fim(
    hora_inicio: time | None,
    hora_fim: time | None,
    duracao_min: int,
) -> time | None:
    if hora_fim:
        return hora_fim
    if not hora_inicio:
        return None
    base = datetime.combine(date.today(), hora_inicio) + timedelta(minutes=duracao_min)
    return base.time()


def _find_agenda_by_externo(cur, id_clie: int, id_externo: str) -> dict | None:
    cur.execute(
        """
        SELECT id_evento, id_evento_pai, status, plan_data
          FROM public.inove_agenda_eventos
         WHERE id_clie = %s AND id_externo_importacao = %s
         LIMIT 1
        """,
        (id_clie, id_externo),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _find_aula_by_externo(cur, id_clie: int, id_externo: str) -> dict | None:
    cur.execute(
        """
        SELECT id, id_evento_agenda
          FROM public.inove_aulas_simples
         WHERE id_clie = %s AND id_externo_importacao = %s
         LIMIT 1
        """,
        (id_clie, id_externo),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def upsert_registro_importado(
    cur,
    *,
    id_clie: int,
    row: dict,
    disciplina_id: int | None,
    duracao_min: int,
    lote_id: int | None,
    origem: str = "importacao",
    is_from_school: bool = False,
) -> tuple[int, str, int | None]:
    """
    Upsert canônico na agenda; espelha Dia a Dia se tipo=aula.
    Retorna (id_evento, acao 'created'|'updated', aula_simples_id|None).

    `origem` padrão = importacao (arquivo). Push School usa planejamento_escola.
    """
    origem_val = (origem or "importacao").strip() or "importacao"
    id_externo = row["id_externo"]
    titulo = row["titulo"]
    tipo_reg = row["tipo"]
    data_evento = _build_data_evento(row["data"], row["hora_inicio"])
    hora_fim = _compute_hora_fim(row["hora_inicio"], row["hora_fim"], duracao_min)
    nota = row.get("observacoes")

    agenda_tipo = "aula_dia" if tipo_reg == "aula" else "geral"
    existing = _find_agenda_by_externo(cur, id_clie, id_externo)
    aula_id: int | None = None

    assunto = (row.get("assunto") or row.get("tema") or "").strip() or None
    if assunto:
        assunto = assunto[:200]

    meta = {
        "origem": origem_val,
        "id_externo": id_externo,
        "tipo_arquivo": tipo_reg,
        "importacao_lote_id": lote_id,
        "hora_inicio": row["hora_inicio"].strftime("%H:%M") if row.get("hora_inicio") else None,
        "hora_fim": hora_fim.strftime("%H:%M") if hora_fim else None,
        "duracao_min": duracao_min,
        "aguardando_planejamento": True,
        "tema": assunto,
        "assunto": assunto,
    }
    if origem_val == "planejamento_escola":
        meta["origem_school"] = "planejamento_escolar"

    if tipo_reg == "aula":
        existing_aula = _find_aula_by_externo(cur, id_clie, id_externo)
        if existing_aula:
            cur.execute(
                """
                UPDATE public.inove_aulas_simples
                   SET data_planejada = %s,
                       tema_aula = %s,
                       fechamento_checkout = COALESCE(%s, fechamento_checkout),
                       disciplina_id = %s,
                       tipo_registro = 'aula',
                       origem = %s,
                       status = CASE WHEN status = 'realizado' THEN status ELSE 'draft' END,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s AND id_clie = %s
             RETURNING id, id_evento_agenda
                """,
                (
                    row["data"],
                    titulo[:255],
                    nota or "",
                    disciplina_id,
                    origem_val,
                    int(existing_aula["id"]),
                    id_clie,
                ),
            )
            arow = cur.fetchone()
            aula_id = int(arow["id"])
            if arow.get("id_evento_agenda") and not existing:
                existing = {"id_evento": arow["id_evento_agenda"]}
        else:
            cur.execute(
                """
                INSERT INTO public.inove_aulas_simples (
                    id_clie, data_planejada, tema_aula, fechamento_checkout,
                    status, disciplina_id, tipo_registro, origem, id_externo_importacao
                ) VALUES (
                    %s, %s, %s, %s, 'draft', %s, 'aula', %s, %s
                )
                RETURNING id
                """,
                (
                    id_clie,
                    row["data"],
                    titulo[:255],
                    nota or "",
                    disciplina_id,
                    origem_val,
                    id_externo,
                ),
            )
            aula_id = int(cur.fetchone()["id"])
        meta["aula_simples_id"] = aula_id
        meta["ciclo"] = origem_val

    meta_json = json.dumps(meta, ensure_ascii=False)

    if existing:
        id_evento = int(existing["id_evento"])
        cur.execute(
            """
            UPDATE public.inove_agenda_eventos
               SET data_evento = %s,
                   titulo = %s,
                   nota_texto = %s,
                   tipo = %s,
                   meta_json = %s::jsonb,
                   disciplina_id = %s,
                   origem = %s,
                   id_externo_importacao = %s,
                   tema = %s,
                   is_from_school = CASE
                     WHEN %s THEN TRUE ELSE COALESCE(is_from_school, FALSE)
                   END,
                   status = CASE WHEN status = 'concluido' THEN status ELSE 'planejado' END
             WHERE id_evento = %s AND id_clie = %s
         RETURNING id_evento
            """,
            (
                data_evento,
                titulo,
                nota,
                agenda_tipo,
                meta_json,
                disciplina_id,
                origem_val,
                id_externo,
                assunto,
                bool(is_from_school),
                id_evento,
                id_clie,
            ),
        )
        acao = "updated"
    else:
        cur.execute(
            """
            INSERT INTO public.inove_agenda_eventos (
                id_clie, data_evento, titulo, nota_texto, status, tipo,
                meta_json, disciplina_id, origem, id_externo_importacao, tema,
                is_from_school
            ) VALUES (
                %s, %s, %s, %s, 'planejado', %s,
                %s::jsonb, %s, %s, %s, %s,
                %s
            )
            RETURNING id_evento
            """,
            (
                id_clie,
                data_evento,
                titulo,
                nota,
                agenda_tipo,
                meta_json,
                disciplina_id,
                origem_val,
                id_externo,
                assunto,
                bool(is_from_school),
            ),
        )
        id_evento = int(cur.fetchone()["id_evento"])
        acao = "created"

    if aula_id is not None:
        cur.execute(
            """
            UPDATE public.inove_aulas_simples
               SET id_evento_agenda = %s, updated_at = CURRENT_TIMESTAMP
             WHERE id = %s AND id_clie = %s
            """,
            (id_evento, aula_id, id_clie),
        )

    return id_evento, acao, aula_id


def _ensure_import_schema(conn) -> None:
    ensure_aulas_simples_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS id_externo_importacao VARCHAR(160);
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS tema VARCHAR(200);
            ALTER TABLE public.inove_agenda_eventos
                ADD COLUMN IF NOT EXISTS is_from_school BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE public.inove_aulas_simples
                ADD COLUMN IF NOT EXISTS id_externo_importacao VARCHAR(160);
            CREATE TABLE IF NOT EXISTS public.inove_importacoes_lote (
                id               BIGSERIAL PRIMARY KEY,
                id_clie          INTEGER NOT NULL
                                   REFERENCES public.ctdi_clie (id_clie) ON DELETE CASCADE,
                nome_arquivo     TEXT NOT NULL DEFAULT '',
                formato          VARCHAR(10) NOT NULL DEFAULT 'json',
                total_registros  INTEGER NOT NULL DEFAULT 0,
                total_sucesso    INTEGER NOT NULL DEFAULT 0,
                total_erro       INTEGER NOT NULL DEFAULT 0,
                total_aviso      INTEGER NOT NULL DEFAULT 0,
                relatorio_json   JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE public.inove_importacoes_lote
                ADD COLUMN IF NOT EXISTS canal VARCHAR(32) NOT NULL DEFAULT 'arquivo';

            ALTER TABLE public.inove_agenda_eventos
                DROP CONSTRAINT IF EXISTS chk_inove_agenda_eventos_origem;
            ALTER TABLE public.inove_agenda_eventos
                ADD CONSTRAINT chk_inove_agenda_eventos_origem
                CHECK (origem IN (
                    'manual', 'wizard_ia', 'importacao',
                    'comunicado_escola', 'alocacao_escola', 'planejamento_escola',
                    'convite_colaborador'
                ));
            ALTER TABLE public.inove_aulas_simples
                DROP CONSTRAINT IF EXISTS chk_inove_aulas_simples_origem;
            ALTER TABLE public.inove_aulas_simples
                ADD CONSTRAINT chk_inove_aulas_simples_origem
                CHECK (origem IN (
                    'manual', 'wizard_ia', 'importacao', 'planejamento_escola'
                ));
            """
        )


@importacoes_bp.post("/api/importacoes/aulas-eventos")
@require_session
def importar_aulas_eventos():
    id_clie = _id_clie()
    try:
        rows_raw, nome_arquivo, formato = _extract_rows_from_request()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        print(f"[importacoes] parse: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao ler o arquivo."}), 400

    if not rows_raw:
        return jsonify({"error": "Arquivo sem registros."}), 400
    if len(rows_raw) > MAX_ROWS:
        return jsonify({"error": f"Limite de {MAX_ROWS} registros por arquivo."}), 400

    relatorio: list[dict] = []
    externals: dict[str, dict] = {}  # id_externo → row normalizado
    line_errors = 0

    for idx, raw in enumerate(rows_raw, start=1):
        if not isinstance(raw, dict):
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": None,
                    "status": "erro",
                    "mensagem": "registro inválido (não é objeto)",
                }
            )
            line_errors += 1
            continue
        norm, err = _normalize_row(raw, idx, id_clie=id_clie)
        if err:
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": _cell(raw, _map_headers(list(raw.keys())), "id_externo") or None,
                    "status": "erro",
                    "mensagem": err,
                }
            )
            line_errors += 1
            continue
        if norm["id_externo"] in externals:
            relatorio.append(
                {
                    "linha": idx,
                    "id_externo": norm["id_externo"],
                    "status": "erro",
                    "mensagem": "id_externo duplicado no arquivo",
                }
            )
            line_errors += 1
            continue
        externals[norm["id_externo"]] = norm

    id_map: dict[str, int] = {}  # id_externo → id_evento
    total_sucesso = 0
    total_aviso = 0
    created = 0
    updated = 0

    try:
        with get_conn() as conn:
            _ensure_import_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO public.inove_importacoes_lote (
                        id_clie, nome_arquivo, formato,
                        total_registros, total_sucesso, total_erro, total_aviso,
                        relatorio_json
                    ) VALUES (%s, %s, %s, %s, 0, 0, 0, '[]'::jsonb)
                    RETURNING id
                    """,
                    (id_clie, nome_arquivo[:500], formato, len(rows_raw)),
                )
                lote_id = int(cur.fetchone()["id"])

                # Passada 1 — upsert
                for id_ext, row in externals.items():
                    avisos: list[str] = []
                    try:
                        disc_id, dur_periodo, avisos_res = _resolve_disciplina(
                            cur,
                            id_clie,
                            row["instituicao"],
                            row["curso"],
                            row["disciplina"],
                        )
                        avisos.extend(avisos_res)
                        duracao = dur_periodo or DEFAULT_DURACAO_MIN
                        id_evento, acao, aula_id = upsert_registro_importado(
                            cur,
                            id_clie=id_clie,
                            row=row,
                            disciplina_id=disc_id,
                            duracao_min=duracao,
                            lote_id=lote_id,
                        )
                        id_map[id_ext] = id_evento
                        total_sucesso += 1
                        if acao == "created":
                            created += 1
                        else:
                            updated += 1
                        if avisos:
                            total_aviso += 1
                        relatorio.append(
                            {
                                "linha": row["line"],
                                "id_externo": id_ext,
                                "status": "ok",
                                "acao": acao,
                                "id_evento": id_evento,
                                "aula_simples_id": aula_id,
                                "disciplina_id": disc_id,
                                "avisos": avisos,
                                "mensagem": (
                                    ("criado" if acao == "created" else "atualizado")
                                    + (f"; {'; '.join(avisos)}" if avisos else "")
                                ),
                            }
                        )
                    except Exception as exc:
                        print(f"[importacoes] linha {row['line']}: {exc}", file=sys.stderr)
                        line_errors += 1
                        relatorio.append(
                            {
                                "linha": row["line"],
                                "id_externo": id_ext,
                                "status": "erro",
                                "mensagem": f"falha ao persistir: {exc}",
                            }
                        )

                # Passada 2 — vínculos pai (só dentro do lote / mapa atual)
                for id_ext, row in externals.items():
                    pai_ext = row.get("vinculo_pai_id_externo") or ""
                    if not pai_ext:
                        continue
                    id_evento = id_map.get(id_ext)
                    if not id_evento:
                        continue
                    id_pai = id_map.get(pai_ext)
                    if not id_pai:
                        # tenta registro já existente do professor com mesmo id_externo
                        prev = _find_agenda_by_externo(cur, id_clie, pai_ext)
                        id_pai = int(prev["id_evento"]) if prev else None
                    if not id_pai:
                        total_aviso += 1
                        for item in relatorio:
                            if item.get("id_externo") == id_ext and item.get("status") == "ok":
                                avisos = list(item.get("avisos") or [])
                                msg = (
                                    f"vinculo_pai_id_externo '{pai_ext}' "
                                    "não resolvido neste lote"
                                )
                                avisos.append(msg)
                                item["avisos"] = avisos
                                item["mensagem"] = (item.get("mensagem") or "") + f"; {msg}"
                                break
                        continue
                    if id_pai == id_evento:
                        continue
                    cur.execute(
                        """
                        UPDATE public.inove_agenda_eventos
                           SET id_evento_pai = %s
                         WHERE id_evento = %s AND id_clie = %s
                        """,
                        (id_pai, id_evento, id_clie),
                    )
                    for item in relatorio:
                        if item.get("id_externo") == id_ext and item.get("status") == "ok":
                            item["id_evento_pai"] = id_pai
                            break

                # Ordena relatório por linha
                relatorio.sort(key=lambda r: (r.get("linha") or 0, r.get("id_externo") or ""))

                cur.execute(
                    """
                    UPDATE public.inove_importacoes_lote
                       SET total_sucesso = %s,
                           total_erro = %s,
                           total_aviso = %s,
                           relatorio_json = %s
                     WHERE id = %s AND id_clie = %s
                    """,
                    (
                        total_sucesso,
                        line_errors,
                        total_aviso,
                        Json(relatorio),
                        lote_id,
                        id_clie,
                    ),
                )
                conn.commit()
    except pg_errors.UndefinedTable:
        return jsonify(
            {
                "error": "Schema de importação pendente. Aplique a migration 011.",
                "code": "schema_pending",
            }
        ), 503
    except Exception as exc:
        print(f"[importacoes] lote: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao processar importação."}), 500

    return jsonify(
        {
            "ok": True,
            "lote_id": lote_id,
            "nome_arquivo": nome_arquivo,
            "formato": formato,
            "total_registros": len(rows_raw),
            "total_sucesso": total_sucesso,
            "total_erro": line_errors,
            "total_aviso": total_aviso,
            "total_criados": created,
            "total_atualizados": updated,
            "relatorio": relatorio,
        }
    ), 201


@importacoes_bp.get("/api/importacoes")
@require_session
def listar_importacoes():
    id_clie = _id_clie()
    try:
        with get_conn() as conn:
            _ensure_import_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, nome_arquivo, formato, total_registros,
                           total_sucesso, total_erro, total_aviso, created_at
                      FROM public.inove_importacoes_lote
                     WHERE id_clie = %s
                     ORDER BY created_at DESC, id DESC
                     LIMIT 50
                    """,
                    (id_clie,),
                )
                rows = []
                for r in cur.fetchall():
                    item = dict(r)
                    if item.get("created_at"):
                        item["created_at"] = item["created_at"].isoformat()
                    rows.append(item)
        return jsonify({"ok": True, "importacoes": rows})
    except pg_errors.UndefinedTable:
        return jsonify({"error": "Schema pendente.", "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[importacoes] list: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao listar importações."}), 500


@importacoes_bp.get("/api/importacoes/<int:lote_id>")
@require_session
def detalhe_importacao(lote_id: int):
    id_clie = _id_clie()
    try:
        with get_conn() as conn:
            _ensure_import_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, nome_arquivo, formato, total_registros,
                           total_sucesso, total_erro, total_aviso,
                           relatorio_json, created_at
                      FROM public.inove_importacoes_lote
                     WHERE id = %s AND id_clie = %s
                    """,
                    (lote_id, id_clie),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "Importação não encontrada."}), 404
                item = dict(row)
                if item.get("created_at"):
                    item["created_at"] = item["created_at"].isoformat()
                rel = item.get("relatorio_json")
                if isinstance(rel, str):
                    try:
                        rel = json.loads(rel)
                    except Exception:
                        rel = []
                item["relatorio"] = rel if isinstance(rel, list) else []
                del item["relatorio_json"]
                # Resumo pedagógico para cartões / corrigir pendências
                rel_list = item["relatorio"]
                aulas = sum(
                    1
                    for r in rel_list
                    if r.get("status") in ("ok", "aviso") and r.get("tipo") == "aula"
                )
                eventos = sum(
                    1
                    for r in rel_list
                    if r.get("status") in ("ok", "aviso") and r.get("tipo") == "evento"
                )
                item["resumo"] = {
                    "aulas": aulas or item.get("total_sucesso") or 0,
                    "eventos": eventos,
                    "pendentes": item.get("total_erro") or 0,
                    "avisos": item.get("total_aviso") or 0,
                }
                item["linhas_pendentes"] = [
                    {
                        "linha": r.get("linha"),
                        "titulo": r.get("titulo") or "",
                        "data": r.get("data") or "",
                        "data_iso": r.get("data_iso") or "",
                        "hora_inicio": r.get("hora_inicio") or "",
                        "hora_fim": r.get("hora_fim") or "",
                        "tipo": r.get("tipo") or "aula",
                        "tipo_label": tipo_label(r.get("tipo") or "aula"),
                        "instituicao": r.get("instituicao") or "",
                        "curso": r.get("curso") or "",
                        "disciplina": r.get("disciplina") or "",
                        "assunto": r.get("assunto") or "",
                        "observacoes": r.get("observacoes") or "",
                        "status": "pendente",
                        "mensagens": [r.get("mensagem")] if r.get("mensagem") else [msg("pendente")],
                    }
                    for r in rel_list
                    if r.get("status") == "erro"
                ]
        return jsonify({"ok": True, "importacao": item})
    except pg_errors.UndefinedTable:
        return jsonify({"error": msg("falha_gravar"), "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[importacoes] detalhe: {exc}", file=sys.stderr)
        return jsonify({"error": msg("falha_gravar")}), 500


@importacoes_bp.post("/api/importacoes/pre-visualizar")
@require_session
def pre_visualizar_importacao():
    """Interpreta o arquivo sem gravar nada."""
    id_clie = _id_clie()
    try:
        rows_raw, nome_arquivo, _formato = _extract_rows_from_request()
    except ValueError:
        return jsonify({"error": msg("arquivo_invalido"), "code": "arquivo_invalido"}), 400
    except Exception as exc:
        print(f"[importacoes] preview parse: {exc}", file=sys.stderr)
        return jsonify({"error": msg("arquivo_invalido"), "code": "arquivo_invalido"}), 400

    if not rows_raw:
        return jsonify({"error": msg("arquivo_vazio"), "code": "arquivo_vazio"}), 400
    if len(rows_raw) > MAX_ROWS:
        return jsonify({"error": msg("arquivo_grande"), "code": "arquivo_grande"}), 400

    mapeamento_req = None
    if request.files or request.form:
        raw_map = request.form.get("mapeamento")
        if raw_map:
            try:
                mapeamento_req = json.loads(raw_map)
            except Exception:
                mapeamento_req = None
    else:
        body = request.get_json(silent=True)
        if isinstance(body, dict):
            mapeamento_req = body.get("mapeamento")

    # Colunas na ordem da primeira linha
    colunas: list[str] = []
    seen: set[str] = set()
    for raw in rows_raw:
        if not isinstance(raw, dict):
            continue
        for k in raw.keys():
            sk = str(k)
            if sk not in seen:
                seen.add(sk)
                colunas.append(sk)

    mapeamento = mapeamento_req if isinstance(mapeamento_req, dict) else sugerir_mapeamento(colunas)
    # Completa chaves faltantes
    for col in colunas:
        mapeamento.setdefault(col, sugerir_mapeamento([col]).get(col, ""))

    linhas: list[dict] = []
    try:
        with get_conn() as conn:
            _ensure_import_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for idx, raw in enumerate(rows_raw, start=1):
                    if not isinstance(raw, dict):
                        linhas.append(
                            {
                                "linha": idx,
                                "titulo": "",
                                "data": "",
                                "data_iso": "",
                                "hora_inicio": "",
                                "hora_fim": "",
                                "tipo": "aula",
                                "tipo_label": "Aula",
                                "instituicao": "",
                                "curso": "",
                                "disciplina": "",
                                "assunto": "",
                                "observacoes": "",
                                "status": "pendente",
                                "mensagens": [msg("pendente")],
                            }
                        )
                        continue
                    fields = _apply_mapping(raw, mapeamento)
                    # Se mapeamento vazio, tenta aliases automáticos
                    if not fields:
                        mapping = _map_headers(list(raw.keys()))
                        fields = {
                            f: _cell(raw, mapping, f)
                            for f in (
                                "titulo",
                                "data",
                                "hora_inicio",
                                "hora_fim",
                                "tipo",
                                "instituicao",
                                "curso",
                                "disciplina",
                                "assunto",
                                "observacoes",
                            )
                            if mapping.get(f)
                        }
                    linhas.append(
                        _linha_preview_from_fields(fields, idx, cur=cur, id_clie=id_clie)
                    )
    except Exception as exc:
        print(f"[importacoes] preview: {exc}", file=sys.stderr)
        # Sem DB ainda — valida só estrutura
        linhas = []
        for idx, raw in enumerate(rows_raw, start=1):
            if not isinstance(raw, dict):
                continue
            fields = _apply_mapping(raw, mapeamento)
            linhas.append(_linha_preview_from_fields(fields, idx))

    return jsonify(
        {
            "ok": True,
            "nome_arquivo": nome_arquivo,
            "colunas_arquivo": colunas,
            "mapeamento": mapeamento,
            "campos_destino": CAMPOS_DESTINO,
            "linhas": linhas,
            "resumo": _resumo_linhas(linhas),
        }
    )


@importacoes_bp.post("/api/importacoes/confirmar")
@require_session
def confirmar_importacao():
    """Grava linhas já conferidas/ajustadas pelo professor."""
    id_clie = _id_clie()
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"error": msg("arquivo_invalido")}), 400

    nome_arquivo = str(body.get("nome_arquivo") or "planilha de planejamento")[:500]
    linhas_in = body.get("linhas")
    if not isinstance(linhas_in, list) or not linhas_in:
        return jsonify({"error": msg("arquivo_vazio"), "code": "arquivo_vazio"}), 400
    if len(linhas_in) > MAX_ROWS:
        return jsonify({"error": msg("arquivo_grande"), "code": "arquivo_grande"}), 400

    relatorio: list[dict] = []
    prontas: list[dict] = []
    line_errors = 0

    for idx, raw in enumerate(linhas_in, start=1):
        if not isinstance(raw, dict):
            line_errors += 1
            relatorio.append(
                {
                    "linha": idx,
                    "status": "erro",
                    "mensagem": msg("pendente"),
                    "tipo": "aula",
                }
            )
            continue
        line_no = int(raw.get("linha") or idx)
        fields = {
            "titulo": str(raw.get("titulo") or "").strip(),
            "data": str(raw.get("data_iso") or raw.get("data") or "").strip(),
            "hora_inicio": str(raw.get("hora_inicio") or "").strip(),
            "hora_fim": str(raw.get("hora_fim") or "").strip(),
            "tipo": str(raw.get("tipo") or "aula"),
            "instituicao": str(raw.get("instituicao") or "").strip(),
            "curso": str(raw.get("curso") or "").strip(),
            "disciplina": str(raw.get("disciplina") or "").strip(),
            "assunto": str(raw.get("assunto") or "").strip(),
            "observacoes": str(raw.get("observacoes") or "").strip(),
        }
        preview = _linha_preview_from_fields(fields, line_no)
        snap = {
            "linha": line_no,
            "titulo": preview["titulo"],
            "data": preview["data"],
            "data_iso": preview["data_iso"],
            "hora_inicio": preview["hora_inicio"],
            "hora_fim": preview["hora_fim"],
            "tipo": preview["tipo"],
            "instituicao": preview["instituicao"],
            "curso": preview["curso"],
            "disciplina": preview["disciplina"],
            "assunto": preview["assunto"],
            "observacoes": preview["observacoes"],
        }
        if preview["status"] == "pendente":
            line_errors += 1
            relatorio.append(
                {
                    **snap,
                    "status": "erro",
                    "mensagem": "; ".join(preview["mensagens"]) or msg("pendente"),
                }
            )
            continue

        data_val = _parse_date(fields["data"])
        id_ext = make_id_externo(
            id_clie,
            instituicao=fields["instituicao"],
            data_iso=data_val.isoformat() if data_val else "",
            titulo=fields["titulo"],
            disciplina=fields["disciplina"],
        )
        prontas.append(
            {
                "line": line_no,
                "id_externo": id_ext,
                "titulo": fields["titulo"][:200],
                "tipo": preview["tipo"],
                "data": data_val,
                "hora_inicio": _parse_time(fields["hora_inicio"]),
                "hora_fim": _parse_time(fields["hora_fim"]),
                "instituicao": fields["instituicao"],
                "curso": fields["curso"],
                "disciplina": fields["disciplina"],
                "assunto": fields["assunto"] or None,
                "vinculo_pai_id_externo": "",
                "observacoes": fields["observacoes"] or None,
                "_snap": snap,
            }
        )

    total_sucesso = 0
    total_aviso = 0
    created = 0
    updated = 0
    gravados: list[dict] = []

    try:
        with get_conn() as conn:
            _ensure_import_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO public.inove_importacoes_lote (
                        id_clie, nome_arquivo, formato,
                        total_registros, total_sucesso, total_erro, total_aviso,
                        relatorio_json
                    ) VALUES (%s, %s, %s, %s, 0, 0, 0, '[]'::jsonb)
                    RETURNING id
                    """,
                    (id_clie, nome_arquivo, "csv", len(linhas_in)),
                )
                lote_id = int(cur.fetchone()["id"])

                for row in prontas:
                    avisos: list[str] = []
                    snap = row.pop("_snap")
                    try:
                        disc_id, dur_periodo, avisos_res = _resolve_disciplina(
                            cur,
                            id_clie,
                            row["instituicao"],
                            row["curso"],
                            row["disciplina"],
                        )
                        avisos.extend(avisos_res)
                        duracao = dur_periodo or DEFAULT_DURACAO_MIN
                        id_evento, acao, aula_id = upsert_registro_importado(
                            cur,
                            id_clie=id_clie,
                            row=row,
                            disciplina_id=disc_id,
                            duracao_min=duracao,
                            lote_id=lote_id,
                        )
                        total_sucesso += 1
                        if acao == "created":
                            created += 1
                        else:
                            updated += 1
                        if avisos:
                            total_aviso += 1
                        friendly = msg("atualizado") if acao == "updated" else msg("criado")
                        if avisos:
                            friendly = friendly + " " + " ".join(avisos)
                        relatorio.append(
                            {
                                **snap,
                                "status": "aviso" if avisos else "ok",
                                "acao": acao,
                                "id_evento": id_evento,
                                "aula_simples_id": aula_id,
                                "disciplina_id": disc_id,
                                "avisos": avisos,
                                "mensagem": friendly,
                            }
                        )
                        gravados.append(
                            {
                                "id_evento": id_evento,
                                "linha": row["line"],
                                "data": row["data"],
                                "assunto": row.get("assunto"),
                                "disciplina_id": disc_id,
                            }
                        )
                    except Exception as exc:
                        print(f"[importacoes] confirmar linha {row['line']}: {exc}", file=sys.stderr)
                        line_errors += 1
                        relatorio.append(
                            {
                                **snap,
                                "status": "erro",
                                "mensagem": msg("falha_gravar"),
                            }
                        )

                _chain_by_assunto(cur, id_clie, gravados)

                relatorio.sort(key=lambda r: (r.get("linha") or 0,))
                cur.execute(
                    """
                    UPDATE public.inove_importacoes_lote
                       SET total_sucesso = %s,
                           total_erro = %s,
                           total_aviso = %s,
                           relatorio_json = %s
                     WHERE id = %s AND id_clie = %s
                    """,
                    (
                        total_sucesso,
                        line_errors,
                        total_aviso,
                        Json(relatorio),
                        lote_id,
                        id_clie,
                    ),
                )
                conn.commit()
    except pg_errors.UndefinedTable:
        return jsonify({"error": msg("falha_gravar"), "code": "schema_pending"}), 503
    except Exception as exc:
        print(f"[importacoes] confirmar: {exc}", file=sys.stderr)
        return jsonify({"error": msg("falha_gravar")}), 500

    resumo_txt_parts = []
    if created or updated:
        # Conta por tipo nas linhas ok
        n_aulas = sum(1 for r in relatorio if r.get("status") in ("ok", "aviso") and r.get("tipo") == "aula")
        n_ev = sum(1 for r in relatorio if r.get("status") in ("ok", "aviso") and r.get("tipo") == "evento")
        resumo_txt_parts.append(
            f"Foram registradas {n_aulas} aula{'s' if n_aulas != 1 else ''}"
            f" e {n_ev} evento{'s' if n_ev != 1 else ''}."
        )
    if line_errors:
        resumo_txt_parts.append(
            f"{line_errors} linha{'s' if line_errors != 1 else ''} ficou pendente até ser corrigida."
        )

    return jsonify(
        {
            "ok": True,
            "lote_id": lote_id,
            "nome_arquivo": nome_arquivo,
            "total_registros": len(linhas_in),
            "total_sucesso": total_sucesso,
            "total_erro": line_errors,
            "total_aviso": total_aviso,
            "total_criados": created,
            "total_atualizados": updated,
            "mensagem": " ".join(resumo_txt_parts) or "Importação concluída.",
            "relatorio": relatorio,
        }
    ), 201
