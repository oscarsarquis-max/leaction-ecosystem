#!/usr/bin/env python3
"""Prompt 70 — enriquecer Escola Teste (produção), sem criar instituição nova.

Idempotente por nome/matrícula/e-mail. Não imprime senhas.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
if not (ROOT / "backend").exists():
    ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402

from aee_canonico import get_canonico  # noqa: E402
from b2c_integration_service import (  # noqa: E402
    dispatch_event_to_b2c,
    dispatch_pei_override_updated,
)
from db import get_conn  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "seed_et", ROOT / "scripts" / "seed-escola-teste-producao.py"
)
seed_et = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(seed_et)

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG_EMAIL = "homologador@leaction.com.br"
ANO = 2026

NOVOS_PROFESSORES = (
    ("marina.alves@escolateste.edu.br", "Marina Alves"),
    ("rafael.moura@escolateste.edu.br", "Rafael Moura"),
    ("camila.nunes@escolateste.edu.br", "Camila Nunes"),
    ("diego.ferreira@escolateste.edu.br", "Diego Ferreira"),
)

ALUNOS_6A = [
    ("Lucas Mendes", "ET-2026-101"),
    ("Beatriz Oliveira", "ET-2026-102"),
    ("Gabriel Souza", "ET-2026-103"),
    ("Larissa Costa", "ET-2026-104"),
    ("Matheus Lima", "ET-2026-105"),
    ("Isabela Rocha", "ET-2026-106"),
    ("Pedro Henrique Silva", "ET-2026-107"),
    ("Ana Clara Martins", "ET-2026-108"),
    ("João Pedro Almeida", "ET-2026-109"),
    ("Fernanda Ribeiro", "ET-2026-110"),
    ("Thiago Barbosa", "ET-2026-111"),
    ("Júlia Fernandes", "ET-2026-112"),
]
ALUNOS_6B = [
    ("Caio Moreira", "ET-2026-201"),
    ("Sofia Carvalho", "ET-2026-202"),
    ("Enzo Araujo", "ET-2026-203"),
    ("Valentina Dias", "ET-2026-204"),
    ("Davi Nascimento", "ET-2026-205"),
    ("Helena Castro", "ET-2026-206"),
    ("Bernardo Pinto", "ET-2026-207"),
    ("Manuela Teixeira", "ET-2026-208"),
    ("Arthur Correia", "ET-2026-209"),
    ("Laura Mendes", "ET-2026-210"),
    ("Heitor Campos", "ET-2026-211"),
    ("Alice Freitas", "ET-2026-212"),
]
ALUNOS_1A_EXTRA = [
    ("Mariana Duarte", "ET-2026-004"),
    ("Felipe Andrade", "ET-2026-005"),
    ("Camila Borges", "ET-2026-006"),
    ("Rafael Cunha", "ET-2026-007"),
    ("Letícia Prado", "ET-2026-008"),
    ("Vinícius Lopes", "ET-2026-009"),
    ("Amanda Vieira", "ET-2026-010"),
    ("Bruno Cardoso", "ET-2026-011"),
    ("Carolina Melo", "ET-2026-012"),
    ("Eduardo Pires", "ET-2026-013"),
]
ALUNOS_1B_EXTRA = [
    ("Nicole Azevedo", "ET-2026-014"),
    ("Gustavo Reis", "ET-2026-015"),
    ("Patrícia Gomes", "ET-2026-016"),
    ("Leonardo Batista", "ET-2026-017"),
    ("Isadora Monteiro", "ET-2026-018"),
    ("Rodrigo Farias", "ET-2026-019"),
    ("Tatiane Cruz", "ET-2026-020"),
    ("Paulo Henrique Ramos", "ET-2026-021"),
    ("Sabrina Nogueira", "ET-2026-022"),
    ("Daniela Moraes", "ET-2026-023"),
    ("Igor Santana", "ET-2026-024"),
]

AVISOS = (
    "Reunião pedagógica — sexta-feira, 12/09, às 14h no Campus Escola Teste. Presença da equipe docente.",
    "Semana de avaliações: 15 a 19/09. Entregar planejamentos até quarta-feira.",
    "Plantão de inclusão (AEE): terças, 10h–12h. Encaminhamentos pela Coordenação.",
)

METODOLOGIAS_CUSTOM = (
    (
        "Sala de aula invertida",
        "Versão Escola Teste: material enviado com 48h de antecedência, guia de foco "
        "(tempo por trecho) e abertura da aula com 3 perguntas dos alunos.",
    ),
    (
        "Minute Paper",
        "Versão Escola Teste: 3 minutos no fim da aula — o que ficou claro, o que travou, "
        "uma pergunta. Recolha no caderno coletivo da turma.",
    ),
    (
        "Design Thinking express",
        "Versão Escola Teste: empatia rápida (entrevista de 5 min entre pares), definição "
        "em post-it, protótipo em papel e teste com a dupla ao lado.",
    ),
)


def _one(cur, sql, params):
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def ensure_curso(cur, periodo_id: str, nome: str, nivel: str) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_cursos
        WHERE periodo_letivo_id = %s AND lower(nome) = lower(%s)
        LIMIT 1
        """,
        (periodo_id, nome),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"])
    cur.execute(
        """
        INSERT INTO public.school_cursos (periodo_letivo_id, nome, nivel, turma_turno)
        VALUES (%s, %s, %s, 'manha')
        RETURNING id
        """,
        (periodo_id, nome, nivel),
    )
    return str(cur.fetchone()["id"])


