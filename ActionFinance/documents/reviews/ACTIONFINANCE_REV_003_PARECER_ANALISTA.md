# ACTIONFINANCE_REV_003 — Parecer funcional, UX e dados

Data: 28/09/2026. **Resultado: entrega parcial; aceite pendente de correções do PRM_003.** Sem PRM_004.

Cópia integral do parecer do analista. Não é um novo prompt de ciclo nem autorização de produção. O recorte permanece o PRM_003; as correções R1–R6 são responsabilidade do Cursor neste mesmo ciclo.

## Alcance da revisão

Leitura do relatório Cursor, migrations V2, serviços de títulos/cadastros, repositório de títulos, App.tsx, api.ts, session.ts, teste de UI e relatórios XML locais. Inspeção visual das capturas desktop de recebíveis e mobile de contas a pagar entregues. Não executei operações no runtime, não li tokens e não modifiquei o produto. Os problemas de lógica abaixo foram identificados estaticamente; não são apresentados como testes de navegador executados pelo analista.

Os XML presentes em backend/target registram 7 unitários e 21 ITs, todos sem falhas/erros/skips. São evidência de que os testes existentes passaram, não de cobertura integral do prompt. O relatório afirma execução completa; não localizei pacote imutável específico de evidências do PRM_003 na pasta documental consultada.

## O que está aproveitável

- Modelo com tenant distinto de company, contrapartes/categorias por empresa, título compartilhado com direção e histórico separado.
- Migrations com chaves estrangeiras compostas de isolamento, dinheiro numeric(19,0), estados e restrições de completude, índices e sem seed operacional embutido.
- Casos de uso locais para ambas as direções, sem dependência de conectores.
- Concorrência de versão, locks de cadastros e idempotência persistida já possuem implementação e testes parciais.
- Desktop tem a hierarquia principal proposta. A operação permanece demonstrativa; nenhuma movimentação financeira ou integração foi entregue ou exigida.

## Correções prioritárias

### R1 — Identidade da operação idempotente incompleta

**Prioridade alta.** Em TitleService.java:152–153, a correção calcula hash de operação/direção/comando, sem o ID do título. O escopo da operação também não inclui o ID. Assim, repetir a mesma chave e corpo para outro título da mesma direção/empresa pode devolver o primeiro título como sucesso, sem corrigir o segundo nem rejeitar o pedido diferente.

Além disso, withIdempotency, linha 389, consulta o estado atual do título no replay; não devolve o resultado original armazenado. O registro guarda apenas o ID e status 200. Depois de outra alteração, a mesma operação pode retornar resposta diferente.

Correção requerida: fingerprint incluindo alvo e semântica completa; resultado de sucesso estável, com autorização antes do replay. Testes: mesma chave/corpo em alvo diferente produz 409; repetição legítima não duplica evento; alteração posterior não muda a resposta original da operação repetida. Conferir também criação/confirmar/cancelar.

### R2 — Registrar rascunho em edição não confirma

**Prioridade alta.** Em App.tsx, TitleFormPage.submit, quando há id a chamada é sempre PATCH; o parâmetro register só afeta a criação POST. O botão Registrar de um rascunho em edição chama submit(true), mas TitleService.update preserva DRAFT. A interface promete uma transição que não executa.

Correção requerida: salvar alterações e confirmar com comportamento explícito e seguro. Pode usar operação atômica dedicada ou sequência que trate falha parcial sem anunciar registro concluído. Verificar também acesso direto à edição de CANCELLED, que hoje cai nos botões de rascunho no formulário, embora o backend recuse a alteração.

Prova: criar rascunho incompleto, abrir edição, completar campos e Registrar; título termina OPEN, histórico é coerente e nenhuma escrita parcial é tratada como confirmação completa.

### R3 — Falha de rede e sessão não têm recuperação consistente

**Prioridade alta.** Formulário mantém uma chave única, mas recria o payload dos campos a cada tentativa: após timeout o usuário pode mudar dados e reenviar a mesma chave, sem recuperar primeiro o resultado desconhecido. Confirmar/cancelar geram nova chave a cada clique e não bloqueiam duplo envio. Cadastros não possuem tratamento consistente de erros nas promessas de edição/inativação.

Em api.ts, 401 chama setSession(null) no módulo session.ts, mas essa função não notifica o estado React de App. A interface pode permanecer mostrando dados protegidos e o contexto anterior após a sessão ser invalidada. A verificação de geração ocorre antes de aguardar o corpo da resposta; falta proteção após essa espera.

