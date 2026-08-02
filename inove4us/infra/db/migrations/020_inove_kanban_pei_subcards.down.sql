-- Rollback 020_inove_kanban_pei_subcards.sql

BEGIN;

DROP TABLE IF EXISTS public.inove_kanban_cards;

COMMIT;