def rename_if(cur, table: str, old: str, new: str, extra_where: str, extra_params: tuple) -> None:
    cur.execute(
        f"SELECT id, nome FROM public.{table} WHERE {extra_where} AND lower(nome) = lower(%s) LIMIT 1",
        extra_params + (old,),
    )
    row = cur.fetchone()
    if not row:
        return
    cur.execute(
        f"SELECT id FROM public.{table} WHERE {extra_where} AND lower(nome) = lower(%s) AND id <> %s LIMIT 1",
        extra_params + (new, str(row["id"])),
    )
    if cur.fetchone():
        return
    cur.execute(
        f"UPDATE public.{table} SET nome = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (new, str(row["id"])),
    )


def ensure_aviso(cur, instituicao_id: str, gestor_id: str | None, texto: str) -> str:
    cur.execute(
        """
        SELECT id FROM public.school_avisos_mesa
        WHERE instituicao_id = %s AND texto = %s
        LIMIT 1
        """,
        (instituicao_id, texto),
    )
    row = cur.fetchone()
    if row:
        return str(row["id"])
    cur.execute(
        """
        INSERT INTO public.school_avisos_mesa (
            instituicao_id, texto, ativo, criado_por_gestor_id
        ) VALUES (%s, %s, TRUE, %s)
        RETURNING id
        """,
        (instituicao_id, texto, gestor_id),
    )
    return str(cur.fetchone()["id"])


