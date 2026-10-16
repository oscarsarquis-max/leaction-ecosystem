-- Classificação e conciliação ficam fora da evidência importada.
-- statement_line.classification_state permanece UNCLASSIFIED.
-- A aplicação anterior pode gravar o extrato; estes gatilhos impedem que
-- uma retirada ou um estorno deixem uma conferência ativa sem validade.

create table actionfinance.initiative (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    code varchar(40) not null,
    name varchar(100) not null,
    active boolean not null,
    version bigint not null,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    created_by uuid not null,
    updated_by uuid not null,
    constraint initiative_pk primary key (id),
    constraint initiative_scope_id unique (tenant_id, company_id, id),
    constraint initiative_code_unique unique (tenant_id, company_id, code),
    constraint initiative_company_fk foreign key (tenant_id, company_id)
        references actionfinance.company (tenant_id, id) on delete restrict,
    constraint initiative_code_chk check (code ~ '^[A-Z0-9][A-Z0-9_-]{1,39}$'),
    constraint initiative_version_chk check (version >= 0)
);

create table actionfinance.initiative_history (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    initiative_id uuid not null,
    version bigint not null,
    name varchar(100) not null,
    active boolean not null,
    reason varchar(300) not null,
    changed_at timestamptz not null,
    changed_by uuid not null,
    constraint initiative_history_pk primary key (id),
    constraint initiative_history_version_unique unique (tenant_id, company_id, initiative_id, version),
    constraint initiative_history_fk foreign key (tenant_id, company_id, initiative_id)
        references actionfinance.initiative (tenant_id, company_id, id) on delete restrict
);

create table actionfinance.initiative_application_map (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    application_code varchar(80) not null,
    initiative_id uuid not null,
    created_at timestamptz not null,
    created_by uuid not null,
    constraint initiative_application_map_pk primary key (id),
    constraint initiative_application_map_code_unique unique (tenant_id, company_id, application_code),
    constraint initiative_application_map_fk foreign key (tenant_id, company_id, initiative_id)
        references actionfinance.initiative (tenant_id, company_id, id) on delete restrict
);

create table actionfinance.allocation_rule (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    name varchar(100) not null,
    active boolean not null,
    version bigint not null,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    created_by uuid not null,
    updated_by uuid not null,
    constraint allocation_rule_pk primary key (id),
    constraint allocation_rule_scope_id unique (tenant_id, company_id, id),
    constraint allocation_rule_company_fk foreign key (tenant_id, company_id)
        references actionfinance.company (tenant_id, id) on delete restrict
);

create table actionfinance.allocation_rule_version (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    rule_id uuid not null,
    version_no integer not null,
    valid_from date not null,
    valid_to date,
    note varchar(300),
    created_at timestamptz not null,
    created_by uuid not null,
    constraint allocation_rule_version_pk primary key (id),
    constraint allocation_rule_version_scope_id unique (tenant_id, company_id, id),
    constraint allocation_rule_version_no_unique unique (tenant_id, company_id, rule_id, version_no),
    constraint allocation_rule_version_rule_fk foreign key (tenant_id, company_id, rule_id)
        references actionfinance.allocation_rule (tenant_id, company_id, id) on delete restrict,
    constraint allocation_rule_version_span_chk check (valid_to is null or valid_to >= valid_from)
);

create table actionfinance.allocation_rule_share (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    version_id uuid not null,
    initiative_id uuid not null,
    basis_points integer not null,
    constraint allocation_rule_share_pk primary key (id),
    constraint allocation_rule_share_once unique (tenant_id, company_id, version_id, initiative_id),
    constraint allocation_rule_share_version_fk foreign key (tenant_id, company_id, version_id)
        references actionfinance.allocation_rule_version (tenant_id, company_id, id) on delete restrict,
    constraint allocation_rule_share_initiative_fk foreign key (tenant_id, company_id, initiative_id)
        references actionfinance.initiative (tenant_id, company_id, id) on delete restrict,
    constraint allocation_rule_share_points_chk check (basis_points > 0 and basis_points <= 10000)
);

