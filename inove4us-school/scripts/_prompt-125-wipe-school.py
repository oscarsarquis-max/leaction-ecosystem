#!/usr/bin/env python3
"""125 — backup + wipe transacional da camada de instância da Escola Teste (School).

Não toca catálogo/domínio (metodologia, AEE, BNCC, currículo, gestores, cadastro).
Uso (no host School):
  PYTHONPATH=backend backend/.venv/bin/python /tmp/_prompt-125-wipe-school.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
BACKUP_DIR = Path("/tmp/prompt-125-backup")
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

KEEP_FP = [
    "school_gestores",
    "school_periodos_letivos",
    "school_disciplinas",
    "school_metodologias_catalogo",
    "school_metodologias_org",
    "school_metodologia_config",
    "school_aee_matrizes",
    "school_aee_metodologias_canonico",
    "school_bncc_temas_canonico",
]


def q(cur, sql, params=None):
    cur.execute(sql, params or ())
    return [dict(r) for r in (cur.fetchall() or [])]


def n(cur, sql, params=None) -> int:
    row = q(cur, sql, params)
    return int((row[0] or {}).get("n") or 0) if row else 0


def exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
        (table,),
    )
    return bool(cur.fetchone())


def fingerprint(cur, table: str) -> dict:
    if table in ("school_metodologias_catalogo", "school_aee_metodologias_canonico", "school_bncc_temas_canonico"):
        cur.execute(f"SELECT id::text AS id FROM public.{table} ORDER BY id::text")
    else:
        cur.execute(
            f"SELECT id::text AS id FROM public.{table} WHERE instituicao_id = %s ORDER BY id::text",
            (INST,),
        )
    ids = [r["id"] for r in (cur.fetchall() or [])]
    return {
        "table": table,
        "n": len(ids),
        "sha256": hashlib.sha256(",".join(ids).encode()).hexdigest(),
    }


def dump_json(name: str, payload) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"{STAMP}_{name}.json"
    path.write_text(json.dumps(payload, default=str, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    out: dict = {"prompt": 125, "stamp": STAMP, "instituicao_id": INST}
    with get_conn() as conn:
        conn.autocommit = False
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            inst = q(
                cur,
                "SELECT id::text, razao_social FROM public.school_instituicoes WHERE id=%s",
                (INST,),
            )
            if not inst or inst[0]["razao_social"] != "Escola Teste":
                conn.rollback()
                print(json.dumps({"ok": False, "reason": "instituicao_mismatch", "row": inst}, default=str))
                return 2
            other = n(
                cur,
                "SELECT COUNT(*)::int AS n FROM public.school_instituicoes WHERE id IS DISTINCT FROM %s",
                (INST,),
            )
            out["outras_instituicoes"] = other
            out["fp_before"] = [fingerprint(cur, t) for t in KEEP_FP]
            dump_json("keep_fp_before", out["fp_before"])

            backups = {}
            backups["planejamento"] = q(cur, "SELECT * FROM public.school_planejamento_escolar WHERE instituicao_id=%s", (INST,))
            backups["comunicacoes"] = q(cur, "SELECT * FROM public.school_comunicacoes_eventos WHERE instituicao_id=%s", (INST,))
            backups["avisos"] = q(cur, "SELECT * FROM public.school_avisos_mesa WHERE instituicao_id=%s", (INST,))
            backups["curadoria_met"] = q(cur, "SELECT * FROM public.school_curadoria_metodologias WHERE instituicao_id=%s", (INST,))
            backups["curadoria_pei"] = q(cur, "SELECT * FROM public.school_curadoria_pei WHERE instituicao_id=%s", (INST,))
            backups["planos"] = q(cur, "SELECT * FROM public.school_planos_aula_espelhados WHERE instituicao_id=%s", (INST,))
            backups["pei_doc"] = q(cur, "SELECT * FROM public.school_pei_aluno_documental WHERE instituicao_id=%s", (INST,))
            backups["pei_alunos"] = q(cur, "SELECT * FROM public.school_pei_alunos WHERE instituicao_id=%s", (INST,))
            backups["alocacoes"] = q(cur, "SELECT * FROM public.school_alocacoes_docentes WHERE instituicao_id=%s", (INST,))
            backups["habilitacao"] = q(
                cur,
                """
                SELECT h.* FROM public.school_professor_disciplina_habilitacao h
                  JOIN public.school_professores_vinculo v ON v.id=h.professor_vinculo_id
                 WHERE v.instituicao_id=%s
                """,
                (INST,),
            )
            backups["prof_turma"] = q(
                cur,
                """
                SELECT pt.* FROM public.school_professor_turma pt
                  JOIN public.school_professores_vinculo v ON v.id=pt.professor_vinculo_id
                 WHERE v.instituicao_id=%s
                """,
                (INST,),
            )
            backups["vinculos"] = q(cur, "SELECT * FROM public.school_professores_vinculo WHERE instituicao_id=%s", (INST,))
            backups["alunos"] = q(cur, "SELECT * FROM public.school_alunos WHERE instituicao_id=%s", (INST,))
            backups["turmas"] = q(cur, "SELECT * FROM public.school_turmas WHERE instituicao_id=%s", (INST,))
            dump_json("school_transactional", {k: len(v) for k, v in backups.items()})
            dump_json("school_transactional_rows", backups)
            out["backup_counts"] = {k: len(v) for k, v in backups.items()}

            deleted = {}

            cur.execute("DELETE FROM public.school_planejamento_escolar WHERE instituicao_id=%s", (INST,))
            deleted["planejamento"] = cur.rowcount
            cur.execute("DELETE FROM public.school_comunicacoes_eventos WHERE instituicao_id=%s", (INST,))
            deleted["comunicacoes"] = cur.rowcount
            cur.execute("DELETE FROM public.school_avisos_mesa WHERE instituicao_id=%s", (INST,))
            deleted["avisos"] = cur.rowcount
            cur.execute("DELETE FROM public.school_curadoria_metodologias WHERE instituicao_id=%s", (INST,))
            deleted["curadoria_met"] = cur.rowcount
            cur.execute("DELETE FROM public.school_curadoria_pei WHERE instituicao_id=%s", (INST,))
            deleted["curadoria_pei"] = cur.rowcount
            cur.execute("DELETE FROM public.school_planos_aula_espelhados WHERE instituicao_id=%s", (INST,))
            deleted["planos"] = cur.rowcount
            cur.execute("DELETE FROM public.school_pei_aluno_documental WHERE instituicao_id=%s", (INST,))
            deleted["pei_doc"] = cur.rowcount
            cur.execute("DELETE FROM public.school_pei_alunos WHERE instituicao_id=%s", (INST,))
            deleted["pei_alunos"] = cur.rowcount
            cur.execute("DELETE FROM public.school_alocacoes_docentes WHERE instituicao_id=%s", (INST,))
            deleted["alocacoes"] = cur.rowcount
            cur.execute(
                """
                DELETE FROM public.school_professor_turma pt
                 USING public.school_professores_vinculo v
                 WHERE pt.professor_vinculo_id=v.id AND v.instituicao_id=%s
                """,
                (INST,),
            )
            deleted["prof_turma"] = cur.rowcount
            cur.execute(
                """
                DELETE FROM public.school_professor_disciplina_habilitacao h
                 USING public.school_professores_vinculo v
                 WHERE h.professor_vinculo_id=v.id AND v.instituicao_id=%s
                """,
                (INST,),
            )
            deleted["habilitacao"] = cur.rowcount
            cur.execute("DELETE FROM public.school_professores_vinculo WHERE instituicao_id=%s", (INST,))
            deleted["vinculos"] = cur.rowcount
            cur.execute("DELETE FROM public.school_alunos WHERE instituicao_id=%s", (INST,))
            deleted["alunos"] = cur.rowcount
            cur.execute("DELETE FROM public.school_turmas WHERE instituicao_id=%s", (INST,))
            deleted["turmas"] = cur.rowcount

            # Safety: no other institution lost rows in delete-set
            leftover = {
                "planejamento": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_planejamento_escolar WHERE instituicao_id=%s", (INST,)),
                "comunicacoes": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_comunicacoes_eventos WHERE instituicao_id=%s", (INST,)),
                "avisos": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_avisos_mesa WHERE instituicao_id=%s", (INST,)),
                "curadoria_met": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_curadoria_metodologias WHERE instituicao_id=%s", (INST,)),
                "curadoria_pei": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_curadoria_pei WHERE instituicao_id=%s", (INST,)),
                "planos": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_planos_aula_espelhados WHERE instituicao_id=%s", (INST,)),
                "pei_alunos": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_pei_alunos WHERE instituicao_id=%s", (INST,)),
                "alocacoes": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_alocacoes_docentes WHERE instituicao_id=%s", (INST,)),
                "vinculos": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_professores_vinculo WHERE instituicao_id=%s", (INST,)),
                "alunos": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_alunos WHERE instituicao_id=%s", (INST,)),
                "turmas": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_turmas WHERE instituicao_id=%s", (INST,)),
            }
            out["leftover_escola_teste"] = leftover
            if any(v != 0 for v in leftover.values()):
                conn.rollback()
                out["ok"] = False
                out["reason"] = "leftover_not_zero"
                print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
                return 3

            other_turmas = n(cur, "SELECT COUNT(*)::int AS n FROM public.school_turmas WHERE instituicao_id IS DISTINCT FROM %s", (INST,))
            other_alunos = n(cur, "SELECT COUNT(*)::int AS n FROM public.school_alunos WHERE instituicao_id IS DISTINCT FROM %s", (INST,))
            out["other_inst_turmas"] = other_turmas
            out["other_inst_alunos"] = other_alunos

            out["fp_after"] = [fingerprint(cur, t) for t in KEEP_FP]
            dump_json("keep_fp_after", out["fp_after"])
            drift = []
            for a, b in zip(out["fp_before"], out["fp_after"]):
                if a != b:
                    drift.append({"before": a, "after": b})
            if drift:
                conn.rollback()
                out["ok"] = False
                out["reason"] = "keep_fingerprint_drift"
                out["drift"] = drift
                print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
                return 4

            keep_counts = {
                "instituicao": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_instituicoes WHERE id=%s", (INST,)),
                "gestores": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_gestores WHERE instituicao_id=%s", (INST,)),
                "periodos": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_periodos_letivos WHERE instituicao_id=%s", (INST,)),
                "cursos": n(
                    cur,
                    """
                    SELECT COUNT(*)::int AS n FROM public.school_cursos c
                      JOIN public.school_periodos_letivos p ON p.id=c.periodo_letivo_id
                     WHERE p.instituicao_id=%s
                    """,
                    (INST,),
                ),
                "disciplinas": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_disciplinas WHERE instituicao_id=%s", (INST,)),
                "curso_disciplinas": n(
                    cur,
                    """
                    SELECT COUNT(*)::int AS n FROM public.school_curso_disciplinas cd
                      JOIN public.school_cursos c ON c.id=cd.curso_id
                      JOIN public.school_periodos_letivos p ON p.id=c.periodo_letivo_id
                     WHERE p.instituicao_id=%s
                    """,
                    (INST,),
                ),
                "metodologias_catalogo": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_metodologias_catalogo"),
                "metodologias_org": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_metodologias_org WHERE instituicao_id=%s", (INST,)),
                "aee_matrizes": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_aee_matrizes WHERE instituicao_id=%s", (INST,)),
                "aee_ativo": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_aee_matrizes WHERE instituicao_id=%s AND status='ativo'", (INST,)),
                "aee_canonico": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_aee_metodologias_canonico"),
                "bncc_temas": n(cur, "SELECT COUNT(*)::int AS n FROM public.school_bncc_temas_canonico"),
                "bncc_oficial": n(cur, "SELECT COUNT(*)::int AS n FROM public.bncc_habilidades_oficial"),
            }
            out["keep_counts_after"] = keep_counts
            expected_keep = {
                "instituicao": 1,
                "gestores": 5,
                "periodos": 1,
                "cursos": 5,
                "disciplinas": 15,
                "curso_disciplinas": 21,
                "metodologias_catalogo": 39,
                "metodologias_org": 4,
                "aee_matrizes": 22,
                "aee_ativo": 8,
                "aee_canonico": 312,
                "bncc_temas": 539,
                "bncc_oficial": 1721,
            }
            keep_mismatch = {k: {"got": keep_counts[k], "expected": v} for k, v in expected_keep.items() if keep_counts[k] != v}
            if keep_mismatch:
                conn.rollback()
                out["ok"] = False
                out["reason"] = "keep_count_mismatch"
                out["keep_mismatch"] = keep_mismatch
                print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
                return 5

            out["gestores_after"] = q(
                cur,
                "SELECT email, nome, ativo FROM public.school_gestores WHERE instituicao_id=%s ORDER BY email",
                (INST,),
            )
            out["deleted"] = deleted
            conn.commit()
            out["ok"] = True
            out["committed"] = True

    dump_json("school_wipe_report", out)
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
