# SEGSENSE_PRM_015 — Painel de evidências da jornada sintética

## Controle

- Projeto: SegSense. Versão 1.0. Data: 14/09/2026.
- Etapa anterior: `SEGSENSE_PRM_014` encerrado **aprovado com ressalvas** após o único corretivo `SEGSENSE_PRM_014_COR_001`. Não há segundo corretivo do PRM_014.
- Execução: Cursor, no monorepo `leaction-ecosystem`. SegSense, Spider e Insurance Provider Mock permanecem aplicações independentes. Não modificar Panne ou outros produtos. Sem commit, push ou deploy.
- Toda documentação **nova originada deste prompt** deve ter identificador `SEGSENSE_`. Preserve os identificadores preexistentes dos documentos Spider e do Satellite Contract V1.
- Este prompt contém primeiro as **correções herdadas da etapa anterior**; só depois inicia seu novo escopo. Não inicie PRM_016.

## Prompt para o Cursor

Implemente o PRM_015 de forma verificável e restrita ao MVP local sintético. A regra central do patrocinador continua: **só pode aparecer como fato da jornada o que efetivamente ocorreu no sistema e possui evidência.** Uma explicação de arquitetura, uma intenção de clique, um request pendente, um log isolado e um Test Double não autorizam afirmar execução de etapas que o contrato não comprova. Não converta a demonstração em proposta comercial, cotação, produto Icatu ou piloto de produção.

