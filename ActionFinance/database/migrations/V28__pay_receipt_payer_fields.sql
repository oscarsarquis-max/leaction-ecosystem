-- Pagador e pedido copiados da listagem 1.6. Sem valor padrão e sem backfill.
-- Não cria contraparte, título, baixa nem movimento.

ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN payer_name VARCHAR(200);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN payer_email VARCHAR(200);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN store_order_reference VARCHAR(80);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN store_payment_request_id VARCHAR(80);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN processor_payment_id VARCHAR(80);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN purchase_description VARCHAR(200);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN processor_approved_at VARCHAR(64);
ALTER TABLE actionfinance.pay_receipt_transaction
    ADD COLUMN processor_installments INTEGER;

COMMENT ON COLUMN actionfinance.pay_receipt_transaction.payer_name IS
    'Nome do pagador informado pela listagem. Nulo quando a origem não enviou.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.payer_email IS
    'E-mail do pagador informado pela listagem. Nulo quando ausente ou técnico.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.processor_approved_at IS
    'Instante de aprovação como texto ISO recebido. Não é convertido.';
COMMENT ON COLUMN actionfinance.pay_receipt_transaction.processor_installments IS
    'Número de parcelas recebido. Nulo quando a origem não enviou.';