def ensure_metodologia_custom(cur, instituicao_id: str, nome: str, passos: str) -> dict:
    cur.execute(
        """
        SELECT id, nome FROM public.school_metodologias_catalogo
        WHERE lower(nome) = lower(%s)
        LIMIT 1
        """,
        (nome,),
    )
    cat = cur.fetchone()
    if not cat:
        cur.execute(
            """
            SELECT id, nome FROM public.school_metodologias_catalogo
            WHERE lower(nome) LIKE lower(%s)
            LIMIT 1
            """,
            (f"%{nome}%",),
        )
        cat = cur.fetchone()
    if not cat:
        return {"nome": nome, "ok": False, "reason": "catalogo_nao_encontrado"}
    cur.execute(
        """
        INSERT INTO public.school_metodologias_org (
            instituicao_id, metodologia_id_canonica, passos_customizados, is_active
        ) VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (instituicao_id, metodologia_id_canonica) DO UPDATE SET
            passos_customizados = EXCLUDED.passos_customizados,
            is_active = TRUE,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (instituicao_id, str(cat["id"]), passos),
    )
    row = cur.fetchone()
    return {
        "nome": cat["nome"],
        "ok": True,
        "org_id": str(row["id"]),
        "catalogo_id": str(cat["id"]),
    }


def ensure_matriz_tdah(cur, instituicao_id: str) -> dict:
    canon = get_canonico("TDAH") or {}
    cur.execute(
        """
        SELECT * FROM public.school_aee_matrizes
        WHERE instituicao_id = %s AND condicao_categoria = 'TDAH'
        ORDER BY versao DESC
        LIMIT 1
        """,
        (instituicao_id,),
    )
    row = cur.fetchone()
    if row:
        mid = str(row["id"])
        cur.execute(
            """
            UPDATE public.school_aee_matrizes SET
                texto_escola = %s,
                campos_experiencia_metodologica = %s,
                assinado_coordenador = TRUE,
                assinado_psicopedagogo = TRUE,
                status = 'ativo',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *
            """,
            (
                canon.get("descricao_base_canonica") or "Diretriz TDAH — Escola Teste",
                canon.get("campos_experiencia_metodologica_canonica") or "",
                mid,
            ),
        )
        return dict(cur.fetchone())
    cur.execute(
        """
        INSERT INTO public.school_aee_matrizes (
            instituicao_id, versao, condicao_categoria, texto_escola,
            campos_experiencia_metodologica, status,
            assinado_coordenador, assinado_psicopedagogo
        ) VALUES (%s, 1, 'TDAH', %s, %s, 'ativo', TRUE, TRUE)
        RETURNING *
        """,
        (
            instituicao_id,
            canon.get("descricao_base_canonica") or "Diretriz TDAH — Escola Teste",
            canon.get("campos_experiencia_metodologica_canonica") or "",
        ),
    )
    return dict(cur.fetchone())


def ensure_pei(
    cur, instituicao_id: str, aluno: dict, matriz: dict, periodo_id: str
) -> dict:
    cur.execute(
        """
        SELECT * FROM public.school_pei_alunos
        WHERE instituicao_id = %s AND aluno_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (instituicao_id, aluno["id"]),
    )
    row = cur.fetchone()
    fields = dict(
        nome_completo=aluno["nome"],
        matricula=aluno["matricula"],
        nome_responsavel="Carla Mendes",
        perfil_atual_habilidades=(
            "Participa bem em atividades curtas e concretas. Lê com fluência, "
            "mas perde o fio em tarefas longas sem marco intermediário."
        ),
        barreiras_identificadas=(
            "Dificuldade de sustentar atenção em exposições acima de 10 minutos; "
            "impulsividade na fala em grupo; organização do material."
        ),
        metas_desenvolvimento=(
            "Concluir atividades em 2–3 blocos com check-in; usar timer visível; "
            "registrar uma síntese ao final de cada estação."
        ),
        recursos_assistivos="Timer visual, checklist ilustrado, lugar preferencial próximo ao professor.",
        criterios_avaliacao_flexibilizados=(
            "Valorizar processo e entregas parciais; tempo adicional de 25%; "
            "oral complementar à escrita quando necessário."
        ),
        experiencias_adaptadas_individuais=(
            "Rotação por Estações com papéis claros; Minute Paper no fechamento; "
            "microdesafios em vez de prova única longa."
        ),
    )
    if row:
        cur.execute(
            """
            UPDATE public.school_pei_alunos SET
                aee_matriz_id = %s,
                nome_completo = %s,
                matricula = %s,
                nome_responsavel = %s,
                perfil_atual_habilidades = %s,
                barreiras_identificadas = %s,
                metas_desenvolvimento = %s,
                recursos_assistivos = %s,
                criterios_avaliacao_flexibilizados = %s,
                experiencias_adaptadas_individuais = %s,
                periodo_letivo_id = %s,
                assinado_coordenador = TRUE,
                assinado_psicopedagogo = TRUE,
                data_assinatura = COALESCE(data_assinatura, CURRENT_TIMESTAMP),
                status = 'ativo',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *
            """,
            (
                str(matriz["id"]),
                fields["nome_completo"],
                fields["matricula"],
                fields["nome_responsavel"],
                fields["perfil_atual_habilidades"],
                fields["barreiras_identificadas"],
                fields["metas_desenvolvimento"],
                fields["recursos_assistivos"],
                fields["criterios_avaliacao_flexibilizados"],
                fields["experiencias_adaptadas_individuais"],
                periodo_id,
                str(row["id"]),
            ),
        )
        return dict(cur.fetchone())
    pei_linha_id = uuid.uuid4()
    cur.execute(
        """
        INSERT INTO public.school_pei_alunos (
            instituicao_id, aee_matriz_id, pei_linha_id, versao, status, aluno_id,
            nome_completo, matricula, nome_responsavel,
            perfil_atual_habilidades, barreiras_identificadas,
            metas_desenvolvimento, recursos_assistivos,
            criterios_avaliacao_flexibilizados,
            experiencias_adaptadas_individuais,
            periodo_letivo_id,
            assinado_coordenador, assinado_psicopedagogo, data_assinatura
        ) VALUES (
            %s, %s, %s, 1, 'ativo', %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            TRUE, TRUE, CURRENT_TIMESTAMP
        )
        RETURNING *
        """,
        (
            instituicao_id,
            str(matriz["id"]),
            str(pei_linha_id),
            aluno["id"],
            fields["nome_completo"],
            fields["matricula"],
            fields["nome_responsavel"],
            fields["perfil_atual_habilidades"],
            fields["barreiras_identificadas"],
            fields["metas_desenvolvimento"],
            fields["recursos_assistivos"],
            fields["criterios_avaliacao_flexibilizados"],
            fields["experiencias_adaptadas_individuais"],
            periodo_id,
        ),
    )
    return dict(cur.fetchone())