Correção requerida: sessão reativa, limpeza imediata de dados em 401/saída, invalidação de respostas antigas até a aplicação final no estado; operação pendente com chave/payload/rota fixos enquanto o resultado for desconhecido; novo pedido somente após resolução explícita. Desabilitar envio concorrente e apresentar erros recuperáveis em todas as ações. Testar resposta atrasada após troca de empresa e logout, timeout após commit e repetição.

### R4 — Mobile entregue não atende à especificação

**Prioridade alta de UX.** A captura mobile-360-payables.png mostra tabela e cartões simultaneamente, conteúdo cortado à direita, cartões de resumo fora da largura e cabeçalho/menu truncados. Isso é evidência visual da entrega, não apenas ausência de testes. A presença de media queries no CSS não comprova que o resultado exibido está correto.

Correção requerida: tabela só no desktop; cartões só no mobile; cabeçalho/menu, filtros, resumo e ações dentro de 360 px; sem esconder dados por overflow para simular sucesso. Refazer capturas de lista, formulário, detalhe, cadastros e cancelamento. Medir largura real da página no navegador. Se a captura foi produzida antes do CSS final, comprovar o resultado atual com novas evidências.

### R5 — Fluxos de UX incompletos

**Prioridade média.** A navegação lateral chama navigate diretamente e ignora a proteção de formulário alterado. Voltar do navegador também não verifica alterações. Diálogos usam dialog open, sem implementação identificada de modalidade/foco contido; cadastros rápidos não têm o comportamento de diálogo especificado. Conflito de versão exibe instrução de recarregar, mas não oferece recuperação guiada.

Datas aparecem em formato ISO nas listas/detalhes. humanChanges mostra centavos e códigos de estado sem converter para moeda/rótulos em português. Referências UUID inteiras dominam a tabela e quebram linhas de valores. Falha ao obter histórico é convertida em histórico vazio. Filtro de categoria e busca nos seletores requeridos não estão presentes na interface lida.

Correção requerida: concluir os comportamentos já especificados, sem redesign do produto. Garantir saída protegida, diálogos acessíveis, recuperação de conflito, data brasileira, dinheiro legível no histórico, referência compacta com acesso ao valor completo, filtro de categoria e seleção pesquisável. Erro de histórico deve aparecer como erro com tentativa novamente.

### R6 — Lista e resumo podem representar instantes diferentes

**Prioridade média.** TitleService.list não declara transação consistente; JdbcTitleRepository.list faz consultas distintas de count, itens e resumo. Sob alteração concorrente, uma única resposta pode combinar contagem/lista/totais de momentos distintos, contrariando o snapshot especificado.

Correção requerida: mesma fotografia transacional (isolamento adequado) ou consulta equivalente consistente para a resposta inteira. Manter cálculo exato de centavos e escopo tenant/company. Acrescentar prova de concorrência controlada, além do teste estático de soma por filtro.

## Evidências e pendências locais

Os cinco testes Vitest relatados não cobrem o percurso funcional pedido: App.test.tsx contém teste de entrada de token, não testes completos de cadastro, confirmação, correção, cancelamento e recuperação. Completar provas de navegador dessas jornadas e dos casos R1–R6. Capturas de listas não substituem a execução desses fluxos.

O relatório especifica npm audit --omit=dev, embora a síntese mencione audit 0. Registrar auditoria completa e de runtime separadamente; não inferir situação de dependências de desenvolvimento a partir da auditoria restrita.

O ensaio start/stop continua sem conclusão integral por resíduo da própria execução sem metadado. Preservar a recusa segura e resolver a perda dos metadados/filhos do lançamento; não restaurar adoção por porta ou encerramento global. É uma pendência operacional já existente, secundária às correções funcionais acima.

Datas demonstrativas fixadas em 15/09 não comprovam os casos relativos a hoje. Manter seed estável após criação, mas usar data de negócio na carga explícita ou casos de teste com Clock fixo para ontem/hoje/amanhã, registrando a distinção.

## Deliberação

O trabalho já implementa parte substancial do domínio financeiro; não será reiniciado nem substituído por mais fundação. O PRM_003 fica **parcialmente entregue e ainda não aprovado**, pelas falhas funcionais e de UX descritas. Corrigir este recorte antes de ampliar o produto. Não emitir PRM_004 nesta revisão.

Este documento é o parecer do analista, não um novo prompt de implementação ou autorização de produção. O código permanece sob responsabilidade do Cursor. ActionFinance continua produto autônomo/integrável; ActionHub e Panne são origens do primeiro cenário, sem mudança dessas fronteiras.
