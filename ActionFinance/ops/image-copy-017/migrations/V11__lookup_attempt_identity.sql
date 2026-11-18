-- Identidade estável de tentativa. Não altera V1–V10.
-- Uma linha por tentativa: início e conclusão no mesmo id. Eventos V10 sem pares permanecem órfãos.

ALTER TABLE actionfinance.lookup_attempt
    ADD COLUMN started_at TIMESTAMPTZ,
    ADD COLUMN completed_at TIMESTAMPTZ,
    ADD COLUMN received_outcome VARCHAR(24),
    ADD COLUMN observation_applied BOOLEAN,
    ADD COLUMN discarded_reason VARCHAR(24),
    ADD COLUMN attempt_correlation_id VARCHAR(80);

UPDATE actionfinance.lookup_attempt
    SET started_at = created_at
    WHERE started_at IS NULL;

UPDATE actionfinance.lookup_attempt
    SET completed_at = created_at,
        received_outcome = outcome
    WHERE outcome <> 'STARTED'
      AND completed_at IS NULL;

ALTER TABLE actionfinance.lookup_attempt
    ADD CONSTRAINT lookup_attempt_discarded_chk CHECK (
        discarded_reason IS NULL
        OR discarded_reason IN ('CONCURRENT', 'STALE', 'RECOVERED')
    );

ALTER TABLE actionfinance.external_operation
    ADD COLUMN last_attempt_id UUID;

COMMENT ON TABLE actionfinance.lookup_attempt IS
    'Uma linha por tentativa de consulta (início e conclusão no mesmo id). Não é fila outbox. Linhas V10 com ids distintos STARTED/resultado não são pareadas.';
COMMENT ON COLUMN actionfinance.lookup_attempt.observation_applied IS
    'Verdadeiro só quando a observação financeira foi gravada por updateIfVersion desta tentativa.';
COMMENT ON COLUMN actionfinance.lookup_attempt.discarded_reason IS
    'CONCURRENT/STALE/RECOVERED. Nulo se a tentativa concluiu sem descarte de observação.';
COMMENT ON COLUMN actionfinance.lookup_attempt.attempt_correlation_id IS
    'Correlação do salto desta tentativa. Distinta da correlação estável da operação.';

GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.lookup_attempt TO actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.lookup_attempt FROM actionfinance_runtime;