def main() -> int:
    print("=== prompt 70 — enriquecer Escola Teste ===", flush=True)
    report: dict = {"instituicao_id": INST}

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            inst = _one(
                cur,
                "SELECT id, razao_social, dominio_email FROM public.school_instituicoes WHERE id = %s",
                (INST,),
            )
            if not inst:
                raise RuntimeError("Instituição Escola Teste não encontrada — abortar.")
            homolog = _one(
                cur,
                """
                SELECT g.id, g.nome, g.email,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s AND lower(g.email) = %s
                GROUP BY g.id
                """,
                (INST, HOMOLOG_EMAIL),
            )
            if not homolog:
                raise RuntimeError("Homologador LeAction não encontrado — abortar.")
            zonas = set(homolog["zonas"] or [])
            need = {"administrativo", "operacional", "pedagogico"}
            if not need.issubset(zonas):
                raise RuntimeError(f"Zonas insuficientes no Homologador: {sorted(zonas)}")
            report["homologador"] = {
                "id": str(homolog["id"]),
                "email": homolog["email"],
                "nome": homolog["nome"],
                "zonas": sorted(zonas),
            }

            unidade = _one(
                cur,
                "SELECT id FROM public.school_unidades WHERE instituicao_id = %s LIMIT 1",
                (INST,),
            )
            periodo = _one(
                cur,
                """
                SELECT id FROM public.school_periodos_letivos
                WHERE instituicao_id = %s AND em_curso = TRUE
                ORDER BY ano_letivo DESC LIMIT 1
                """,
                (INST,),
            )
            unidade_id = str(unidade["id"])
            periodo_id = str(periodo["id"])
            report["unidade_id"] = unidade_id
            report["periodo_id"] = periodo_id

            rename_if(
                cur,
                "school_cursos",
                "Ensino Médio — Escola Teste",
                "Ensino Médio",
                "periodo_letivo_id = %s",
                (periodo_id,),
            )
            rename_if(
                cur,
                "school_turmas",
                "1ª Série A — Escola Teste",
                "1ª Série A",
                "instituicao_id = %s AND periodo_letivo_id = %s",
                (INST, periodo_id),
            )
            rename_if(
                cur,
                "school_turmas",
                "1ª Série B — Escola Teste",
                "1ª Série B",
                "instituicao_id = %s AND periodo_letivo_id = %s",
                (INST, periodo_id),
            )
            rename_if(
                cur,
                "school_disciplinas",
                "Matemática — Escola Teste",
                "Matemática",
                "instituicao_id = %s",
                (INST,),
            )
            rename_if(
                cur,
                "school_disciplinas",
                "Português — Escola Teste",
                "Língua Portuguesa",
                "instituicao_id = %s",
                (INST,),
            )

            curso_em = ensure_curso(cur, periodo_id, "Ensino Médio", "medio")
            curso_ef = ensure_curso(cur, periodo_id, "Ensino Fundamental II", "fundamental")
            report["cursos"] = {"ensino_medio": curso_em, "fundamental_ii": curso_ef}

            t1a = seed_et.ensure_turma(
                cur,
                instituicao_id=INST,
                unidade_id=unidade_id,
                periodo_id=periodo_id,
                curso_id=curso_em,
                nome="1ª Série A",
                serie="1ª série",
                turno="manha",
            )
            t1b = seed_et.ensure_turma(
                cur,
                instituicao_id=INST,
                unidade_id=unidade_id,
                periodo_id=periodo_id,
                curso_id=curso_em,
                nome="1ª Série B",
                serie="1ª série",
                turno="tarde",
            )
            t6a = seed_et.ensure_turma(
                cur,
                instituicao_id=INST,
                unidade_id=unidade_id,
                periodo_id=periodo_id,
                curso_id=curso_ef,
                nome="6º Ano A",
                serie="6º ano",
                turno="manha",
            )
            t6b = seed_et.ensure_turma(
                cur,
                instituicao_id=INST,
                unidade_id=unidade_id,
                periodo_id=periodo_id,
                curso_id=curso_ef,
                nome="6º Ano B",
                serie="6º ano",
                turno="tarde",
            )
            report["turmas"] = {"1a": t1a, "1b": t1b, "6a": t6a, "6b": t6b}

            disc_em = ["Matemática", "Língua Portuguesa", "História", "Geografia", "Inglês", "Arte", "Educação Física", "Biologia"]
            disc_ef = ["Matemática", "Língua Portuguesa", "Ciências", "História", "Geografia", "Inglês", "Arte", "Educação Física"]
            discs: dict[str, str] = {}
            for nome in sorted(set(disc_em + disc_ef)):
                discs[nome] = seed_et.ensure_disciplina(cur, INST, curso_em if nome in disc_em else curso_ef, nome)
            for nome in disc_em:
                seed_et.ensure_disciplina(cur, INST, curso_em, nome)
            for nome in disc_ef:
                seed_et.ensure_disciplina(cur, INST, curso_ef, nome)
            report["disciplinas"] = discs

            alunos_out = []
            for nome, mat in ALUNOS_1A_EXTRA:
                alunos_out.append(seed_et.ensure_aluno(cur, instituicao_id=INST, turma_id=t1a, nome=nome, matricula=mat))
            for nome, mat in ALUNOS_1B_EXTRA:
                alunos_out.append(seed_et.ensure_aluno(cur, instituicao_id=INST, turma_id=t1b, nome=nome, matricula=mat))
            for nome, mat in ALUNOS_6A:
                alunos_out.append(seed_et.ensure_aluno(cur, instituicao_id=INST, turma_id=t6a, nome=nome, matricula=mat))
            for nome, mat in ALUNOS_6B:
                alunos_out.append(seed_et.ensure_aluno(cur, instituicao_id=INST, turma_id=t6b, nome=nome, matricula=mat))

            lucas = _one(
                cur,
                "SELECT id, nome, matricula FROM public.school_alunos WHERE instituicao_id = %s AND matricula = %s",
                (INST, "ET-2026-101"),
            )
            report["aluno_pei"] = dict(lucas) if lucas else None

            invites = []
            for email, _nome in NOVOS_PROFESSORES:
                invites.append(seed_et.invite_professor(cur, INST, email))
            for email in ("professor1@escolateste.edu.br", "professor2@escolateste.edu.br"):
                invites.append(seed_et.invite_professor(cur, INST, email))

            def vinculo_id(email: str) -> str | None:
                cur.execute(
                    """
                    SELECT id FROM public.school_professores_vinculo
                    WHERE instituicao_id = %s AND lower(email_convite) = %s
                    LIMIT 1
                    """,
                    (INST, email.lower()),
                )
                r = cur.fetchone()
                return str(r["id"]) if r else None

            aloc_specs = [
                ("professor1@escolateste.edu.br", "Matemática", t1a),
                ("professor2@escolateste.edu.br", "Língua Portuguesa", t1b),
                ("marina.alves@escolateste.edu.br", "Matemática", t6a),
                ("marina.alves@escolateste.edu.br", "Ciências", t6a),
                ("rafael.moura@escolateste.edu.br", "História", t6a),
                ("rafael.moura@escolateste.edu.br", "Geografia", t6b),
                ("camila.nunes@escolateste.edu.br", "Língua Portuguesa", t6a),
                ("camila.nunes@escolateste.edu.br", "Inglês", t1a),
                ("diego.ferreira@escolateste.edu.br", "Educação Física", t6b),
                ("diego.ferreira@escolateste.edu.br", "Arte", t1b),
                (HOMOLOG_EMAIL, "Matemática", t6a),
            ]
            aloc_ids = []
            for email, disc_nome, turma_id in aloc_specs:
                vid = vinculo_id(email)
                did = discs.get(disc_nome)
                if not vid or not did:
                    continue
                aloc_ids.append(
                    (
                        email,
                        disc_nome,
                        seed_et.ensure_alocacao(
                            cur,
                            instituicao_id=INST,
                            unidade_id=unidade_id,
                            periodo_id=periodo_id,
                            disciplina_id=did,
                            professor_vinculo_id=vid,
                            turma_id=turma_id,
                        ),
                    )
                )

            matriz = ensure_matriz_tdah(cur, INST)
            pei = ensure_pei(cur, INST, lucas, matriz, periodo_id) if lucas else None
            aviso_ids = [
                ensure_aviso(cur, INST, str(homolog["id"]), texto) for texto in AVISOS
            ]
            mets = [ensure_metodologia_custom(cur, INST, n, p) for n, p in METODOLOGIAS_CUSTOM]

            report["convites"] = [
                {"email": i["email"], "vinculo_id": i["id"], "status": i["status_vinculo"], "created": i["created"]}
                for i in invites
            ]
            report["alocacoes"] = [{"email": e, "disciplina": d, "id": a} for e, d, a in aloc_ids]
            report["matriz_tdah"] = {"id": str(matriz["id"]), "status": str(matriz.get("status"))}
            report["pei"] = (
                {
                    "id": str(pei["id"]),
                    "aluno_id": str(pei.get("aluno_id")),
                    "nome": pei.get("nome_completo"),
                    "assinado": bool(pei.get("assinado_coordenador"))
                    and bool(pei.get("assinado_psicopedagogo")),
                }
                if pei
                else None
            )
            report["avisos"] = aviso_ids
            report["metodologias"] = mets

    pushes = {"teacher_invite": [], "teacher_allocated": [], "avisos": []}
    for inv in report["convites"]:
        if inv["status"] == "ativo":
            pushes["teacher_invite"].append({"email": inv["email"], "skipped": True})
            continue
        pushes["teacher_invite"].append(
            {
                "email": inv["email"],
                "b2c": seed_et.push_teacher_invite(INST, {"id": inv["vinculo_id"], "email": inv["email"], "professor_b2c_id": None}, "Escola Teste"),
            }
        )
    for item in report["alocacoes"]:
        pushes["teacher_allocated"].append(seed_et.push_teacher_allocated(item["id"]))
    for aid in report["avisos"]:
        pushes["avisos"].append(
            dispatch_event_to_b2c(
                "AVISO_MESA_PINNED",
                {
                    "instituicao_id": INST,
                    "aviso_id": aid,
                    "texto": next(t for t in AVISOS),
                    "ativo": True,
                },
            )
        )
        # mark replicated
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.school_avisos_mesa
                    SET replicado_b2c = TRUE, replicado_b2c_em = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (aid,),
                )

    if report.get("matriz_tdah"):
        pushes["pei_aee"] = dispatch_pei_override_updated(
            {
                "nivel": "aee_base",
                "instituicao_id": INST,
                "condicao": "TDAH",
                "diretriz": (get_canonico("TDAH") or {}).get("descricao_base_canonica") or "",
                "versao": 1,
                "aee_matriz_id": report["matriz_tdah"]["id"],
            }
        )
    if report.get("pei"):
        pushes["pei_individual"] = dispatch_pei_override_updated(
            {
                "nivel": "individual",
                "instituicao_id": INST,
                "aluno_id": report["pei"]["aluno_id"],
                "aluno_nome": report["pei"]["nome"],
                "condicao": "TDAH",
                "particularidades": "Check-ins curtos, timer visível, entregas parciais.",
                "aee_matriz_id_base": report["matriz_tdah"]["id"],
                "versao": 1,
                "pei_aluno_id": report["pei"]["id"],
            }
        )

    # Fix aviso texts (each aviso its own text) — the loop above reused AVISOS[0].
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, texto FROM public.school_avisos_mesa WHERE instituicao_id = %s ORDER BY created_at",
                (INST,),
            )
            aviso_rows = [dict(r) for r in cur.fetchall()]
    pushes["avisos"] = []
    for row in aviso_rows:
        pushes["avisos"].append(
            dispatch_event_to_b2c(
                "AVISO_MESA_PINNED",
                {
                    "instituicao_id": INST,
                    "aviso_id": str(row["id"]),
                    "texto": row["texto"],
                    "ativo": True,
                },
            )
        )

    report["pushes"] = {
        "teacher_invite_ok": sum(1 for x in pushes["teacher_invite"] if (x.get("b2c") or {}).get("ok") or x.get("skipped")),
        "teacher_allocated": [
            {"email": x.get("professor_email"), "ok": x.get("ok")} for x in pushes["teacher_allocated"]
        ],
        "avisos_ok": [bool(x.get("ok")) for x in pushes["avisos"]],
        "pei_aee_ok": bool((pushes.get("pei_aee") or {}).get("ok")),
        "pei_individual_ok": bool((pushes.get("pei_individual") or {}).get("ok")),
    }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT t.nome, COUNT(a.id) AS n
                FROM public.school_turmas t
                LEFT JOIN public.school_alunos a ON a.turma_id = t.id
                WHERE t.instituicao_id = %s
                GROUP BY t.nome ORDER BY t.nome
                """,
                (INST,),
            )
            report["alunos_por_turma"] = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT email_convite, status_vinculo, professor_b2c_id
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s ORDER BY email_convite
                """,
                (INST,),
            )
            report["professores_finais"] = [dict(r) for r in cur.fetchall()]

    print("--- REPORT ---", flush=True)
    print(json.dumps(report, default=str, ensure_ascii=False, indent=2), flush=True)
    print("=== prompt 70 school OK ===", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SEED70_FAILED: {exc}", file=sys.stderr, flush=True)
        raise
