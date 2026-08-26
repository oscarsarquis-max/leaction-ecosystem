# Modelo de dados 0020

Migração reversível `0020_inventory_procurement`. UUID, `timestamptz`, `numeric`, FKs compostas por organização, RLS ENABLE+FORCE, exclusão física bloqueada.

Tabelas: política e versão; local; item; lote; movimento; saldo projetado; reserva e alocação; separação e linhas; postagem de consumo; sessão/escopo/contagem/revisão de inventário; sugestão de reposição; requisição; cotação; pedido, revisão e itens; recebimento; devolução; comando; contador de códigos.

Saldo projetado é cache reconstruível a partir do ledger. Nunca é fonte histórica.
