from sqlalchemy import text


def migrate_legacy_schema(engine) -> None:
    """Remove tabelas legadas antes de criar indicadores + medicoes."""
    statement = """
    DROP TABLE IF EXISTS importacao_json CASCADE;
    DROP TABLE IF EXISTS importacoes CASCADE;
    DROP TABLE IF EXISTS indicador_posicao CASCADE;

    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'indicadores'
              AND column_name = 'payload_completo'
        ) THEN
            DROP TABLE indicadores CASCADE;
        END IF;
    END $$;
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def migrate_descricao_indicador_schema(engine) -> None:
    """Remove FK física e UNIQUE isolado em indicadores.cod_indicador."""
    statement = """
    DO $$
    DECLARE
        fk_name TEXT;
    BEGIN
        IF to_regclass('public.descricao_indicador') IS NULL THEN
            RETURN;
        END IF;

        FOR fk_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'descricao_indicador'
              AND con.contype = 'f'
        LOOP
            EXECUTE format(
                'ALTER TABLE descricao_indicador DROP CONSTRAINT %I',
                fk_name
            );
        END LOOP;
    END $$;

    ALTER TABLE indicadores DROP CONSTRAINT IF EXISTS uq_indicadores_cod_indicador;
    DROP INDEX IF EXISTS uq_indicadores_cod_indicador;
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def migrate_colaboradores_schema(engine) -> None:
    """Normaliza colaboradores e FK id_colaborador em medicoes."""
    statement = """
    CREATE TABLE IF NOT EXISTS colaboradores (
        id_colaborador SERIAL PRIMARY KEY,
        matricula VARCHAR(20) NOT NULL UNIQUE,
        nome VARCHAR(150) NOT NULL,
        funcao VARCHAR(100),
        codsetor VARCHAR(20)
    );

    CREATE INDEX IF NOT EXISTS ix_colaboradores_matricula ON colaboradores (matricula);

    ALTER TABLE medicoes DROP COLUMN IF EXISTS colaborador_matricula;

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'medicoes'
              AND column_name = 'id_colaborador'
        ) THEN
            ALTER TABLE medicoes
                ADD COLUMN id_colaborador INTEGER
                REFERENCES colaboradores(id_colaborador) ON DELETE SET NULL;
        END IF;
    END $$;

    CREATE INDEX IF NOT EXISTS ix_medicoes_id_colaborador ON medicoes (id_colaborador);
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def ensure_schema_indexes(engine) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_indicadores_cod_indicador ON indicadores (cod_indicador)",
        "CREATE INDEX IF NOT EXISTS ix_indicadores_nome_grupo ON indicadores (nome_grupo)",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_indicadores_cod_grupo
        ON indicadores (cod_indicador, nome_grupo)
        """,
        """
        CREATE TABLE IF NOT EXISTS descricao_indicador (
            id SERIAL PRIMARY KEY,
            cod_indicador VARCHAR(10) NOT NULL UNIQUE,
            subpapel VARCHAR(50),
            normalizacao VARCHAR(100),
            explicacao TEXT,
            importancia TEXT
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_descricao_indicador_cod_indicador ON descricao_indicador (cod_indicador)",
        "CREATE INDEX IF NOT EXISTS ix_medicoes_indicador_id ON medicoes (indicador_id)",
        "CREATE INDEX IF NOT EXISTS ix_medicoes_id_colaborador ON medicoes (id_colaborador)",
        "CREATE INDEX IF NOT EXISTS ix_medicoes_status_import ON medicoes (status_import)",
        "CREATE INDEX IF NOT EXISTS ix_medicoes_data_importacao ON medicoes (data_importacao)",
        "CREATE INDEX IF NOT EXISTS ix_medicoes_data_referencia ON medicoes (data_referencia)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def migrate_papeis_iaps_schema(engine) -> None:
    """Adiciona papel/subpapel em colaboradores e subpapeis_aplicaveis em indicadores."""
    statement = """
    ALTER TABLE colaboradores
        ADD COLUMN IF NOT EXISTS papel VARCHAR(50),
        ADD COLUMN IF NOT EXISTS subpapel VARCHAR(50);

    ALTER TABLE indicadores
        ADD COLUMN IF NOT EXISTS subpapeis_aplicaveis TEXT[];

    UPDATE indicadores
    SET subpapeis_aplicaveis = ARRAY['Dev', 'Tester']::TEXT[]
    WHERE cod_indicador = 'P007'
      AND (subpapeis_aplicaveis IS NULL OR cardinality(subpapeis_aplicaveis) = 0);
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def migrate_configuracao_pesos_schema(engine) -> None:
    """Cria tabela configuracao_pesos com pesos IAPS por papel/subpapel."""
    statement = """
    CREATE TABLE IF NOT EXISTS configuracao_pesos (
        id SERIAL PRIMARY KEY,
        papel VARCHAR(50) NOT NULL,
        subpapel VARCHAR(50) NOT NULL,
        peso_ind NUMERIC(5, 4) NOT NULL DEFAULT 0.4,
        peso_eq NUMERIC(5, 4) NOT NULL DEFAULT 0.6,
        peso_satisfacao NUMERIC(5, 4) NOT NULL,
        peso_performance NUMERIC(5, 4) NOT NULL,
        peso_atividade NUMERIC(5, 4) NOT NULL,
        peso_comunicacao NUMERIC(5, 4) NOT NULL,
        peso_eficiencia NUMERIC(5, 4) NOT NULL,
        CONSTRAINT uq_configuracao_pesos_papel_subpapel UNIQUE (papel, subpapel)
    );

    CREATE INDEX IF NOT EXISTS ix_configuracao_pesos_papel
        ON configuracao_pesos (papel);
    CREATE INDEX IF NOT EXISTS ix_configuracao_pesos_subpapel
        ON configuracao_pesos (subpapel);
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def migrate_indicadores_motor_regras_schema(engine) -> None:
    """Adiciona fórmula normalizada e parâmetros configuráveis em indicadores."""
    statement = """
    ALTER TABLE indicadores
        ADD COLUMN IF NOT EXISTS formula_normalizada VARCHAR(255),
        ADD COLUMN IF NOT EXISTS parametros_configuraveis JSONB;
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


