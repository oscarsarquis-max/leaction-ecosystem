#!/usr/bin/env python3
"""Gera migrations/014_matriz_okr_direcionadores.sql com textos canônicos."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "migrations" / "014_matriz_okr_direcionadores.sql"

MATRIX = [
    {
        "nome": "Digitalização Organizacional",
        "descricao": "Eficiência operacional, integração de sistemas e cultura data-driven.",
        "objetivos": [
            {
                "titulo": "Otimizar a eficiência e fluidez dos processos internos.",
                "krs": [
                    ("Reduzir o tempo médio de processamento de fluxos administrativos (core) em X%.", "X%"),
                    ("Aumentar a taxa de resolução no primeiro nível (FCR) do suporte interno para >Y%.", ">Y%"),
                    ("Eliminar Z% das aprovações manuais ou baseadas em papel nos processos de secretaria/backoffice.", "Z%"),
                ],
            },
            {
                "titulo": "Consolidar uma arquitetura de sistemas integrada e resiliente.",
                "krs": [
                    ("Alcançar 100% de integração de dados entre o ERP e as plataformas fim (LMS/CRM).", "100%"),
                    ("Reduzir o tempo de indisponibilidade (downtime) de sistemas críticos para <X horas/ano.", "<X horas/ano"),
                    ("Migrar Y% dos sistemas legados on-premise para soluções em nuvem (SaaS/IaaS).", "Y%"),
                ],
            },
            {
                "titulo": "Fomentar a cultura de tomada de decisão baseada em dados.",
                "krs": [
                    ("Garantir que 100% dos gestores tenham acesso e utilizem dashboards de BI semanalmente.", "100%"),
                    ("Reduzir o tempo de geração de relatórios gerenciais de dias para <X horas.", "<X horas"),
                    ("Treinar Y% das lideranças em fundamentos de análise de dados (Data Literacy).", "Y%"),
                ],
            },
        ],
    },
    {
        "nome": "Engajamento da Comunidade",
        "descricao": "Comunicação digital, satisfação da comunidade e participação ativa.",
        "objetivos": [
            {
                "titulo": "Fortalecer a comunicação institucional nos canais digitais.",
                "krs": [
                    ("Aumentar a taxa de leitura/abertura dos comunicados oficiais em X%.", "X%"),
                    ("Reduzir o tempo médio de resposta às solicitações da comunidade para <Y horas.", "<Y horas"),
                    ("Aumentar o volume de interações nos portais de autoatendimento em Z%.", "Z%"),
                ],
            },
            {
                "titulo": "Elevar os níveis de satisfação e retenção da comunidade.",
                "krs": [
                    ("Alcançar um NPS (Net Promoter Score) da comunidade superior a X.", "NPS > X"),
                    ("Reduzir a taxa de evasão (churn) de usuários/alunos em Y%.", "Y%"),
                    ("Aumentar a taxa de satisfação com o atendimento digital (CSAT) para >Z%.", ">Z%"),
                ],
            },
            {
                "titulo": "Promover a participação ativa em iniciativas da instituição.",
                "krs": [
                    ("Aumentar a presença em eventos híbridos ou virtuais em X%.", "X%"),
                    ("Obter Y propostas válidas de melhoria originadas pela própria comunidade por semestre.", "Y propostas/semestre"),
                    ("Implementar réguas de engajamento personalizadas para 100% dos perfis de usuários mapeados.", "100%"),
                ],
            },
        ],
    },
    {
        "nome": "Capacitação Docente",
        "descricao": "Fluência digital docente, metodologias ativas e aprendizado contínuo.",
        "objetivos": [
            {
                "titulo": "Elevar a fluência digital e autonomia do corpo docente.",
                "krs": [
                    ("Certificar X% dos professores no uso avançado das plataformas educacionais (LMS).", "X%"),
                    ("Reduzir o volume de chamados de suporte técnico de nível 1 abertos por docentes em Y%.", "Y%"),
                    ("Garantir que Z% do corpo docente utilize ferramentas interativas (quizzes, fóruns) semanalmente.", "Z%"),
                ],
            },
            {
                "titulo": "Modernizar a entrega de ensino com metodologias suportadas por TI.",
                "krs": [
                    ("Aumentar o número de disciplinas que adotam metodologias ativas (ex: sala de aula invertida) em X%.", "X%"),
                    ("Garantir que 100% dos novos cursos possuam design instrucional digital-first.", "100%"),
                    ("Elevar a avaliação média dos alunos sobre a didática digital dos professores para >Y.", ">Y"),
                ],
            },
            {
                "titulo": "Criar um ecossistema de aprendizado contínuo para os educadores.",
                "krs": [
                    ("Cumprir X horas médias de treinamento em tecnologias educacionais por docente ao ano.", "X horas/ano"),
                    ("Publicar Y novos materiais de boas práticas no repositório institucional por trimestre.", "Y materiais/trimestre"),
                    ("Alcançar Z% de participação ativa dos docentes nas comunidades de prática internas.", "Z%"),
                ],
            },
        ],
    },
    {
        "nome": "Prontidão Tecnológica",
        "descricao": "Infraestrutura resiliente, cibersegurança e gestão de ativos de TI.",
        "objetivos": [
            {
                "titulo": "Assegurar estabilidade e escalabilidade da infraestrutura.",
                "krs": [
                    ("Garantir um uptime de 99,9% para as plataformas core.", "99,9%"),
                    ("Reduzir o Mean Time to Repair (MTTR) de incidentes críticos em X%.", "X%"),
                    ("Executar 100% das rotinas de testes de Disaster Recovery (DR) previstas no ano.", "100%"),
                ],
            },
            {
                "titulo": "Elevar o nível de maturidade em Cibersegurança e Compliance.",
                "krs": [
                    ("Zerar incidentes graves de vazamento de dados (Zero Data Breach).", "Zero Data Breach"),
                    ("Alcançar 100% de conformidade com as diretrizes da LGPD nos processos digitais.", "100%"),
                    ("Treinar X% dos colaboradores em conscientização de segurança da informação.", "X%"),
                ],
            },
            {
                "titulo": "Otimizar a gestão do ciclo de vida dos ativos de TI.",
                "krs": [
                    ("Reduzir a idade média do parque de equipamentos (hardware) para <X anos.", "<X anos"),
                    ("Automatizar Y% dos fluxos de provisionamento de acessos e softwares.", "Y%"),
                    ("Reduzir custos com licenciamento ocioso de software em Z%.", "Z%"),
                ],
            },
        ],
    },
    {
        "nome": "Novos Modelos de Negócio",
        "descricao": "Receita digital, expansão de mercado e inovação disruptiva ágil.",
        "objetivos": [
            {
                "titulo": "Diversificar as fontes de receita através de ecossistemas digitais.",
                "krs": [
                    ("Lançar X novos produtos, cursos ou serviços 100% digitais no ano.", "X lançamentos/ano"),
                    ("Aumentar o faturamento bruto proveniente de canais puramente online em Y%.", "Y%"),
                    ("Fechar Z novas parcerias B2B integradas digitalmente à instituição.", "Z parcerias"),
                ],
            },
            {
                "titulo": "Expandir o alcance de mercado superando barreiras geográficas.",
                "krs": [
                    ("Aumentar o volume de matrículas/vendas fora da região principal de atuação em X%.", "X%"),
                    ("Reduzir o Custo de Aquisição de Clientes (CAC) em campanhas de captação digital em Y%.", "Y%"),
                    ("Adaptar/localizar Z% do conteúdo principal para explorar um novo nicho demográfico.", "Z%"),
                ],
            },
            {
                "titulo": "Validar inovações disruptivas de forma ágil.",
                "krs": [
                    ("Conduzir X Provas de Conceito (PoCs) de novas tecnologias (IA, VR, etc.) com impacto no negócio.", "X PoCs"),
                    ("Lançar pelo menos 1 iniciativa comercial impulsionada por IA no semestre.", "1+/semestre"),
                    ("Alcançar Y% de adoção inicial nos primeiros 3 meses após o lançamento de novos modelos.", "Y%"),
                ],
            },
        ],
    },
]


def esc(s: str) -> str:
    return s.replace("'", "''")


def main() -> None:
    lines = [
        "-- Matriz canônica OKR PanelDX — baseline global (Direcionadores > Objetivos > KRs)",
        "-- Executar após migrations anteriores.",
        "",
        "BEGIN;",
        "",
        "CREATE TABLE IF NOT EXISTS public.dx_direcionadores (",
        "    id          SERIAL PRIMARY KEY,",
        "    nome        VARCHAR(200) NOT NULL,",
        "    descricao   TEXT",
        ");",
        "",
        "CREATE TABLE IF NOT EXISTS public.dx_objetivos (",
        "    id                  SERIAL PRIMARY KEY,",
        "    direcionador_id     INTEGER NOT NULL REFERENCES public.dx_direcionadores(id) ON DELETE CASCADE,",
        "    titulo              TEXT NOT NULL",
        ");",
        "",
        "CREATE TABLE IF NOT EXISTS public.dx_krs (",
        "    id                          SERIAL PRIMARY KEY,",
        "    objetivo_id                 INTEGER NOT NULL REFERENCES public.dx_objetivos(id) ON DELETE CASCADE,",
        "    descricao                   TEXT NOT NULL,",
        "    metrica_alvo_placeholder    VARCHAR(120)",
        ");",
        "",
        "CREATE INDEX IF NOT EXISTS idx_dx_objetivos_direcionador ON public.dx_objetivos (direcionador_id);",
        "CREATE INDEX IF NOT EXISTS idx_dx_krs_objetivo ON public.dx_krs (objetivo_id);",
        "",
        "COMMENT ON TABLE public.dx_direcionadores IS 'Catálogo global — 5 direcionadores estratégicos PanelDX';",
        "COMMENT ON TABLE public.dx_objetivos IS 'Objetivos canônicos vinculados a cada direcionador';",
        "COMMENT ON TABLE public.dx_krs IS 'Key Results canônicos (baseline para clientes)';",
        "",
        "-- Sprint passa a referenciar objetivo canônico (substitui texto solto de direcionador)",
        "ALTER TABLE public.ctdi_sprn",
        "    ADD COLUMN IF NOT EXISTS objetivo_id INTEGER REFERENCES public.dx_objetivos(id) ON DELETE SET NULL;",
        "",
        "CREATE INDEX IF NOT EXISTS idx_ctdi_sprn_objetivo_id ON public.ctdi_sprn (objetivo_id);",
        "",
        "-- Pontes opcionais para instância OKR por cliente",
        "ALTER TABLE public.ctdi_okr_direcionadores",
        "    ADD COLUMN IF NOT EXISTS dx_direcionador_id INTEGER REFERENCES public.dx_direcionadores(id) ON DELETE SET NULL;",
        "ALTER TABLE public.ctdi_okr_objetivos_dt",
        "    ADD COLUMN IF NOT EXISTS dx_objetivo_id INTEGER REFERENCES public.dx_objetivos(id) ON DELETE SET NULL;",
        "ALTER TABLE public.ctdi_okr_krs",
        "    ADD COLUMN IF NOT EXISTS dx_kr_id INTEGER REFERENCES public.dx_krs(id) ON DELETE SET NULL;",
        "",
        "-- Limpa seeds anteriores (ids fixos reproduzíveis)",
        "DELETE FROM public.dx_krs;",
        "DELETE FROM public.dx_objetivos;",
        "DELETE FROM public.dx_direcionadores;",
        "",
    ]

    d_id = 0
    o_id = 0
    k_id = 0
    for d in MATRIX:
        d_id += 1
        lines.append(
            f"INSERT INTO public.dx_direcionadores (id, nome, descricao) VALUES "
            f"({d_id}, '{esc(d['nome'])}', '{esc(d['descricao'])}');"
        )
        for obj in d["objetivos"]:
            o_id += 1
            lines.append(
                f"INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES "
                f"({o_id}, {d_id}, '{esc(obj['titulo'])}');"
            )
            for desc, placeholder in obj["krs"]:
                k_id += 1
                lines.append(
                    f"INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES "
                    f"({k_id}, {o_id}, '{esc(desc)}', '{esc(placeholder)}');"
                )

    lines.extend([
        "",
        f"SELECT setval(pg_get_serial_sequence('public.dx_direcionadores', 'id'), {d_id}, true);",
        f"SELECT setval(pg_get_serial_sequence('public.dx_objetivos', 'id'), {o_id}, true);",
        f"SELECT setval(pg_get_serial_sequence('public.dx_krs', 'id'), {k_id}, true);",
        "",
        "COMMIT;",
        "",
    ])

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({d_id} direcionadores, {o_id} objetivos, {k_id} KRs)")


if __name__ == "__main__":
    main()
