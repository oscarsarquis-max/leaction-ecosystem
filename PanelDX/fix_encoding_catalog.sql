-- Fix encoding corruption from bad dump (literal ?? placeholders).
-- Source of truth: framework_definitions.py + migrations 017/018/023.

BEGIN;

-- Dimensões (framework LeAction)
UPDATE public.leaf_dime SET name_dime = 'Visão Compartilhada (SV)' WHERE id_dime = 1;
UPDATE public.leaf_dime SET name_dime = 'Coração e Conexão (HC)' WHERE id_dime = 2;
UPDATE public.leaf_dime SET name_dime = 'Estrutura Fluida (FS)' WHERE id_dime = 3;
UPDATE public.leaf_dime SET name_dime = 'Aprendizagem em Ação (LA)' WHERE id_dime = 4;
UPDATE public.leaf_dime SET name_dime = 'Arquitetura Digital (DA)' WHERE id_dime = 5;

-- Domínios
UPDATE public.leaf_doma SET name_doma = 'Estratégia Digital (ds)' WHERE id_doma = 1;
UPDATE public.leaf_doma SET name_doma = 'Modelo de Negócio Digital (bm)' WHERE id_doma = 2;
UPDATE public.leaf_doma SET name_doma = 'Cultura de Inovação (ic)' WHERE id_doma = 3;
UPDATE public.leaf_doma SET name_doma = 'Cultura de Dados (dc)' WHERE id_doma = 4;
UPDATE public.leaf_doma SET name_doma = 'Cultura de Colaboração (cc)' WHERE id_doma = 5;
UPDATE public.leaf_doma SET name_doma = 'Governança Digital (dg)' WHERE id_doma = 6;
UPDATE public.leaf_doma SET name_doma = 'Plataformas Digitais (dp)' WHERE id_doma = 7;
UPDATE public.leaf_doma SET name_doma = 'Capacidades Digitais (dc)' WHERE id_doma = 8;
UPDATE public.leaf_doma SET name_doma = 'Métricas Digitais (dm)' WHERE id_doma = 9;

-- Planos CRM / vitrine
UPDATE public.dx_planos SET
  nome = 'Conta Básica',
  descricao_beneficios = '["Diagnóstico de maturidade digital","Gestão de squads e OKRs","Suporte por e-mail"]'::jsonb
WHERE id = 1;

UPDATE public.dx_planos SET
  nome = 'Conta Premium',
  descricao_beneficios = '["Tudo da Conta Avançada","Cockpit executivo completo","eSIM e telemetria integrada","CSM dedicado","Renovação prioritária"]'::jsonb
WHERE id = 2;

UPDATE public.dx_planos SET
  nome = 'Conta Avançada',
  descricao_beneficios = '["Tudo da Conta Básica","Inteligência de negócio avançada","Múltiplas squads ativas","Consultoria mensal"]'::jsonb
WHERE id = 3;

UPDATE public.dx_planos SET
  nome = 'Pacote Extra: 5 Usuários',
  descricao_beneficios = '["+5 usuários ativos no seu plano","Sem troca de plano base","Ativação imediata após pagamento"]'::jsonb
WHERE id = 4;

-- Cliente demo
UPDATE public.ctdi_clie SET nome_clie = 'Colégio Demo Maria' WHERE id_clie = 4;

COMMIT;