GESTAO_TECNICA_CATALOGO = [
    {
        "cod_indicador": "S001",
        "nome_indicador": "Carga Cognitiva Individual",
        "nome_grupo": "Técnica",
        "dimensao": "Satisfação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "((mli - 1) / 4) * 100",
        "parametros_configuraveis": {"escala_likert_min": 1, "escala_likert_max": 5},
    },
    {
        "cod_indicador": "S002",
        "nome_indicador": "eNPS do Processo",
        "nome_grupo": "Técnica",
        "dimensao": "Satisfação",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(prom / (prom + detrat)) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P001",
        "nome_indicador": "Business Value per Sprint",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "((ir + sr + rs + eo + rc) / (5 * sc)) * 100",
        "parametros_configuraveis": {"escala_likert": 5},
    },
    {
        "cod_indicador": "P002",
        "nome_indicador": "Product Market Fit",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(ac / ua) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P003",
        "nome_indicador": "Velocidade de Desbloqueio",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(tr / bt) * 100",
        "parametros_configuraveis": {"limite_horas": 4},
    },
    {
        "cod_indicador": "P004",
        "nome_indicador": "Predictability",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(pe / pp) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P005",
        "nome_indicador": "SLA Compliance (Internal)",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(cmpp / zmpt) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P006",
        "nome_indicador": "Business Impact ROI",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(bve / coe) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A001",
        "nome_indicador": "Backlog Health",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(ca / bp) * 100",
        "parametros_configuraveis": {"n_sprints": 3},
    },
    {
        "cod_indicador": "A002",
        "nome_indicador": "Feature Delivery Rate",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(fd / fp) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A003",
        "nome_indicador": "Cerimonias Atendidas",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(pa / ts) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A004",
        "nome_indicador": "Cycle Time Variance",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(dv / mi) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A005",
        "nome_indicador": "Resource Allocation Balance",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "1 - abs(spr - spi)",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A006",
        "nome_indicador": "Strategic Milestone Progress",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(mt / mp) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "C001",
        "nome_indicador": "SLA Compliance (Prazos Técnicos)",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(it / tq) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "C002",
        "nome_indicador": "Cross-team Alignment",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(dr / i3us) * 100",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "C003",
        "nome_indicador": "Team Health Check",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "((gm3s - 1) / 4) * 100",
        "parametros_configuraveis": {"escala_likert_min": 1, "escala_likert_max": 5},
    },
    {
        "cod_indicador": "C004",
        "nome_indicador": "Stakeholder Satisfaction",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "((m3Gs - 1) / 4) * 100",
        "parametros_configuraveis": {"escala_likert_min": 1, "escala_likert_max": 5},
    },
    {
        "cod_indicador": "C005",
        "nome_indicador": "Strategic Stakeholder Trust Score",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "((m3GEs - 1) / 4) * 100",
        "parametros_configuraveis": {"escala_likert_min": 1, "escala_likert_max": 5},
    },
    {
        "cod_indicador": "E001",
        "nome_indicador": "Requirement Lead Time",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(1 - (mwi / mWE)) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "E002",
        "nome_indicador": "Value Stream Efficiency",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(ta / lt) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "E003",
        "nome_indicador": "Meeting Load",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "(hr / fte) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "E004",
        "nome_indicador": "Time to Recover (MTTR)",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(ir / it) * 100",
        "parametros_configuraveis": {"limite_horas": 2},
    },
]

