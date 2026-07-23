"""Completa correção de leaf_bloc: framework + mapa explícito dos nomes fora do framework."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "LeAction_SysF" / "ai_engine" / "framework_definitions.py"
OUT = ROOT / "fix_encoding_blocs.sql"

# Nomes presentes no banco mas com rótulo diferente/ausente no framework
EXTRA_CANON = [
    "Alicerce de Execução",
    "Alocação Profissional Externa",
    "Alocação Profissional Interna",
    "Analítica de Cenários",
    "Análise de Necessidades de Aprendizagem",
    "Apoio e Aplicação em Vagas de Trabalho",
    "Associações Profissionais e Industriais",
    "Competências de Tecnologia",
    "Conteúdo Imersivo e Simulado",
    "Criação de Conteúdo Digital",
    "Elaboração de Projetos de Aprendizagem",
    "Empregabilidade e Construção de Competências",
    "Estratégias de Promoção de Eventos Educacionais",
    "Experiências de Aprendizagem Digital",
    "Feedback de Avaliação",
    "Gerenciamento da Integração de Conteúdo",
    "Gerenciamento de Identidade e Autenticação",
    "Interoperabilidade e Padrões Abertos",
    "Licenciamento de OER* e Conteúdos",
    "Liderança Estratégica Digital",
    "Onboarding e Orientação",
    "Pacote de Inovação Corporativa",
    "Padrões de Acessibilidade",
    "Padrões de Ciência de Dados e Big Data",
    "Padrões de Dados e Tecnologia",
    "Padrões de Desenvolvimento Ágil",
    "Parcerias e Colaboração na Indústria",
    "Plano de Dívida Técnica",
    "Programas Híbridos e On-Line",
    "Projetos e Simulação no Espaço de Trabalho",
    "Redes de Mentoria na Indústria",
    "Relatórios de Analítica",
    "Seleção de Programas e Eventos Educacionais",
    "Serviço de Planejamento de Carreira",
    "Validação de Problemas",
]


def extract_bloc_names(src: str) -> list[str]:
    return sorted(set(re.findall(r'"([^"]+)":\s*"####', src)))


def corrupt_like_dump(text: str) -> str:
    return "".join("??" if ord(ch) > 127 else ch for ch in text)


def main() -> int:
    src = FRAMEWORK.read_text(encoding="utf-8")
    canon = extract_bloc_names(src) + EXTRA_CANON
    by_corrupt = {corrupt_like_dump(c): c for c in canon}

    corrupted_list = [ln.strip() for ln in sys.stdin if ln.strip()]
    lines = [
        "-- Auto-gerado: leaf_bloc.name_bloc",
        "BEGIN;",
        "",
    ]
    matched = 0
    missing: list[str] = []
    for corrupted in corrupted_list:
        good = by_corrupt.get(corrupted)
        if not good:
            missing.append(corrupted)
            continue
        g = good.replace("'", "''")
        b = corrupted.replace("'", "''")
        lines.append(
            f"UPDATE public.leaf_bloc SET name_bloc = '{g}' WHERE name_bloc = '{b}';"
        )
        matched += 1

    lines += ["", "COMMIT;", ""]
    OUT.write_bytes("\n".join(lines).encode("utf-8"))
    print(f"matched={matched} missing={len(missing)}")
    for m in missing:
        print("MISS", m)
    return 0 if not missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