Antes de editar, leia integralmente `SEGSENSE_PRM_014`, `SEGSENSE_PRM_014_COR_001`, `SEGSENSE_REV_014`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_SAT_V1_ADERENCIA_001`, `SEGSENSE_DEMO_RUN_001`, `SEGSENSE_PLN_001`, `SPIDER-SATELLITE-CONTRACT-V1`/`SPIDER-SAT-003` e os schemas V1 pertinentes. Inspecione o código e o working tree; preserve toda alteração alheia já presente. Registre quais campos são realmente retornados/persistidos hoje. Não preencha lacunas do contrato por suposição.

## 1. Correções herdadas da etapa anterior — obrigatórias antes do novo escopo

### 1.1 Prova de provedor indisponível e segurança operacional

O `prove-mvp-http.ps1` relatou `mockDownStatus=READY`: o primeiro `mock=` de `.mvp-logs/pids.txt` estava obsoleto, e o processo real em `:8095` permaneceu ativo. A rotina atual que usa `Stop-Process` com base apenas nesse PID é **insegura**: um PID reciclado pode pertencer a processo alheio. Até corrigir, o roteiro da reunião não deve instruir ninguém a executar esse script.

Repare a prova de indisponibilidade sem encerrar processos identificados somente por `pids.txt`. Preferência: teste negativo numa **stack isolada e controlada**, com porta/provedor inacessível ou falha controlada, sem afetar os três processos da reunião. Se optar por encerramento de processo próprio, exija antes verificação inequívoca de PID, porta, executável, linha de comando, início do processo e marcador de propriedade desta execução; diante de qualquer ambiguidade, **falhe sem matar nada**. Nunca encerre processo preexistente ou de outro produto, nem derrube a stack em uso para fabricar a prova. Mantenha a operação em PowerShell, com caminhos absolutos e alvo validado. Teste explicitamente o caso de PID obsoleto/reciclado e comprove que o processo alheio permanece intacto.

A prova HTTP deve demonstrar duas coisas separadas: (a) o provedor estava **de fato indisponível** para a Spider daquela execução; (b) a interação canônica respondeu `PROVIDER_UNAVAILABLE`, sem `providerReference`, sem itens e sem pré-proposta. Se a prova ao vivo não for viável neste ambiente, não simule sucesso: registre `NÃO COMPROVADO`, mantenha o teste automatizado correspondente e explique o limite. Atualize `SEGSENSE_DEMO_RUN_001` e demais instruções operacionais para só chamar o script depois da correção e da validação.

### 1.2 Aceite visual ainda aberto

Execute, se houver browser interativo, a jornada real em 1440×900, 768×1024, 390×844, 320×568, zoom 200%, teclado/foco e impressão. Confira a copy corrigida do PRM_014, estados pendente/erro/sucesso e watermark. Registre capturas ou observações específicas; testes DOM, HTTP e compilação **não** substituem inspeção visual. Se o browser não estiver disponível, declare cada dimensão como não verificada e deixe um roteiro reproduzível; não afirme aceite visual.

## 2. Novo escopo — painel operacional de evidências, não uma jornada inventada

O plano anterior descrevia uma visão completa de origem, contexto, consentimento, intent, policy, plano, capabilities, resolução, execução e resultado. **Recorte esta etapa ao que o Satellite Contract V1 `local-demo` efetivamente expõe e o SegSense possui como evidência.** Intent Contract pleno, CTX-004, Eligibility Gate, plano/execução do Data Plane, callback, IdP, seguradora autorizada e cotação vinculante não existem nesta fatia. Não desenhe essas etapas como cumpridas nem crie `planId`, `executionId` ou timestamps sintéticos. Registre o recorte e a razão em `SEGSENSE_OPS_001.md` e atualize `SEGSENSE_PLN_001` sem apagar a ambição futura nem reescrever o histórico.

Crie uma visão **utilizável na reunião** dentro da experiência pública já existente em `/demonstracao/mvp-integrado`, como painel de “Evidências desta simulação”. Ela deve aparecer após a resposta real e ser compreensível antes dos detalhes técnicos. Não dependa do admin protegido por IdP ausente. Não abra endpoint público para consultar arbitrariamente decisões ou identificadores. O painel deve ser somente da interação corrente, alimentado pela projeção persistida e validada do BFF/resposta canônica; não leia logs diretamente do browser. Se for necessário consultar algo, use apenas contrato/API já autorizado e justifique a segurança. Não altere schema, rota ou semântica do Satellite Contract V1 para adequar a UI. Não modifique o mock sem necessidade demonstrada.

Apresente apenas fatos cuja fonte e condição estejam documentadas, por exemplo:

| Fato possível | Condição mínima de exibição |
|---|---|
| Origem/contexto sintético governado | Snapshot/versionamento realmente associado à interação; nunca alegar verificação da vida real do visitante. |
| Objetivo enviado | Valor efetivamente recebido/registrado pelo BFF; antes da resposta, descrever somente envio/espera do cliente. |
| Decisão da Spider | `decisionId` e status canônico presentes; redação da `explanation` ecoada sem substituição local. |
| Capability despachada | Evidência canônica de `capabilityId` e `providerRequestId`; ausente em `REJECTED`. |
| Retorno do Test Double | `providerReference` e `resultSummary` confirmados; nomear Test Double e itens ilustrativos, sem sugerir catálogo ou disponibilidade. |
| Correlação | IDs reais, em detalhes técnicos recolhidos, sem segredos. |

Uma ordem visual de cartões **não é** uma cronologia auditável. Só exiba data/hora de uma etapa se o timestamp dessa etapa vier de fonte real e for distinguível de horário local de renderização ou de recebimento HTTP. Não derive “Spider recebeu às...” do início do `fetch`; não infira conclusão de subetapas a partir de `READY` além do que o contrato assegura. Na ausência de evento intermediário, prefira “resultado confirmado na resposta” a uma linha do tempo com pontos animados. Para recursos futuros, use uma nota separada “Fora desta demonstração”, não estados visuais de jornada concluída. Quando Spider/mock falhar, o painel não deve conservar cartões ou itens de uma tentativa anterior como se fossem resultado da atual; diferencie tentativa, correlação e idempotency key.

Mantenha home pública e cenário Icatu não oficial separados. SegSense continua sem chamar o mock e sem conhecer contrato/credenciais Icatu. A Spider é dona da decisão e do despacho; o mock é Test Double, não Provider Satellite certificado. Nenhum dado pessoal, produto, preço, cobertura, elegibilidade ou taxa comercial deve ser inventado. A peça impressa conserva o aviso “DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO”.

## 3. Evidência, segurança e aceitação

Atualize `SEGSENSE_JRN_EVID_001` com matriz `frase/cartão → fato → fonte exata → identificador/timestamp disponível → condição de exibição → comportamento se ausente`. Diferencie explicitamente configuração, ação do cliente, resposta BFF, decisão Spider e resultado do Test Double. Crie `SEGSENSE_OPS_001` com escopo atual versus lacunas futuras; documente como reproduzir a demonstração sem expor segredos.

Teste pelo menos: antes do envio; request pendente; `READY` completo; `REJECTED`; `PROVIDER_UNAVAILABLE`; `SPIDER_UNAVAILABLE`/rede; resposta malformada ou sem `decisionId`; sem `providerRequestId`/`providerReference`; retry da mesma chave e tentativa nova; ausência de mistura entre resultados; contexto sintético explícito; nenhuma frase que atribua ação não observada à Spider; impressão sem resultado não confirmado. Testes devem verificar que os campos exibidos são os da resposta/projeção, não defaults do frontend. Preserve testes de autorização, correlação, idempotência, ACL, independência arquitetural e contrato canônico. Rode lint/test/build frontend, `mvnw verify` no SegSense e testes relevantes da Spider/mock quando tocados. Prove HTTP real da cadeia canônica com runtimes identificados, sem fallback deprecated, e sem imprimir credenciais.

Documente em `SEGSENSE_REV_015.md` a matriz SAT-01–10 com distinção entre V1 demo implementado e certificação/produção, os resultados dos gates, evidência visual e lacunas. Copie este prompt integralmente para `segsense/documents/SEGSENSE_PRM_015.md`, indexe-o, atualize `SEGSENSE_DEMO_RUN_001`, `SEGSENSE_PLN_001` e READMEs pertinentes. Preserve migrations e dados existentes; qualquer migração nova exige justificativa, execução incremental e teste em banco vazio/existente, sem reset de volume. Não faça commit, push ou deploy.

Na devolutiva, comece com: (1) correção do script e prova de que processo alheio não foi encerrado; (2) resultado **verdadeiro** da falha de provedor; (3) painel com matriz de fontes; (4) provas visual e funcional; (5) alterações por aplicação e Git; (6) ressalvas. **Pare para minha auditoria. Não autoaprove e não inicie PRM_016.** Há no máximo um corretivo para este PRM_015.
