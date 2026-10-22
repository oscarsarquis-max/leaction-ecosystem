-- Dados cadastrais da conta. Não cria movimento, título, baixa, saldo nem vínculo de origem.
-- Contas já gravadas permanecem com estes campos nulos até preenchimento explícito.

alter table actionfinance.financial_account
    add column institution_name varchar(120),
    add column bank_code varchar(8),
    add column bank_modality varchar(24),
    add column branch_number varchar(12),
    add column branch_digit varchar(4),
    add column account_number varchar(32),
    add column account_digit varchar(4),
    add column country_code char(2),
    add column institution_email varchar(160),
    add column institution_phone varchar(40);

alter table actionfinance.financial_account
    add constraint financial_account_modality_chk check (
        bank_modality is null or bank_modality in ('CHECKING', 'SAVINGS', 'INVESTMENT', 'PAYMENT')
    ),
    add constraint financial_account_country_chk check (
        country_code is null or country_code = upper(country_code)
    );

alter table actionfinance.financial_account_history
    drop constraint financial_account_history_action_chk;

alter table actionfinance.financial_account_history
    add constraint financial_account_history_action_chk check (
        action in ('CREATED', 'RENAMED', 'DEACTIVATED', 'REACTIVATED', 'PROFILE_UPDATED')
    );

create table actionfinance.financial_account_contact (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    account_id uuid not null,
    person_name varchar(80) not null,
    contact_role varchar(24) not null,
    email varchar(160),
    phone varchar(40),
    primary_contact boolean not null,
    association varchar(24) not null,
    sort_order integer not null,
    removed_at timestamptz,
    created_at timestamptz not null,
    created_by uuid not null,
    constraint financial_account_contact_pk primary key (id),
    constraint financial_account_contact_scope_id unique (tenant_id, company_id, id),
    constraint financial_account_contact_company_fk foreign key (tenant_id, company_id)
        references actionfinance.company (tenant_id, id) on delete restrict,
    constraint financial_account_contact_account_fk foreign key (tenant_id, company_id, account_id)
        references actionfinance.financial_account (tenant_id, company_id, id) on delete restrict,
    constraint financial_account_contact_role_chk check (
        contact_role in ('ACCOUNT_MANAGER', 'BRANCH_MANAGER', 'SERVICE', 'OTHER')
    ),
    constraint financial_account_contact_association_chk check (
        association in ('ACCOUNT', 'BRANCH', 'INSTITUTION')
    )
);

create index financial_account_contact_account_idx
    on actionfinance.financial_account_contact (tenant_id, company_id, account_id)
    where removed_at is null;

grant select, insert, update on table actionfinance.financial_account_contact to actionfinance_runtime;
revoke delete on table actionfinance.financial_account_contact from actionfinance_runtime;
