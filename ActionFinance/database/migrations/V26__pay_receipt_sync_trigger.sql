-- Origem da execução de sincronização. Não cria recebimento, título, baixa nem saldo.
-- Registros anteriores a esta coluna foram iniciados pelo botão.

alter table actionfinance.pay_receipt_sync_run
    add column trigger_kind varchar(16) not null default 'MANUAL';

alter table actionfinance.pay_receipt_sync_run
    add constraint pay_receipt_sync_run_trigger_chk
        check (trigger_kind in ('MANUAL', 'AUTOMATIC'));