TECNICA_CATALOGO = [
    {
        "cod_indicador": "S001",
        "nome_indicador": "Carga Cognitiva Individual",
        "nome_grupo": "Técnica",
        "dimensao": "Satisfação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "((ml - 1) / 4) * 100",
        "parametros_configuraveis": {"escala_likert_min": 1, "escala_likert_max": 5},
    },
    {
        "cod_indicador": "S002",
        "nome_indicador": "eNPS do Processo",
        "nome_grupo": "Técnica",
        "dimensao": "Satisfação",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(prom / (prom + detrat)) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P007",
        "nome_indicador": "Taxa de Retrabalho",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "1 - (ir / ie)",
        "parametros_configuraveis": {"janela_sprints": 3},
        "subpapeis_aplicaveis": ["Dev", "Tester"],
    },
    {
        "cod_indicador": "P008",
        "nome_indicador": "Change Failure Rate",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "1 - (df / dr)",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P009",
        "nome_indicador": "Aderência Arquitetural",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "1 - (carc / pr)",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "P010",
        "nome_indicador": "Stability Index",
        "nome_grupo": "Técnica",
        "dimensao": "Performance",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "(mtbf * ip) / tt",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A007",
        "nome_indicador": "Throughput de PRs",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "pra / mvt",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "A008",
        "nome_indicador": "Deployment Frequency",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "dprod / dup",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "A009",
        "nome_indicador": "Test Coverage",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "sta / sdp",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "A010",
        "nome_indicador": "Defect Detection Efficiency (DDE)",
        "nome_grupo": "Técnica",
        "dimensao": "Atividade",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "btes / (btes + bprod)",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "C006",
        "nome_indicador": "Review Response Time",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "trev / mter",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "C007",
        "nome_indicador": "Knowledge Spread (Bus Factor)",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "comcod / pcrit",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "C008",
        "nome_indicador": "Documentação Técnica",
        "nome_grupo": "Técnica",
        "dimensao": "Comunicação",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "wdr / ics",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "E005",
        "nome_indicador": "Focus Time (Deep Work)",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "((ttj - trs) / 2) / (bet / bfl)",
        "parametros_configuraveis": {"bloco_flow_horas": 2},
    },
    {
        "cod_indicador": "E006",
        "nome_indicador": "Flow Efficiency",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "tec / ctt",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "E007",
        "nome_indicador": "Time to Sandbox",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Individual",
        "formula_normalizada": "1 - (rttdev / 8)",
        "parametros_configuraveis": {"limite_horas": 8},
    },
    {
        "cod_indicador": "E008",
        "nome_indicador": "Cycle Time",
        "nome_grupo": "Técnica",
        "dimensao": "Eficiência",
        "nivel_avaliacao": "Equipe",
        "formula_normalizada": "1 - (dpcy / mcy)",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
]

CATALOGO_TECNICA_COMPLETO = [*GESTAO_TECNICA_CATALOGO, *TECNICA_CATALOGO]

FORMULAS_INDICADORES_LEGADO = [
    {
        "cod_indicador": "P007",
        "nome_grupo": "Gerência Técnica",
        "formula_normalizada": "1 - (ir / ie)",
        "parametros_configuraveis": {"janela_sprints": 3},
    },
    {
        "cod_indicador": "P003",
        "nome_grupo": "Gerência Técnica",
        "formula_normalizada": "(tr / bt) * 100",
        "parametros_configuraveis": {"limite_horas": 4},
    },
    {
        "cod_indicador": "P004",
        "nome_grupo": "Gerência Técnica",
        "formula_normalizada": "(pe / pp) * 100",
        "parametros_configuraveis": {},
    },
    {
        "cod_indicador": "P001",
        "nome_grupo": "Gestão Geral",
        "formula_normalizada": "((ir + sr + rs + eo + rc) / (5 * sc)) * 100",
        "parametros_configuraveis": {"escala_likert": 5},
    },
    {
        "cod_indicador": "P005",
        "nome_grupo": "Gestão Geral",
        "formula_normalizada": "(cmpp / zmpt) * 100",
        "parametros_configuraveis": {},
    },
]

FORMULAS_INDICADORES_PADRAO = [
    *[
        {
            "cod_indicador": item["cod_indicador"],
            "nome_grupo": item["nome_grupo"],
            "formula_normalizada": item["formula_normalizada"],
            "parametros_configuraveis": item["parametros_configuraveis"],
        }
        for item in CATALOGO_TECNICA_COMPLETO
    ],
    *FORMULAS_INDICADORES_LEGADO,
]


def upsert_catalogo_tecnica(engine) -> None:
    """Insere ou atualiza indicadores das planilhas Gestão Técnica e Técnica."""
    import json

    with engine.begin() as connection:
        for item in CATALOGO_TECNICA_COMPLETO:
            subpapeis = item.get("subpapeis_aplicaveis")
            connection.execute(
                text(
                    """
                    INSERT INTO indicadores (
                        cod_indicador,
                        nome_indicador,
                        nome_grupo,
                        dimensao,
                        nivel_avaliacao,
                        formula_normalizada,
                        parametros_configuraveis,
                        subpapeis_aplicaveis
                    )
                    VALUES (
                        :cod, :nome, :grupo, :dimensao, :nivel, :formula,
                        CAST(:parametros AS jsonb), :subpapeis
                    )
                    ON CONFLICT (cod_indicador, nome_grupo)
                    DO UPDATE SET
                        nome_indicador = EXCLUDED.nome_indicador,
                        dimensao = EXCLUDED.dimensao,
                        nivel_avaliacao = EXCLUDED.nivel_avaliacao,
                        formula_normalizada = EXCLUDED.formula_normalizada,
                        parametros_configuraveis = EXCLUDED.parametros_configuraveis,
                        subpapeis_aplicaveis = COALESCE(
                            EXCLUDED.subpapeis_aplicaveis,
                            indicadores.subpapeis_aplicaveis
                        )
                    """
                ),
                {
                    "cod": item["cod_indicador"],
                    "nome": item["nome_indicador"],
                    "grupo": item["nome_grupo"],
                    "dimensao": item["dimensao"],
                    "nivel": item["nivel_avaliacao"],
                    "formula": item["formula_normalizada"],
                    "parametros": json.dumps(item["parametros_configuraveis"]),
                    "subpapeis": subpapeis,
                },
            )


def upsert_gestao_tecnica_catalogo(engine) -> None:
    """Alias de compatibilidade."""
    upsert_catalogo_tecnica(engine)


def seed_formulas_indicadores_padrao(engine) -> None:
    """Atualiza fórmulas normalizadas do catálogo mestre."""
    import json

    with engine.begin() as connection:
        for item in FORMULAS_INDICADORES_PADRAO:
            connection.execute(
                text(
                    """
                    UPDATE indicadores
                    SET formula_normalizada = :formula,
                        parametros_configuraveis = CAST(:parametros AS jsonb)
                    WHERE cod_indicador = :cod
                      AND (:grupo IS NULL OR nome_grupo = :grupo)
                    """
                ),
                {
                    "formula": item["formula_normalizada"],
                    "parametros": json.dumps(item["parametros_configuraveis"]),
                    "cod": item["cod_indicador"],
                    "grupo": item.get("nome_grupo"),
                },
            )


def corrigir_payload_seed_apd_p007(engine) -> None:
    """Inclui variáveis IR/IE no payload do seed APD para P007 (score 66,66%)."""
    statement = """
    UPDATE medicoes m
    SET payload = jsonb_set(
          jsonb_set(
            COALESCE(m.payload, '{}'::jsonb),
            '{resumo,ie}',
            '3'::jsonb,
            true
          ),
          '{resumo,ir}',
          '1'::jsonb,
          true
        )
    FROM indicadores i
    WHERE m.indicador_id = i.id
      AND i.cod_indicador = 'P007'
      AND m.nome_arquivo LIKE 'seed_apd_%'
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def migrate_analises_inteligentes_schema(engine) -> None:
    statement = """
    CREATE TABLE IF NOT EXISTS analises_inteligentes (
        id SERIAL PRIMARY KEY,
        id_colaborador INTEGER NOT NULL
            REFERENCES colaboradores(id_colaborador) ON DELETE CASCADE,
        hash_contexto VARCHAR(64) NOT NULL,
        resultado JSONB NOT NULL,
        modelo VARCHAR(120),
        provider VARCHAR(50),
        gerado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_analises_inteligentes_colaborador UNIQUE (id_colaborador)
    );

    CREATE INDEX IF NOT EXISTS ix_analises_inteligentes_colaborador
        ON analises_inteligentes (id_colaborador);
    """
    with engine.begin() as connection:
        connection.execute(text(statement))


def upgrade_schema(engine) -> None:
    migrate_legacy_schema(engine)
    migrate_descricao_indicador_schema(engine)
    migrate_colaboradores_schema(engine)
    migrate_papeis_iaps_schema(engine)
    migrate_configuracao_pesos_schema(engine)
    migrate_indicadores_motor_regras_schema(engine)
    migrate_analises_inteligentes_schema(engine)
    upsert_catalogo_tecnica(engine)
    seed_formulas_indicadores_padrao(engine)
    corrigir_payload_seed_apd_p007(engine)
