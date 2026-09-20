# SEGSENSE_PRM_020_COR_001 — Correção única da fidelidade semântica da URL real

## Controle

- Projeto: SegSense. Versão 1.0. Data: 15/09/2026.
- Corretivo único de `SEGSENSE_PRM_020`. Não emitir segundo corretivo e não iniciar `SEGSENSE_PRM_021`.
- A auditoria confirmou no navegador que a captura HTTP da URL pública é real e produz estado visível. Contudo, o PRM_020 **não está aprovado**: o extrator associou elementos distantes e não relacionados ao evento, produzindo contexto estruturado sem sustentação semântica suficiente.
- Alterações apenas em `segsense/`, `spider/` e `segsense-provider-mock/` se indispensáveis. Não tocar Experience Hub, Panne ou outros produtos. Sem commit, push ou deploy.

## Evidência do desvio

Na URL real `https://pt.wikipedia.org/wiki/Agricultura_no_Brasil`, capturada em 15/09/2026, a interface mostrou:

- `Tema: quebra de safra` e `Evento: quebra de safra`, sustentados por trecho que contém a expressão;
- `Cultura: milho`, sustentada apenas por ocorrência no índice/listagem de culturas;
- `Região: Rio Grande do Sul`, sustentada por trecho histórico sobre a criação de um curso em Pelotas.

As duas últimas ocorrências não demonstram que aquela quebra de safra envolveu milho ou ocorreu no Rio Grande do Sul. A extração por presença global de palavras transformou coincidências distantes em relação factual. Isso viola o requisito central: **nenhum elemento pode ser apresentado como contexto se a fonte não sustentar a relação**.

Além disso, o “Texto da fonte” começou com navegação, menu, login e sumário da Wikipédia. A captura é verdadeira, mas a seleção de conteúdo principal ainda é inadequada para revisão humana.

## Prompt para o Cursor

Leia integralmente `SEGSENSE_PRM_020`, `SEGSENSE_URL_001`, `SEGSENSE_SEC_005`, `SEGSENSE_FUN_005`, `SEGSENSE_DAT_007`, `SEGSENSE_REV_020`, o snapshot real auditado e o código do extrator. Preserve captura server-side, SSRF, hashes, provenance 1.2, contratos anteriores, capability agrícola e separação SegSense → Spider → mock.

### 1. Corrigir extração de conteúdo principal

Separe claramente:

1. bytes recebidos e hash do documento integral;
2. conteúdo principal extraído e hash do texto normalizado;
3. trechos de evidência usados para elementos estruturados.

Para HTML, remova da seleção principal navegação, cabeçalhos globais, rodapés, login, busca, sumário/índice, scripts, estilos, formulários, elementos ocultos e conteúdo repetitivo. Use seleção determinística e versionada baseada em elementos semânticos (`main`, `article` e equivalentes) com fallback documentado. Não execute JavaScript remoto.

Se não for possível isolar conteúdo principal com confiança mínima, retorne `NO_MEANINGFUL_TEXT` ou peça que a pessoa cole um trecho — não use toda a página indiscriminadamente. O snapshot dos bytes continua preservado para auditoria, mas a UI deve revisar texto principal legível, não chrome do site.

### 2. Exigir relação semântica local para cada elemento

Não extraia cultura, região, período, causa, consequência ou sujeito por ocorrência em qualquer ponto do documento. Um elemento só pode ser proposto quando:

- aparece na mesma sentença, parágrafo ou janela textual curta e documentada do evento/tema ao qual está sendo associado; e
- o trecho exibido sustenta a relação, não apenas a presença das duas palavras; e
- o extrator registra regra, posição/offset e trecho exato de evidência.

Não use heurística que una termos encontrados em seções distintas. Não transforme índice, legenda, lista geral, referência bibliográfica ou exemplo histórico distante em atributo do evento atual. Em caso de dúvida, **omita o elemento e pergunte à pessoa**.

Para a página auditada, o resultado aceitável é manter apenas `quebra de safra` como tema/evento se o trecho local realmente o sustentar. `milho` e `Rio Grande do Sul` devem ser omitidos, salvo se uma evidência local diferente comprovar explicitamente a associação — o que precisa aparecer na UI e no teste.

Cada cartão de elemento deve mostrar:

- valor proposto;
- origem `Extraído da página` ou `Declarado/corrigido pela pessoa`;
- trecho curto que sustenta aquele valor;
- ação para remover/corrigir antes da confirmação.

A confirmação humana não transforma uma inferência automática falsa em fato da fonte. Correção do usuário é contribuição separada `USER_DECLARED`, preservando o snapshot e a proposta original rejeitada/removida.

