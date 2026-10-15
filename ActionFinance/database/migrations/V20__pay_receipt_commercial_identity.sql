-- Identidade comercial e do pagador informados pelo ActionHub Pay.
-- Não cria contraparte interna, título, baixa nem movimento.

ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN commercial_application VARCHAR(80);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN commercial_description VARCHAR(200);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN payer_kind VARCHAR(16);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN payer_label VARCHAR(200);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN payer_provenance VARCHAR(40);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN payment_method VARCHAR(40);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN processor_name VARCHAR(40);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN provider_status VARCHAR(40);

ALTER TABLE actionfinance.pay_receipt_transaction
    ADD CONSTRAINT pay_receipt_txn_payer_kind_chk
    CHECK (payer_kind IS NULL OR payer_kind IN ('EMAIL', 'SUBJECT', 'ABSENT'));

COMMENT ON COLUMN actionfinance.pay_receipt_transaction.payer_label IS
    'Identidade externa informada pela origem. Não cria cadastro financeiro.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.commercial_application IS
    'Aplicação comercial de origem (ex.: lojadepaes). Distinta do sistema ActionHub Pay.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.processor_name IS
    'Processador só quando a origem evidencia (ex.: Mercado Pago).';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.paid_amount_minor IS
    'Valor pago informado pelo provedor. Só com evidência; não copiar amount_minor.';
