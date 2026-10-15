-- O relatório de liquidação é um perfil próprio. O CSV de laboratório permanece.
-- A versão do parser continua fora da chave do evento.

alter table actionfinance.statement_batch
    drop constraint statement_batch_profile_chk;

alter table actionfinance.statement_batch
    add constraint statement_batch_profile_chk
        check (profile_id in ('mp-account-money-csv-1', 'mp-settlement-v2-csv-1'));