create table actionfinance.statement_decision (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    line_id uuid not null,
    version bigint not null,
    category_id uuid,
    assignment varchar(16) not null,
    initiative_id uuid,
    rule_version_id uuid,
    basis_minor numeric(19, 0),
    date_basis varchar(16) not null,
    manual_on date,
    review_required boolean not null,
    updated_at timestamptz not null,
    updated_by uuid not null,
    constraint statement_decision_pk primary key (id),
    constraint statement_decision_scope_id unique (tenant_id, company_id, id),
    constraint statement_decision_line_unique unique (tenant_id, company_id, line_id),
    constraint statement_decision_line_fk foreign key (tenant_id, company_id, line_id)
        references actionfinance.statement_line (tenant_id, company_id, id) on delete restrict,
    constraint statement_decision_category_fk foreign key (tenant_id, company_id, category_id)
        references actionfinance.financial_category (tenant_id, company_id, id) on delete restrict,
    constraint statement_decision_initiative_fk foreign key (tenant_id, company_id, initiative_id)
        references actionfinance.initiative (tenant_id, company_id, id) on delete restrict,
    constraint statement_decision_rule_fk foreign key (tenant_id, company_id, rule_version_id)
        references actionfinance.allocation_rule_version (tenant_id, company_id, id) on delete restrict,
    constraint statement_decision_assignment_chk check (assignment in ('UNASSIGNED', 'SINGLE', 'ALLOCATED')),
    constraint statement_decision_date_chk check (date_basis in ('APPROVAL', 'MANUAL', 'ABSENT')),
    constraint statement_decision_shape_chk check (
        (assignment = 'UNASSIGNED' and initiative_id is null and rule_version_id is null)
        or (assignment = 'SINGLE' and initiative_id is not null and rule_version_id is null)
        or (assignment = 'ALLOCATED' and initiative_id is null)
    ),
    constraint statement_decision_basis_chk check (basis_minor is null or basis_minor >= 0)
);

create table actionfinance.statement_decision_share (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    decision_id uuid not null,
    initiative_id uuid,
    amount_minor numeric(19, 0) not null,
    basis_points integer,
    criterion varchar(200) not null,
    constraint statement_decision_share_pk primary key (id),
    constraint statement_decision_share_decision_fk foreign key (tenant_id, company_id, decision_id)
        references actionfinance.statement_decision (tenant_id, company_id, id) on delete restrict,
    constraint statement_decision_share_initiative_fk foreign key (tenant_id, company_id, initiative_id)
        references actionfinance.initiative (tenant_id, company_id, id) on delete restrict,
    constraint statement_decision_share_amount_chk check (amount_minor >= 0)
);

create table actionfinance.statement_decision_history (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    decision_id uuid not null,
    version bigint not null,
    reason varchar(300) not null,
    previous_state jsonb not null,
    next_state jsonb not null,
    changed_at timestamptz not null,
    changed_by uuid not null,
    constraint statement_decision_history_pk primary key (id),
    constraint statement_decision_history_fk foreign key (tenant_id, company_id, decision_id)
        references actionfinance.statement_decision (tenant_id, company_id, id) on delete restrict
);

create unique index statement_occurrence_scope_id_uidx
    on actionfinance.statement_occurrence (tenant_id, company_id, id);

create table actionfinance.statement_occurrence_note (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    occurrence_id uuid not null,
    category_id uuid,
    note varchar(300),
    version bigint not null,
    updated_at timestamptz not null,
    updated_by uuid not null,
    constraint statement_occurrence_note_pk primary key (id),
    constraint statement_occurrence_note_once unique (tenant_id, company_id, occurrence_id),
    constraint statement_occurrence_note_occurrence_fk foreign key (tenant_id, company_id, occurrence_id)
        references actionfinance.statement_occurrence (tenant_id, company_id, id) on delete restrict,
    constraint statement_occurrence_note_category_fk foreign key (tenant_id, company_id, category_id)
        references actionfinance.financial_category (tenant_id, company_id, id) on delete restrict
);

