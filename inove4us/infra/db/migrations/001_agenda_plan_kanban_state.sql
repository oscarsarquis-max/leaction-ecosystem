-- Persistência EduScrum: plano IA + estado do Kanban
-- Aplicado também automaticamente via agenda_routes._ensure_table

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS plan_data JSONB;

ALTER TABLE public.inove_agenda_eventos
    ADD COLUMN IF NOT EXISTS kanban_state JSONB;
