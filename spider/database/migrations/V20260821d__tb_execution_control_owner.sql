-- SPIDER-PROMPT-006 — ownership técnico de execução (aditiva)

ALTER TABLE tb_execution_control
  ADD COLUMN IF NOT EXISTS owner_principal_ref varchar(200);

CREATE INDEX IF NOT EXISTS ix_tb_execution_control_owner
  ON tb_execution_control (owner_principal_ref)
  WHERE owner_principal_ref IS NOT NULL;