comment on table actionfinance.statement_occurrence_note is
    'Anotação documental de ocorrência sem evento. Não entra em total financeiro nem em conciliação monetária.';

create unique index pay_receipt_txn_scope_id_uidx
    on actionfinance.pay_receipt_transaction (tenant_id, company_id, id);

create table actionfinance.statement_reference_link (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    line_id uuid not null,
    target_kind varchar(16) not null,
    title_id uuid,
    pay_receipt_id uuid,
    compared_basis varchar(16) not null,
    allocated_minor numeric(19, 0) not null,
    status varchar(16) not null,
    version bigint not null,
    updated_at timestamptz not null,
    updated_by uuid not null,
    constraint statement_reference_link_pk primary key (id),
    constraint statement_reference_link_line_fk foreign key (tenant_id, company_id, line_id)
        references actionfinance.statement_line (tenant_id, company_id, id) on delete restrict,
    constraint statement_reference_link_title_fk foreign key (tenant_id, company_id, title_id)
        references actionfinance.financial_title (tenant_id, company_id, id) on delete restrict,
    constraint statement_reference_link_receipt_fk foreign key (tenant_id, company_id, pay_receipt_id)
        references actionfinance.pay_receipt_transaction (tenant_id, company_id, id) on delete restrict,
    constraint statement_reference_link_kind_chk check (target_kind in ('TITLE', 'PAY_RECEIPT')),
    constraint statement_reference_link_basis_chk check (compared_basis in ('GROSS', 'CONFIRMED_PAID', 'NET')),
    constraint statement_reference_link_status_chk check (status in ('ACTIVE', 'UNDONE', 'INVALID')),
    constraint statement_reference_link_amount_chk check (allocated_minor > 0),
    constraint statement_reference_link_target_chk check (
        (target_kind = 'TITLE' and title_id is not null and pay_receipt_id is null)
        or (target_kind = 'PAY_RECEIPT' and pay_receipt_id is not null and title_id is null)
    )
);

create table actionfinance.statement_book_group (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    line_id uuid not null,
    equation varchar(500) not null,
    status varchar(16) not null,
    version bigint not null,
    updated_at timestamptz not null,
    updated_by uuid not null,
    constraint statement_book_group_pk primary key (id),
    constraint statement_book_group_scope_id unique (tenant_id, company_id, id),
    constraint statement_book_group_line_fk foreign key (tenant_id, company_id, line_id)
        references actionfinance.statement_line (tenant_id, company_id, id) on delete restrict,
    constraint statement_book_group_status_chk check (status in ('ACTIVE', 'UNDONE', 'INVALID'))
);

create table actionfinance.statement_book_allocation (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    line_id uuid not null,
    group_id uuid,
    movement_id uuid not null,
    allocated_minor numeric(19, 0) not null,
    movement_sign smallint not null,
    status varchar(16) not null,
    version bigint not null,
    updated_at timestamptz not null,
    updated_by uuid not null,
    constraint statement_book_allocation_pk primary key (id),
    constraint statement_book_allocation_line_fk foreign key (tenant_id, company_id, line_id)
        references actionfinance.statement_line (tenant_id, company_id, id) on delete restrict,
    constraint statement_book_allocation_group_fk foreign key (tenant_id, company_id, group_id)
        references actionfinance.statement_book_group (tenant_id, company_id, id) on delete restrict,
    constraint statement_book_allocation_movement_fk foreign key (tenant_id, company_id, movement_id)
        references actionfinance.cash_movement (tenant_id, company_id, id) on delete restrict,
    constraint statement_book_allocation_amount_chk check (allocated_minor > 0),
    constraint statement_book_allocation_sign_chk check (movement_sign in (-1, 1)),
    constraint statement_book_allocation_status_chk check (status in ('ACTIVE', 'UNDONE', 'INVALID'))
);

