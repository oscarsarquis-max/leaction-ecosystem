# Gigio — referência lida na Loja

Leitura de `C:\Projetos\lojadepaes`, em 06/11/2026. Nenhum arquivo da Loja foi alterado. A Gestão copia o desenho e o avatar. O código da sugestão é da Gestão.

## Modelo e região

O Gigio da Loja obtém o modelo e a região nesta ordem, em `backend/app/domain/gigio/settings.py`:

| O quê | Nome no objeto `Settings` | Variável de ambiente | Se os dois estiverem vazios |
|---|---|---|---|
| Região | `bedrock_region` | `BEDROCK_REGION` | constante `CHAMELLEON_BEDROCK_REGION` |
| Modelo | `bedrock_model_id` | `BEDROCK_MODEL_ID` | constante `CHAMELLEON_BEDROCK_MODEL_ID` |

Também entram, sem valor neste documento: `bedrock_max_tokens` / `BEDROCK_MAX_TOKENS`, `bedrock_temperature` / `BEDROCK_TEMPERATURE`, `bedrock_guardrail_id` / `BEDROCK_GUARDRAIL_ID`, `bedrock_guardrail_version` / `BEDROCK_GUARDRAIL_VERSION`, `BEDROCK_SSL_VERIFY`.

A credencial da chamada fica em `aws_access_key_id` / `AWS_ACCESS_KEY_ID` e `aws_secret_access_key` / `AWS_SECRET_ACCESS_KEY`. A Gestão não lê esses valores. A credencial da Gestão é outra, do usuário IAM `gestao-gigio`, em `/etc/gestao/gigio.env`.

A chamada é `bedrock-runtime` `invoke_model`, contrato Anthropic (`bedrock-2023-05-31`). O endpoint com `bedrock-mantle` é recusado.

Na Gestão os nomes são `GESTAO_GIGIO_BEDROCK_REGION`, `GESTAO_GIGIO_BEDROCK_MODEL_ID`, `GESTAO_GIGIO_AWS_ACCESS_KEY_ID` e `GESTAO_GIGIO_AWS_SECRET_ACCESS_KEY`. Sem essas variáveis, e sem `GESTAO_GIGIO_GATEWAY=fake`, o botão fica desligado.

## Persona

O texto versionado está em `rules.py` (`PROCESS_RULES`, versão `PROCESS_RULES_VERSION`). O tom é português brasileiro, curto, acolhedor e prático. O Gigio se apresenta como assistente virtual, não como pessoa da equipe.

O que ele não faz, nesse texto: prometer saúde, glúten, lactose ou digestão; inventar preço, estoque, prazo ou produto; criar, cancelar ou aceitar pedido; publicar conteúdo; alterar receita; pedir cartão ou senha. Ideia dele é sugestão. Receita publicada da casa é outra coisa e precisa de fonte.

Na Gestão a persona é a do padeiro, não a do cliente da vitrine: % do padeiro, linhas fixas e massa-base intocadas, faixa quando a inclusão é incerta, padrão da casa no motivo, e a decisão fica com o padeiro.

## Ferramenta e saída

`gateway.py` define `GigioGateway.complete`. O pedido leva o texto de sistema, as mensagens e as ferramentas. A resposta traz texto, `tool_use`, motivo de parada, tokens e latência.

`tools.py` declara as ferramentas de leitura (`lookup_products`, `lookup_recipes`, `lookup_editorial`, `lookup_builder`, `propose_builder`, `lookup_accompaniments`, `lookup_pairing_references`, `lookup_order`, `lookup_schedule`, `lookup_fidelity`). Cada uma tem nome, descrição e `inputSchema`. O modelo não escreve a chamada no texto: a Loja descarta XML e JSON de ferramenta vazados (`hygiene.py`).

Na Gestão há uma ferramenta só, `sugerir_receita`, com linhas, rendimento, perda, modo de fazer e observações. O Bedrock recebe `tool_choice` apontando para ela.

## Limites, higiene e o falso

`policy.py`: mensagem até 2.000 caracteres, histórico de 12, 3 rodadas de ferramenta, saída até 4.000 caracteres. Marcadores de injeção são recusados ou limpos.

`rate_limit.py`: 20 conversas por minuto por origem e 4 em andamento. A Gestão usa outro limite: 30 sugestões por dia por organização, e 30 segundos de espera.

`fake.py`: `FakeGigioGateway` grava os pedidos e devolve um roteiro, ou uma resposta pronta, sem rede. A Gestão tem `FakeGateway` para os testes e para `GESTAO_GIGIO_GATEWAY=fake`.

## Avatar

Arquivo: `frontend/images/logos/avatar_gigio.png`.

Na loja pública (`GigioHost.tsx`) a imagem entra no topo do painel com 48 px e no botão de conversa com 56 px. Na Gestão o botão "Sugerir com o Gigio" usa 20 px e o painel usa 48 px. O arquivo copiado tem o mesmo SHA-256 do original: `c9c87b87dcb16a6ed90cfbe381e257af8ca6c92fa29c01c7cd5584f2b2a89c8b`.
