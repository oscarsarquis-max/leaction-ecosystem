# SEGSENSE_FUN_005 — Jornada contexto real, intenção e possibilidades

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_FUN_005 |
| Versão | 1.1 |
| Data | 15/09/2026 |
| Prompt | SEGSENSE_PRM_020_COR_001 |

## Ações distintas (não reutilizar o mesmo botão)

1. **Obter conteúdo da URL** — só captura server-side.
2. **Revisar contexto extraído** — título, domínio, URL final, horário UTC, texto principal (sem chrome), cartões com origem, trecho e remover/corrigir.
3. **Confirmar este contexto** — só envia chaves mantidas; correção = `USER_DECLARED`; original = `URL_EXTRACTED` no snapshot. Remover um cartão não apaga o snapshot.
4. **Informar intenção** — campo livre, independente do link.
5. **Ver possibilidades para este contexto** — BFF só com contexto confirmado e intenção suficiente.

Carregamento honesto. Sem timer falso. Entrada preservada se a etapa falhar.

## Distinções visuais

| Camada | O que a pessoa vê |
|---|---|
| Texto da fonte | Conteúdo principal extraído, inerte, sem menus/sumário |
| Extraído da página | Tema/evento/cultura/região/período só com relação local (mesmo parágrafo) e trecho visível |
| Declarado/corrigido pela pessoa | Correções ou acréscimos `USER_DECLARED`; não reescrevem o snapshot |
| Intenção | Frase da pessoa, não inferida da URL |
| Decisão da Spider | Status e capability desta execução |
| Possibilidade do provider | Itens devolvidos pelo mock nesta execução |
| Perguntas agrícolas | Cultura, região, período e situação quando não comprovados |

Não se afirma que a pessoa é produtora, proprietária, está na região ou sofreu a perda.

## Linguagem pública obrigatória

| Estado | Mensagem (sentido) | Próximo passo |
|---|---|---|
| URL pronta | Informe um endereço público e obtenha o conteúdo. | Obter conteúdo |
| Captura em andamento | Obtendo a página indicada. | Esperar o resultado |
| Aguardando revisão | Conteúdo obtido. Confira o trecho e os elementos. | Confirmar ou corrigir |
| Confirmado | Este contexto foi confirmado para esta tentativa. | Informar intenção |
| URL inválida / protocolo | Este endereço não pode ser usado. Use http ou https público, sem credencial na URL. | Corrigir o endereço |
| Host privado / metadata | Este endereço não é uma página pública utilizável nesta demonstração. | Usar URL pública |
| Timeout | A página não respondeu a tempo. | Tentar de novo ou outra URL |
| Redirect inseguro | O redirecionamento desta página não é seguro para captura. | Outra URL |
| HTTP 4xx/5xx | A página não devolveu conteúdo utilizável. | Verificar o endereço |
| MIME | Este tipo de arquivo não é lido nesta demonstração (apenas página em texto). | Outra URL |
| Excesso de tamanho | A resposta ultrapassou o limite desta demonstração. | Outra página menor |
| Sem texto principal / só chrome ou JavaScript | Não foi possível isolar o texto principal. Cole um trecho ou informe outro endereço. | Colar trecho ou outra URL |
| Intenção ausente | Diga o que você deseja fazer com este contexto. | Preencher intenção |
| Contexto insuficiente | Faltam dados específicos (perguntas nomeadas). | Completar |
| Nenhuma capability | Não há possibilidade disponível neste ambiente demonstrativo. | Encerrar ou outro contexto |
| Provider indisponível | O simulador demonstrativo não respondeu nesta tentativa. | Tentar de novo |
| Possibilidades | Caminhos devolvidos pelo provedor demonstrativo (não são produto). | Revisar limites |
| Nova tentativa | A tentativa anterior foi descartada. | Recomeçar |

## Independência residencial × agrícola

- Cotação residencial do PRM_019 permanece; prêmio só com `GENERATE_SYNTHETIC_HOME_QUOTE` + mock COMPLETED.
- Quebra de safra **nunca** usa o simulador residencial e **não** mostra R$.
- Exemplos governados (incêndios, família, renda) continuam nomeados e separados da URL pública.
