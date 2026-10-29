# Gigio — inspiração e atendimento

Assistente virtual com IA da Loja de Pães. Identidade: **Gigio**. Estabelecimento: **A Loja**.

## Integração

- Adaptador isolado no backend da Loja (`app/domain/gigio`). Não altera o Panne nem o Chamelleon.
- Amazon Bedrock Runtime, operação `invoke_model` (Anthropic Messages, `bedrock-2023-05-31`), inference profile `us.anthropic.claude-sonnet-4-6` em `us-east-1`. O perfil anterior, Claude Sonnet 4 `20250514`, deixou de existir em 14/10/2026. Sem streaming e sem `bedrock-mantle`.
- Credenciais só no servidor (cadeia AWS / `LOJADEPAES_AWS_*` / `AWS_*`). Nada no React, logs ou Git. Não copiar chave do Chamelleon para arquivo rastreado.
- Flag: `LOJADEPAES_GIGIO_ENABLED` (padrão `false`). Gateway: `LOJADEPAES_GIGIO_GATEWAY=fake|bedrock`.
- Falha do Gigio não derruba vitrine, checkout nem admin.

## Fontes de leitura

Catálogo publicado, receitas editoriais, calendário, fidelidade vigente, Criador (preço/peso/opções) e explicações aprovadas (`gigio_editorial_notes`). Pedido só com `X-Order-Token` da sessão protegida. Sem token no modelo. Sem CPF/endereço/pagamento no prompt.

## Retenção

A conversa fica só na sessão do navegador. Não há persistência de transcript no servidor. Logs: IDs implícitos, latência, erros e uso agregado — sem o texto da pergunta.

## Admin

`/admin/produtos/gigio` — rascunho vs publicada. Não muda opções nem preços do Criador.
