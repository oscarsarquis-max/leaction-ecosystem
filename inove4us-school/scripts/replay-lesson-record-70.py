#!/usr/bin/env python3
"""Replay LESSON_RECORD_SYNC no School (handler real).

O professor fechou a aula no Inove (POST /api/agenda-eventos/9/concluir-aula)
com sugestão à coordenação. O B2C tentou POST em http://127.0.0.1:5012 e
falhou. Aqui rodamos o mesmo handler do webhook School.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from webhook_b2c_routes import _handle_lesson_record_sync  # noqa: E402

SUGESTAO = (
    "Na Sala de aula invertida com o 6º Ano A, o vídeo curto em casa funcionou "
    "melhor que o texto. Sugiro limitar o pré-aula a 4 minutos e trazer a "
    "equivalência de frações só na estação presencial, com cartões visuais."
)
PEI = (
    "Timer visível e check-in a cada 8 minutos manteve o Lucas no ciclo. "
    "Vale padronizar isso na diretriz TDAH para Matemática."
)

PAYLOAD = {
    "instituicao_id": "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50",
    "origem_plano_b2c_id": "9",
    "professor_email": "homologador@leaction.com.br",
    "email": "homologador@leaction.com.br",
    "professor_b2c_id": "21",
    "professor_id": "21",
    "professor_nome": "Homologador",
    "professor_vinculo_id": "53ba52b8-35c7-4c24-8f77-93877e58716f",
    "turma_id": "f989b568-5566-4328-8c45-5a6d1f6f6d17",
    "aula_contexto": "Sala de aula invertida · Matemática · Frações no cotidiano",
    "texto_sugestao": SUGESTAO,
    "metodologia_nome": "Sala de aula invertida",
    "metodologia_usada": "Sala de aula invertida",
    "semana_referencia": "2026-09-04",
    "tipo_aula": "dia_a_dia",
    "status": "aprovado",
    "conteudo_resumo": "Dia a Dia · Frações no cotidiano · 6º Ano A",
    "has_teacher_adaptations": True,
    "teacher_adaptation_text": SUGESTAO,
    "adaptations": {"texto": SUGESTAO},
    "has_pei_adaptations": True,
    "pei_adaptation_text": PEI,
    "aluno_nome": "Lucas Mendes",
    "pei_aluno_id": "88da0eae-5446-4ec7-9c96-f88f63d37c33",
    "mesa": {
        "id": "9",
        "titulo": "Dia a Dia · Frações no cotidiano · 6º Ano A",
        "tipo_aula": "dia_a_dia",
        "status": "concluido",
        "metodologia_nome": "Sala de aula invertida",
        "semana_referencia": "2026-09-04",
        "has_teacher_adaptations": True,
        "teacher_adaptation_text": SUGESTAO,
        "texto_sugestao": SUGESTAO,
        "aula_contexto": "Sala de aula invertida · Matemática · Frações no cotidiano",
        "adaptations": {"texto": SUGESTAO},
        "has_pei_adaptations": True,
        "pei_adaptation_text": PEI,
        "aluno_nome": "Lucas Mendes",
        "pei_aluno_id": "88da0eae-5446-4ec7-9c96-f88f63d37c33",
        "professor_id": "21",
        "professor_nome": "Homologador",
        "relato_sala": (
            "Ciclo de frações no 6º A. Estações com cartões; Lucas acompanhou "
            "com timer visível. Diário: equivalência 1/2 = 2/4 ficou clara na pizza."
        ),
        "participantes": "6º Ano A — 12 alunos (Homologador)",
    },
}


def main() -> None:
    print(_handle_lesson_record_sync(PAYLOAD))


if __name__ == "__main__":
    main()