create table actionfinance.statement_link_history (
    id uuid not null,
    tenant_id uuid not null,
    company_id uuid not null,
    line_id uuid not null,
    link_kind varchar(16) not null,
    link_id uuid not null,
    action varchar(16) not null,
    reason varchar(300) not null,
    amount_minor numeric(19, 0),
    changed_at timestamptz not null,
    changed_by uuid not null,
    constraint statement_link_history_pk primary key (id),
    constraint statement_link_history_kind_chk check (link_kind in ('REFERENCE', 'BOOK')),
    constraint statement_link_history_action_chk check (action in ('CONFIRMED', 'UNDONE', 'INVALIDATED'))
);

comment on table actionfinance.statement_reference_link is
    'Vínculo de referência. Não baixa título, não altera pago e não concilia o livro.';
comment on table actionfinance.statement_book_allocation is
    'Alocação com o movimento do livro. Não cria outro movimento.';

create or replace function actionfinance.classification_side_effects()
returns trigger
language plpgsql
as $$
begin
    if tg_table_name = 'statement_line' then
        if new.content_hash is distinct from old.content_hash then
            update actionfinance.statement_decision
               set review_required = true
             where tenant_id = new.tenant_id
               and company_id = new.company_id
               and line_id = new.id;
        end if;
        if new.import_status = 'WITHDRAWN' and old.import_status = 'ACTIVE' then
            if exists (
                select 1
                  from actionfinance.statement_occurrence occurrence
                  join actionfinance.statement_batch batch
                    on batch.tenant_id = occurrence.tenant_id
                   and batch.company_id = occurrence.company_id
                   and batch.id = occurrence.batch_id
                 where occurrence.line_id = new.id
                   and batch.status = 'CONFIRMED'
                   and batch.id <> new.batch_id
                   and occurrence.consolidation = 'CONSOLIDATED'
            ) then
                new.import_status := 'ACTIVE';
            else
                insert into actionfinance.statement_link_history (
                    id, tenant_id, company_id, line_id, link_kind, link_id, action, reason, amount_minor, changed_at, changed_by
                )
                select gen_random_uuid(), tenant_id, company_id, line_id, 'BOOK', id, 'INVALIDATED',
                       'A fonte do evento foi retirada e nenhum outro lote confirmado o sustenta.',
                       allocated_minor, now(), '00000000-0000-4000-8000-000000000001'::uuid
                  from actionfinance.statement_book_allocation
                 where tenant_id = new.tenant_id and company_id = new.company_id
                   and line_id = new.id and status = 'ACTIVE'
                union all
                select gen_random_uuid(), tenant_id, company_id, line_id, 'REFERENCE', id, 'INVALIDATED',
                       'A fonte do evento foi retirada e nenhum outro lote confirmado o sustenta.',
                       allocated_minor, now(), '00000000-0000-4000-8000-000000000001'::uuid
                  from actionfinance.statement_reference_link
                 where tenant_id = new.tenant_id and company_id = new.company_id
                   and line_id = new.id and status = 'ACTIVE';
                update actionfinance.statement_book_allocation
                   set status = 'INVALID', updated_at = now()
                 where tenant_id = new.tenant_id and company_id = new.company_id
                   and line_id = new.id and status = 'ACTIVE';
                update actionfinance.statement_book_group
                   set status = 'INVALID', updated_at = now()
                 where tenant_id = new.tenant_id and company_id = new.company_id
                   and line_id = new.id and status = 'ACTIVE';
                update actionfinance.statement_reference_link
                   set status = 'INVALID', updated_at = now()
                 where tenant_id = new.tenant_id and company_id = new.company_id
                   and line_id = new.id and status = 'ACTIVE';
                update actionfinance.statement_decision
                   set review_required = true
                 where tenant_id = new.tenant_id and company_id = new.company_id and line_id = new.id;
            end if;
        end if;
        return new;
    end if;
    return new;
