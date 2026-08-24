"""Action Execution Workspace Ágil V1 (ISOI-007).

Revision ID: 20260824_0023
Revises: 20260819_0022
Create Date: 2026-08-24
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260824_0023"
down_revision = "20260819_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            -- Squads
            CREATE TABLE IF NOT EXISTS agile_squads (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              name text NOT NULL,
              purpose text NOT NULL DEFAULT '',
              status text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
              default_sprint_length_days integer NOT NULL DEFAULT 14
                CHECK (default_sprint_length_days > 0 AND default_sprint_length_days <= 90),
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_agile_squads_id_org UNIQUE (id, organization_id)
            );
            CREATE INDEX IF NOT EXISTS ix_agile_squads_org_status
              ON agile_squads (organization_id, status);

            CREATE TABLE IF NOT EXISTS agile_squad_memberships (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              squad_id uuid NOT NULL,
              membership_id uuid NOT NULL,
              agile_role text NOT NULL
                CHECK (agile_role IN (
                  'value_owner', 'facilitator', 'execution_member', 'stakeholder'
                )),
              status text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_agile_squad_memberships_id_org UNIQUE (id, organization_id),
              CONSTRAINT uq_agile_squad_member_role
                UNIQUE (squad_id, membership_id, agile_role),
              CONSTRAINT fk_agile_sm_squad_org
                FOREIGN KEY (squad_id, organization_id)
                REFERENCES agile_squads (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_agile_sm_membership_org
                FOREIGN KEY (membership_id, organization_id)
                REFERENCES memberships (id, organization_id)
            );
            CREATE INDEX IF NOT EXISTS ix_agile_sm_squad_status
              ON agile_squad_memberships (squad_id, status);

            -- Sprints
            CREATE TABLE IF NOT EXISTS agile_sprints (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              squad_id uuid NOT NULL,
              name text NOT NULL,
              goal text NOT NULL DEFAULT '',
              starts_at timestamptz NOT NULL,
              ends_at timestamptz NOT NULL,
              timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
              status text NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'active', 'completed', 'cancelled')),
              capacity_points integer
                CHECK (capacity_points IS NULL OR capacity_points > 0),
              wip_limit_in_progress integer
                CHECK (wip_limit_in_progress IS NULL OR wip_limit_in_progress > 0),
              activation_skip_cards_rationale text,
              created_by uuid NOT NULL REFERENCES users (id),
              activated_by uuid REFERENCES users (id),
              closed_by uuid REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              activated_at timestamptz,
              closed_at timestamptz,
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_agile_sprints_id_org UNIQUE (id, organization_id),
              CONSTRAINT ck_agile_sprints_dates CHECK (ends_at > starts_at),
              CONSTRAINT fk_agile_sprints_squad_org
                FOREIGN KEY (squad_id, organization_id)
                REFERENCES agile_squads (id, organization_id) ON DELETE CASCADE
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agile_sprints_one_active
              ON agile_sprints (squad_id)
              WHERE status = 'active';
            CREATE INDEX IF NOT EXISTS ix_agile_sprints_org_status
              ON agile_sprints (organization_id, status);

            -- Sprint cards (ActionItem allocation)
            CREATE TABLE IF NOT EXISTS agile_sprint_cards (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              sprint_id uuid NOT NULL,
              action_item_id uuid NOT NULL,
              priority text NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('critical', 'high', 'medium', 'low')),
              estimate_points integer
                CHECK (estimate_points IS NULL OR estimate_points > 0),
              position integer NOT NULL DEFAULT 0,
              committed_at timestamptz NOT NULL DEFAULT now(),
              removed_at timestamptz,
              removal_reason text,
              carried_from_sprint_id uuid,
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_agile_sprint_cards_id_org UNIQUE (id, organization_id),
              CONSTRAINT fk_agile_sc_sprint_org
                FOREIGN KEY (sprint_id, organization_id)
                REFERENCES agile_sprints (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_agile_sc_action_org
                FOREIGN KEY (action_item_id, organization_id)
                REFERENCES action_items (id, organization_id),
              CONSTRAINT fk_agile_sc_carry_sprint
                FOREIGN KEY (carried_from_sprint_id, organization_id)
                REFERENCES agile_sprints (id, organization_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agile_sc_active_allocation
              ON agile_sprint_cards (action_item_id)
              WHERE removed_at IS NULL;
            CREATE INDEX IF NOT EXISTS ix_agile_sc_sprint_pos
              ON agile_sprint_cards (sprint_id, position)
              WHERE removed_at IS NULL;

            -- Check-ins (append-only)
            CREATE TABLE IF NOT EXISTS action_execution_check_ins (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              action_item_id uuid NOT NULL,
              sprint_id uuid,
              health text NOT NULL
                CHECK (health IN ('on_track', 'attention', 'blocked')),
              progress_note text NOT NULL,
              next_step text NOT NULL DEFAULT '',
              reported_by uuid NOT NULL REFERENCES users (id),
              reported_at timestamptz NOT NULL DEFAULT now(),
              idempotency_key text,
              CONSTRAINT uq_action_checkins_id_org UNIQUE (id, organization_id),
              CONSTRAINT fk_checkin_action_org
                FOREIGN KEY (action_item_id, organization_id)
                REFERENCES action_items (id, organization_id),
              CONSTRAINT fk_checkin_sprint_org
                FOREIGN KEY (sprint_id, organization_id)
                REFERENCES agile_sprints (id, organization_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_action_checkins_idempotency
              ON action_execution_check_ins (organization_id, action_item_id, idempotency_key)
              WHERE idempotency_key IS NOT NULL;
            CREATE INDEX IF NOT EXISTS ix_action_checkins_item_reported
              ON action_execution_check_ins (action_item_id, reported_at DESC);

            -- Impediments
            CREATE TABLE IF NOT EXISTS action_impediments (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              action_item_id uuid NOT NULL,
              sprint_id uuid,
              title text NOT NULL,
              description text NOT NULL DEFAULT '',
              severity text NOT NULL DEFAULT 'medium'
                CHECK (severity IN ('low', 'medium', 'high', 'critical')),
              status text NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'resolved', 'cancelled')),
              owner_membership_id uuid,
              opened_by uuid NOT NULL REFERENCES users (id),
              opened_at timestamptz NOT NULL DEFAULT now(),
              resolved_by uuid REFERENCES users (id),
              resolved_at timestamptz,
              resolution_note text,
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_action_impediments_id_org UNIQUE (id, organization_id),
              CONSTRAINT fk_impediment_action_org
                FOREIGN KEY (action_item_id, organization_id)
                REFERENCES action_items (id, organization_id),
              CONSTRAINT fk_impediment_sprint_org
                FOREIGN KEY (sprint_id, organization_id)
                REFERENCES agile_sprints (id, organization_id),
              CONSTRAINT fk_impediment_owner_org
                FOREIGN KEY (owner_membership_id, organization_id)
                REFERENCES memberships (id, organization_id)
            );
            CREATE INDEX IF NOT EXISTS ix_action_impediments_item_status
              ON action_impediments (action_item_id, status);

            -- Dependencies
            CREATE TABLE IF NOT EXISTS action_dependencies (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              predecessor_action_item_id uuid NOT NULL,
              dependent_action_item_id uuid NOT NULL,
              dependency_type text NOT NULL
                CHECK (dependency_type IN ('blocks', 'relates_to')),
              status text NOT NULL DEFAULT 'active',
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              removed_by uuid REFERENCES users (id),
              removed_at timestamptz,
              removal_reason text,
              CONSTRAINT uq_action_deps_id_org UNIQUE (id, organization_id),
              CONSTRAINT ck_action_deps_no_self CHECK (
                predecessor_action_item_id <> dependent_action_item_id
              ),
              CONSTRAINT ck_action_deps_status CHECK (status IN ('active', 'removed')),
              CONSTRAINT fk_dep_pred_org
                FOREIGN KEY (predecessor_action_item_id, organization_id)
                REFERENCES action_items (id, organization_id),
              CONSTRAINT fk_dep_dep_org
                FOREIGN KEY (dependent_action_item_id, organization_id)
                REFERENCES action_items (id, organization_id)
            );

            -- Repair path: 0023 shipped earlier without soft-delete columns.
            ALTER TABLE action_dependencies
              ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
            ALTER TABLE action_dependencies
              ADD COLUMN IF NOT EXISTS removed_by uuid REFERENCES users (id);
            ALTER TABLE action_dependencies
              ADD COLUMN IF NOT EXISTS removed_at timestamptz;
            ALTER TABLE action_dependencies
              ADD COLUMN IF NOT EXISTS removal_reason text;
            ALTER TABLE action_dependencies
              DROP CONSTRAINT IF EXISTS ck_action_deps_status;
            ALTER TABLE action_dependencies
              ADD CONSTRAINT ck_action_deps_status CHECK (status IN ('active', 'removed'));
            ALTER TABLE action_dependencies
              DROP CONSTRAINT IF EXISTS uq_action_deps_pair_type;

            CREATE UNIQUE INDEX IF NOT EXISTS uq_action_deps_active_pair_type
              ON action_dependencies (
                organization_id,
                predecessor_action_item_id,
                dependent_action_item_id,
                dependency_type
              )
              WHERE status = 'active';
            CREATE INDEX IF NOT EXISTS ix_action_deps_pred
              ON action_dependencies (predecessor_action_item_id)
              WHERE status = 'active';
            CREATE INDEX IF NOT EXISTS ix_action_deps_dep
              ON action_dependencies (dependent_action_item_id)
              WHERE status = 'active';

            -- Ceremony records (append-only / new revision)
            CREATE TABLE IF NOT EXISTS agile_ceremony_records (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              sprint_id uuid NOT NULL,
              agenda_event_id uuid NOT NULL,
              ceremony_type text NOT NULL
                CHECK (ceremony_type IN (
                  'sprint_planning', 'daily_check_in', 'sprint_review', 'retrospective'
                )),
              summary text NOT NULL DEFAULT '',
              decisions text NOT NULL DEFAULT '',
              follow_up text NOT NULL DEFAULT '',
              recorded_by uuid NOT NULL REFERENCES users (id),
              recorded_at timestamptz NOT NULL DEFAULT now(),
              revision integer NOT NULL DEFAULT 1,
              CONSTRAINT uq_agile_ceremony_id_org UNIQUE (id, organization_id),
              CONSTRAINT fk_ceremony_sprint_org
                FOREIGN KEY (sprint_id, organization_id)
                REFERENCES agile_sprints (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_ceremony_agenda_org
                FOREIGN KEY (agenda_event_id, organization_id)
                REFERENCES agenda_events (id, organization_id)
            );
            CREATE INDEX IF NOT EXISTS ix_agile_ceremony_sprint
              ON agile_ceremony_records (sprint_id, ceremony_type, recorded_at DESC);

            -- Agenda: sprint link + ceremony event types
            ALTER TABLE agenda_events
              ADD COLUMN IF NOT EXISTS sprint_id uuid;
            ALTER TABLE agenda_events
              DROP CONSTRAINT IF EXISTS fk_agenda_events_sprint_org;
            ALTER TABLE agenda_events
              ADD CONSTRAINT fk_agenda_events_sprint_org
                FOREIGN KEY (sprint_id, organization_id)
                REFERENCES agile_sprints (id, organization_id);
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS agenda_events_event_type_check;
            ALTER TABLE agenda_events
              ADD CONSTRAINT agenda_events_event_type_check
              CHECK (event_type IN (
                'interview', 'meeting', 'visit', 'reminder',
                'milestone', 'deadline', 'other',
                'sprint_planning', 'daily_check_in', 'sprint_review', 'retrospective'
              ));

            -- RLS
            ALTER TABLE agile_squads ENABLE ROW LEVEL SECURITY;
            ALTER TABLE agile_squads FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON agile_squads;
            CREATE POLICY tenant_isolation ON agile_squads FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE agile_squad_memberships ENABLE ROW LEVEL SECURITY;
            ALTER TABLE agile_squad_memberships FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON agile_squad_memberships;
            CREATE POLICY tenant_isolation ON agile_squad_memberships FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE agile_sprints ENABLE ROW LEVEL SECURITY;
            ALTER TABLE agile_sprints FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON agile_sprints;
            CREATE POLICY tenant_isolation ON agile_sprints FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE agile_sprint_cards ENABLE ROW LEVEL SECURITY;
            ALTER TABLE agile_sprint_cards FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON agile_sprint_cards;
            CREATE POLICY tenant_isolation ON agile_sprint_cards FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE action_execution_check_ins ENABLE ROW LEVEL SECURITY;
            ALTER TABLE action_execution_check_ins FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON action_execution_check_ins;
            CREATE POLICY tenant_isolation ON action_execution_check_ins FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE action_impediments ENABLE ROW LEVEL SECURITY;
            ALTER TABLE action_impediments FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON action_impediments;
            CREATE POLICY tenant_isolation ON action_impediments FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE action_dependencies ENABLE ROW LEVEL SECURITY;
            ALTER TABLE action_dependencies FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON action_dependencies;
            CREATE POLICY tenant_isolation ON action_dependencies FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE agile_ceremony_records ENABLE ROW LEVEL SECURITY;
            ALTER TABLE agile_ceremony_records FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON agile_ceremony_records;
            CREATE POLICY tenant_isolation ON agile_ceremony_records FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON
              agile_squads,
              agile_squad_memberships,
              agile_sprints,
              agile_sprint_cards,
              action_execution_check_ins,
              action_impediments,
              agile_ceremony_records
              TO qmind_app;

            -- Dependencies are soft-deleted: the app must never lose the edge.
            GRANT SELECT, INSERT, UPDATE ON action_dependencies TO qmind_app;
            REVOKE DELETE ON action_dependencies FROM qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS fk_agenda_events_sprint_org;
            ALTER TABLE agenda_events DROP COLUMN IF EXISTS sprint_id;
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS agenda_events_event_type_check;
            DROP TABLE IF EXISTS agile_ceremony_records;
            -- Ceremony events only exist because of this revision.
            DELETE FROM agenda_events WHERE event_type IN (
              'sprint_planning', 'daily_check_in', 'sprint_review', 'retrospective'
            );
            ALTER TABLE agenda_events
              ADD CONSTRAINT agenda_events_event_type_check
              CHECK (event_type IN (
                'interview', 'meeting', 'visit', 'reminder',
                'milestone', 'deadline', 'other'
              ));
            DROP TABLE IF EXISTS action_dependencies;
            DROP TABLE IF EXISTS action_impediments;
            DROP TABLE IF EXISTS action_execution_check_ins;
            DROP TABLE IF EXISTS agile_sprint_cards;
            DROP TABLE IF EXISTS agile_sprints;
            DROP TABLE IF EXISTS agile_squad_memberships;
            DROP TABLE IF EXISTS agile_squads;
            """
        )
    )
