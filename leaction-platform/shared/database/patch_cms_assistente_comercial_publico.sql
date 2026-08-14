-- CMS Assistente Chat — destino comercial público (/comeco)
-- Banco: leaction_hub
-- Adiciona sistema_destino=comercial_publico (árvore pré-venda, distinta da Nina).

ALTER TABLE cms_assistente_chat
  DROP CONSTRAINT IF EXISTS chk_cms_assistente_chat_destino;

ALTER TABLE cms_assistente_chat
  ADD CONSTRAINT chk_cms_assistente_chat_destino CHECK (
    sistema_destino IN (
      'hub-publico',
      'actionhub',
      'inove4us',
      'paneldx',
      'todos',
      'comercial_publico'
    )
  );