end;
$$;

create trigger statement_line_classification_effects
    before update on actionfinance.statement_line
    for each row
    execute function actionfinance.classification_side_effects();

create or replace function actionfinance.invalidate_book_on_reversal()
returns trigger
language plpgsql
as $$
begin
    insert into actionfinance.statement_link_history (
        id, tenant_id, company_id, line_id, link_kind, link_id, action, reason, amount_minor, changed_at, changed_by
    )
    select gen_random_uuid(), allocation.tenant_id, allocation.company_id, allocation.line_id, 'BOOK', allocation.id,
           'INVALIDATED', 'A baixa associada foi estornada. A conciliação deixou de valer.',
           allocation.allocated_minor, now(), new.recorded_by
      from actionfinance.statement_book_allocation allocation
      join actionfinance.cash_movement movement
        on movement.tenant_id = allocation.tenant_id
       and movement.company_id = allocation.company_id
       and movement.id = allocation.movement_id
     where movement.settlement_id = new.settlement_id
       and movement.kind = 'SETTLEMENT'
       and allocation.status = 'ACTIVE';
    update actionfinance.statement_book_allocation allocation
       set status = 'INVALID', updated_at = now()
      from actionfinance.cash_movement movement
     where movement.tenant_id = new.tenant_id
       and movement.company_id = new.company_id
       and movement.settlement_id = new.settlement_id
       and movement.kind = 'SETTLEMENT'
       and allocation.tenant_id = movement.tenant_id
       and allocation.company_id = movement.company_id
       and allocation.movement_id = movement.id
       and allocation.status = 'ACTIVE';
    update actionfinance.statement_book_group grp
       set status = 'INVALID', updated_at = now()
     where grp.status = 'ACTIVE'
       and grp.tenant_id = new.tenant_id
       and grp.company_id = new.company_id
       and not exists (
           select 1 from actionfinance.statement_book_allocation allocation
            where allocation.group_id = grp.id and allocation.status = 'ACTIVE'
       );
    return new;
end;
$$;

create trigger settlement_reversal_invalidates_book
    after insert on actionfinance.settlement_reversal
    for each row
    execute function actionfinance.invalidate_book_on_reversal();

grant select, insert, update on table
    actionfinance.initiative,
    actionfinance.initiative_history,
    actionfinance.initiative_application_map,
    actionfinance.allocation_rule,
    actionfinance.allocation_rule_version,
    actionfinance.allocation_rule_share,
    actionfinance.statement_decision,
    actionfinance.statement_decision_share,
    actionfinance.statement_decision_history,
    actionfinance.statement_occurrence_note,
    actionfinance.statement_reference_link,
    actionfinance.statement_book_group,
    actionfinance.statement_book_allocation,
    actionfinance.statement_link_history
    to actionfinance_runtime;

grant delete on table actionfinance.statement_decision_share to actionfinance_runtime;

revoke delete on table
    actionfinance.initiative,
    actionfinance.initiative_history,
    actionfinance.initiative_application_map,
    actionfinance.allocation_rule,
    actionfinance.allocation_rule_version,
    actionfinance.allocation_rule_share,
    actionfinance.statement_decision,
    actionfinance.statement_decision_history,
    actionfinance.statement_occurrence_note,
    actionfinance.statement_reference_link,
    actionfinance.statement_book_group,
    actionfinance.statement_book_allocation,
    actionfinance.statement_link_history
    from actionfinance_runtime;

grant execute on function actionfinance.classification_side_effects() to actionfinance_runtime;
grant execute on function actionfinance.invalidate_book_on_reversal() to actionfinance_runtime;
