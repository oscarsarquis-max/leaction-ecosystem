-- CNPJ da própria empresa, sem máscara. Nulo quando não informado.
-- Nenhum número de cliente entra neste script.

alter table actionfinance.company
    add column if not exists cnpj varchar(14);

alter table actionfinance.company
    drop constraint if exists company_cnpj_chk;

alter table actionfinance.company
    add constraint company_cnpj_chk
        check (cnpj is null or cnpj ~ '^[0-9]{14}$');

comment on column actionfinance.company.cnpj is
    'CNPJ da empresa, 14 dígitos, sem máscara. Nulo quando não informado.';
