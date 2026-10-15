-- Ocorrência do documento. Não é a identidade financeira entre arquivos.
-- Hash do arquivo mais a posição identificam a linha naquele lote.
-- Evento consolidado continua em statement_line, só quando a chave distingue.

alter table actionfinance.statement_line
    add column availability varchar(16) not null default 'UNKNOWN';

alter table actionfinance.statement_line
    add constraint statement_line_availability_chk
        check (availability in ('RELEASED', 'UNRELEASED', 'UNKNOWN'));

create table actionfinance.statement_occurrence (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    batch_id uuid not null,
    source_line_number integer not null,
    document_key varchar(90) not null,
    event_key varchar(220),
    content_hash char(64) not null,
    availability varchar(16) not null,
    consolidation varchar(16) not null,
    exclusion_code varchar(40),
    in_partial_total boolean not null,
    line_id uuid,
    source_id varchar(80) not null,
    record_type varchar(24) not null,
    description varchar(300),
    effective_on date,
    direction varchar(8) not null,
    event_kind varchar(24) not null,
    gross_minor numeric(19, 0),
    gross_absent boolean not null,
    fee_minor numeric(19, 0),
    fee_absent boolean not null,
    net_minor numeric(19, 0),
    net_absent boolean not null,
    raw_text varchar(2000) not null,
    truncated boolean not null,
    created_at timestamptz not null,
    constraint statement_occurrence_pk primary key (id),
    constraint statement_occurrence_position_uidx unique (tenant_id, company_id, batch_id, source_line_number),
    constraint statement_occurrence_company_fk foreign key (tenant_id, company_id)
        references actionfinance.company (tenant_id, id) on delete restrict,
    constraint statement_occurrence_batch_fk foreign key (tenant_id, company_id, batch_id)
        references actionfinance.statement_batch (tenant_id, company_id, id) on delete restrict,
    constraint statement_occurrence_line_fk foreign key (tenant_id, company_id, line_id)
        references actionfinance.statement_line (tenant_id, company_id, id) on delete restrict,
    constraint statement_occurrence_availability_chk check (availability in ('RELEASED', 'UNRELEASED', 'UNKNOWN')),
    constraint statement_occurrence_consolidation_chk check (consolidation in ('CONSOLIDATED', 'IN_REVIEW')),
    constraint statement_occurrence_direction_chk check (direction in ('IN', 'OUT', 'NONE')),
    constraint statement_occurrence_hash_chk check (content_hash ~ '^[0-9a-f]{64}$')
);

comment on table actionfinance.statement_occurrence is
    'Ocorrência preservada do arquivo. document_key é o hash do arquivo e a posição; não prova o evento entre importações.';

grant select, insert on table actionfinance.statement_occurrence to actionfinance_runtime;
revoke update, delete on table actionfinance.statement_occurrence from actionfinance_runtime;
