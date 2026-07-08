-- Matriz canônica OKR PanelDX — baseline global (Direcionadores > Objetivos > KRs)
-- Executar após migrations anteriores.

BEGIN;

CREATE TABLE IF NOT EXISTS public.dx_direcionadores (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    descricao   TEXT
);

CREATE TABLE IF NOT EXISTS public.dx_objetivos (
    id                  SERIAL PRIMARY KEY,
    direcionador_id     INTEGER NOT NULL REFERENCES public.dx_direcionadores(id) ON DELETE CASCADE,
    titulo              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.dx_krs (
    id                          SERIAL PRIMARY KEY,
    objetivo_id                 INTEGER NOT NULL REFERENCES public.dx_objetivos(id) ON DELETE CASCADE,
    descricao                   TEXT NOT NULL,
    metrica_alvo_placeholder    VARCHAR(120)
);

CREATE INDEX IF NOT EXISTS idx_dx_objetivos_direcionador ON public.dx_objetivos (direcionador_id);
CREATE INDEX IF NOT EXISTS idx_dx_krs_objetivo ON public.dx_krs (objetivo_id);

COMMENT ON TABLE public.dx_direcionadores IS 'Catálogo global — 5 direcionadores estratégicos PanelDX';
COMMENT ON TABLE public.dx_objetivos IS 'Objetivos canônicos vinculados a cada direcionador';
COMMENT ON TABLE public.dx_krs IS 'Key Results canônicos (baseline para clientes)';

-- Sprint passa a referenciar objetivo canônico (substitui texto solto de direcionador)
ALTER TABLE public.ctdi_sprn
    ADD COLUMN IF NOT EXISTS objetivo_id INTEGER REFERENCES public.dx_objetivos(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ctdi_sprn_objetivo_id ON public.ctdi_sprn (objetivo_id);

-- Pontes opcionais para instância OKR por cliente
ALTER TABLE public.ctdi_okr_direcionadores
    ADD COLUMN IF NOT EXISTS dx_direcionador_id INTEGER REFERENCES public.dx_direcionadores(id) ON DELETE SET NULL;
ALTER TABLE public.ctdi_okr_objetivos_dt
    ADD COLUMN IF NOT EXISTS dx_objetivo_id INTEGER REFERENCES public.dx_objetivos(id) ON DELETE SET NULL;
ALTER TABLE public.ctdi_okr_krs
    ADD COLUMN IF NOT EXISTS dx_kr_id INTEGER REFERENCES public.dx_krs(id) ON DELETE SET NULL;

-- Limpa seeds anteriores (ids fixos reproduzíveis)
DELETE FROM public.dx_krs;
DELETE FROM public.dx_objetivos;
DELETE FROM public.dx_direcionadores;

INSERT INTO public.dx_direcionadores (id, nome, descricao) VALUES (1, 'Digitalização Organizacional', 'Eficiência operacional, integração de sistemas e cultura data-driven.');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (1, 1, 'Otimizar a eficiência e fluidez dos processos internos.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (1, 1, 'Reduzir o tempo médio de processamento de fluxos administrativos (core) em X%.', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (2, 1, 'Aumentar a taxa de resolução no primeiro nível (FCR) do suporte interno para >Y%.', '>Y%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (3, 1, 'Eliminar Z% das aprovações manuais ou baseadas em papel nos processos de secretaria/backoffice.', 'Z%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (2, 1, 'Consolidar uma arquitetura de sistemas integrada e resiliente.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (4, 2, 'Alcançar 100% de integração de dados entre o ERP e as plataformas fim (LMS/CRM).', '100%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (5, 2, 'Reduzir o tempo de indisponibilidade (downtime) de sistemas críticos para <X horas/ano.', '<X horas/ano');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (6, 2, 'Migrar Y% dos sistemas legados on-premise para soluções em nuvem (SaaS/IaaS).', 'Y%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (3, 1, 'Fomentar a cultura de tomada de decisão baseada em dados.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (7, 3, 'Garantir que 100% dos gestores tenham acesso e utilizem dashboards de BI semanalmente.', '100%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (8, 3, 'Reduzir o tempo de geração de relatórios gerenciais de dias para <X horas.', '<X horas');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (9, 3, 'Treinar Y% das lideranças em fundamentos de análise de dados (Data Literacy).', 'Y%');
INSERT INTO public.dx_direcionadores (id, nome, descricao) VALUES (2, 'Engajamento da Comunidade', 'Comunicação digital, satisfação da comunidade e participação ativa.');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (4, 2, 'Fortalecer a comunicação institucional nos canais digitais.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (10, 4, 'Aumentar a taxa de leitura/abertura dos comunicados oficiais em X%.', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (11, 4, 'Reduzir o tempo médio de resposta às solicitações da comunidade para <Y horas.', '<Y horas');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (12, 4, 'Aumentar o volume de interações nos portais de autoatendimento em Z%.', 'Z%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (5, 2, 'Elevar os níveis de satisfação e retenção da comunidade.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (13, 5, 'Alcançar um NPS (Net Promoter Score) da comunidade superior a X.', 'NPS > X');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (14, 5, 'Reduzir a taxa de evasão (churn) de usuários/alunos em Y%.', 'Y%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (15, 5, 'Aumentar a taxa de satisfação com o atendimento digital (CSAT) para >Z%.', '>Z%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (6, 2, 'Promover a participação ativa em iniciativas da instituição.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (16, 6, 'Aumentar a presença em eventos híbridos ou virtuais em X%.', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (17, 6, 'Obter Y propostas válidas de melhoria originadas pela própria comunidade por semestre.', 'Y propostas/semestre');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (18, 6, 'Implementar réguas de engajamento personalizadas para 100% dos perfis de usuários mapeados.', '100%');
INSERT INTO public.dx_direcionadores (id, nome, descricao) VALUES (3, 'Capacitação Docente', 'Fluência digital docente, metodologias ativas e aprendizado contínuo.');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (7, 3, 'Elevar a fluência digital e autonomia do corpo docente.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (19, 7, 'Certificar X% dos professores no uso avançado das plataformas educacionais (LMS).', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (20, 7, 'Reduzir o volume de chamados de suporte técnico de nível 1 abertos por docentes em Y%.', 'Y%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (21, 7, 'Garantir que Z% do corpo docente utilize ferramentas interativas (quizzes, fóruns) semanalmente.', 'Z%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (8, 3, 'Modernizar a entrega de ensino com metodologias suportadas por TI.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (22, 8, 'Aumentar o número de disciplinas que adotam metodologias ativas (ex: sala de aula invertida) em X%.', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (23, 8, 'Garantir que 100% dos novos cursos possuam design instrucional digital-first.', '100%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (24, 8, 'Elevar a avaliação média dos alunos sobre a didática digital dos professores para >Y.', '>Y');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (9, 3, 'Criar um ecossistema de aprendizado contínuo para os educadores.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (25, 9, 'Cumprir X horas médias de treinamento em tecnologias educacionais por docente ao ano.', 'X horas/ano');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (26, 9, 'Publicar Y novos materiais de boas práticas no repositório institucional por trimestre.', 'Y materiais/trimestre');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (27, 9, 'Alcançar Z% de participação ativa dos docentes nas comunidades de prática internas.', 'Z%');
INSERT INTO public.dx_direcionadores (id, nome, descricao) VALUES (4, 'Prontidão Tecnológica', 'Infraestrutura resiliente, cibersegurança e gestão de ativos de TI.');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (10, 4, 'Assegurar estabilidade e escalabilidade da infraestrutura.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (28, 10, 'Garantir um uptime de 99,9% para as plataformas core.', '99,9%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (29, 10, 'Reduzir o Mean Time to Repair (MTTR) de incidentes críticos em X%.', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (30, 10, 'Executar 100% das rotinas de testes de Disaster Recovery (DR) previstas no ano.', '100%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (11, 4, 'Elevar o nível de maturidade em Cibersegurança e Compliance.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (31, 11, 'Zerar incidentes graves de vazamento de dados (Zero Data Breach).', 'Zero Data Breach');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (32, 11, 'Alcançar 100% de conformidade com as diretrizes da LGPD nos processos digitais.', '100%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (33, 11, 'Treinar X% dos colaboradores em conscientização de segurança da informação.', 'X%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (12, 4, 'Otimizar a gestão do ciclo de vida dos ativos de TI.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (34, 12, 'Reduzir a idade média do parque de equipamentos (hardware) para <X anos.', '<X anos');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (35, 12, 'Automatizar Y% dos fluxos de provisionamento de acessos e softwares.', 'Y%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (36, 12, 'Reduzir custos com licenciamento ocioso de software em Z%.', 'Z%');
INSERT INTO public.dx_direcionadores (id, nome, descricao) VALUES (5, 'Novos Modelos de Negócio', 'Receita digital, expansão de mercado e inovação disruptiva ágil.');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (13, 5, 'Diversificar as fontes de receita através de ecossistemas digitais.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (37, 13, 'Lançar X novos produtos, cursos ou serviços 100% digitais no ano.', 'X lançamentos/ano');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (38, 13, 'Aumentar o faturamento bruto proveniente de canais puramente online em Y%.', 'Y%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (39, 13, 'Fechar Z novas parcerias B2B integradas digitalmente à instituição.', 'Z parcerias');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (14, 5, 'Expandir o alcance de mercado superando barreiras geográficas.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (40, 14, 'Aumentar o volume de matrículas/vendas fora da região principal de atuação em X%.', 'X%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (41, 14, 'Reduzir o Custo de Aquisição de Clientes (CAC) em campanhas de captação digital em Y%.', 'Y%');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (42, 14, 'Adaptar/localizar Z% do conteúdo principal para explorar um novo nicho demográfico.', 'Z%');
INSERT INTO public.dx_objetivos (id, direcionador_id, titulo) VALUES (15, 5, 'Validar inovações disruptivas de forma ágil.');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (43, 15, 'Conduzir X Provas de Conceito (PoCs) de novas tecnologias (IA, VR, etc.) com impacto no negócio.', 'X PoCs');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (44, 15, 'Lançar pelo menos 1 iniciativa comercial impulsionada por IA no semestre.', '1+/semestre');
INSERT INTO public.dx_krs (id, objetivo_id, descricao, metrica_alvo_placeholder) VALUES (45, 15, 'Alcançar Y% de adoção inicial nos primeiros 3 meses após o lançamento de novos modelos.', 'Y%');

SELECT setval(pg_get_serial_sequence('public.dx_direcionadores', 'id'), 5, true);
SELECT setval(pg_get_serial_sequence('public.dx_objetivos', 'id'), 15, true);
SELECT setval(pg_get_serial_sequence('public.dx_krs', 'id'), 45, true);

COMMIT;