### 3. Impedir decisão com atributos não sustentados

O BFF só pode materializar e enviar à Spider elementos confirmados e sustentados por evidência ou declarados explicitamente pela pessoa. Inclua validação server-side: elemento `URL_EXTRACTED` exige referência válida ao snapshot, versão do extrator, offsets/trecho e estado confirmado. Não confie apenas no estado do frontend.

A Spider e o provider não devem receber `crop=milho` ou `region=Rio Grande do Sul` no caso auditado. Prove os payloads sanitizados. A capability agrícola pode ser escolhida com o tema de quebra de safra e a intenção compatível; ela deve retornar possibilidades gerais e perguntas sobre cultura, região, período e situação quando esses dados não estiverem comprovados.

Não altere o provider para fazer parecer que recebeu menos dados: a correção deve ocorrer na extração, confirmação e materialização do contexto.

### 4. Testes de fidelidade obrigatórios

Adicione corpus controlado com HTML contendo:

- evento e cultura na mesma sentença: associação permitida;
- evento em um parágrafo e cultura somente no índice: cultura omitida;
- evento em uma seção e região em história institucional distante: região omitida;
- múltiplos eventos/culturas sem relação inequívoca: resultado ambíguo ou perguntas, nunca combinação cartesiana;
- texto em `nav`, `aside`, sumário, rodapé e conteúdo oculto: excluído do conteúdo principal;
- página sem `main/article`, com fallback válido;
- página sem conteúdo principal confiável: falha honesta;
- HTML hostil e conteúdo excessivo: continuam seguros e limitados.

Os testes devem verificar não apenas palavras presentes, mas relações e payload final enviado. Inclua regressão específica da captura auditada sem versionar a página integral: fixture mínima representativa e hashes claramente identificados como fixture de teste, nunca como prova da URL pública real.

### 5. Repetir a prova real

Na stack isolada, capture novamente a URL pública real e mostre:

1. conteúdo principal sem menus/sumário;
2. `quebra de safra` com trecho de evidência real;
3. ausência de `milho` e `Rio Grande do Sul` como atributos associados, caso não haja evidência local;
4. possibilidade de remover/corrigir cada elemento antes da confirmação;
5. intenção livre preservada;
6. payload enviado à Spider sem atributos espúrios;
7. capability agrícola escolhida e resposta real do mock, sem R$;
8. perguntas explícitas para informações agrícolas ainda desconhecidas;
9. nenhuma substituição por fonte governada ou cartão hardcoded.

Valide visualmente 1440×900, 768×1024, 390×844, 320×568, zoom 200%, teclado/foco e impressão. Não autorize microfone. Guarde evidências em `documents/evidencias/SEGSENSE_PRM_020_COR_001/` sem copiar o artigo integral ou dados pessoais.

### 6. Fechar os gates que ficaram pendentes

Execute:

- frontend: `npm ci`, lint, todos os testes e build;
- SegSense backend: `mvnw verify` completo com ambiente de testes limpo;
- Spider: suíte ampla pertinente ao Satellite Contract 1.0/1.1/1.2, decisão, capability e provider dispatch;
- mock: todos os testes;
- Flyway: validate, V1–V17 em banco vazio e confirmação de V17 no volume isolado existente;
- preflight, ACL/segredos, logs e prova de independência das aplicações.

Não esconda a primeira falha: diferencie defeito de código, contaminação de ambiente e instabilidade externa. A prova pública pode variar com a página; o corpus controlado deve garantir a regra sem depender da internet.

### 7. Documentação e devolutiva

Crie `SEGSENSE_PRM_020_COR_001.md` como cópia integral. Atualize `SEGSENSE_REV_020` para v1.1, `SEGSENSE_URL_001`, `SEGSENSE_FUN_005`, `SEGSENSE_DAT_007`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_DEMO_RUN_001`, `SEGSENSE_PLN_001` e índices.

Na devolutiva, comece com uma comparação visual e factual:

- antes: milho e Rio Grande do Sul associados por ocorrências distantes;
- depois: somente elementos sustentados localmente, com perguntas para o que continua desconhecido.

Apresente depois conteúdo principal, evidências/offsets, payload real para a Spider, retorno do mock, matriz do corpus, SSRF preservado, gates completos, migrations, stacks e Git. Identifique separadamente qualquer sujeira alheia do Experience Hub.

**Pare para auditoria. Não autoaprove e não inicie `SEGSENSE_PRM_021`.** Não faça commit ou push.
