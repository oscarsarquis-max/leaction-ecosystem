# SEGSENSE_PRM_014_COR_001 — Linguagem de jornada estritamente comprovada

## Controle

- Projeto: SegSense; versão 1.0; data: 13/09/2026.
- PRM_014 executado, **não aprovado**. Este é o **único corretivo** específico da etapa.
- Execução pelo Cursor em `C:\Projetos\segsense` e, apenas para corrigir texto emitido pelo contrato canônico, na implementação pontual de `C:\Projetos\spider`. Mock e contrato V1 permanecem independentes e estruturalmente inalterados. Sem commit, push, deploy ou PRM_015.

## Prompt para o Cursor

Regra do patrocinador: **só pode aparecer como parte cumprida da jornada o que efetivamente ocorreu no sistema e tem evidência. Não há fake.** Leia `SEGSENSE_PRM_014`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_REV_014`, o componente `IntegratedMvpPage.tsx`, o mapper canônico e `SatelliteInteractionService` da Spider. Preserve a cadeia real SegSense → Satellite Contract V1 → Spider → Provider Contract → Test Double → Spider → SegSense.

### Achados da auditoria visual e de código

1. A interface mostra `Aguardando resposta da Spider…` enquanto apenas o `fetch` Browser → BFF SegSense está pendente. Nesse instante o navegador **não sabe** se o BFF recebeu o pedido ou se a Spider foi chamada. Em inspeção real, essa frase apareceu antes da resposta. Troque por uma frase de fato observável do cliente, por exemplo `Solicitação enviada; aguardando resposta do SegSense…` somente depois que o envio do navegador for iniciado, ou `Aguardando resultado da solicitação…`. Não use “Spider recebeu”, “Spider analisa” ou “mock processa” sem evento ou confirmação correspondente.
2. A resposta canônica contém `A Spider compreendeu objetivo e contexto governados e despachou a capability…`, mas o serviço atual faz **validação determinística de allowlist, contexto/objetivo e resolução de capability**; não há CTX-004 ou interpretação semântica/Intent Contract pleno. Corrija a redação emitida pela Spider para descrever exatamente o que ocorreu, por exemplo `A Spider validou o contexto e o objetivo sintéticos permitidos e despachou a capability ao executor registrado.` Não use “compreendeu”, “interpretou necessidade”, “personalizou seguro” ou equivalente até existir evidência da capacidade. Preserve retorno, IDs, estado e schema; a mudança deve ser somente de copy onde possível.
3. Audite as frases da pré-proposta impressa, home, demo Icatu e roteiro para o mesmo padrão. A existência de um campo na resposta não prova uma semântica além do que o serviço executou. “Contexto confirmado” significa que a Spider validou a versão e a origem governada sintética, não que verificou a vida real do visitante. “Itens do provedor” são itens ilustrativos do Test Double, não produtos disponíveis. Atualize a matriz `SEGSENSE_JRN_EVID_001` para que fonte, condição e texto coincidam com o runtime pós-ajuste.

### Provas e limites

Teste em frontend o estado pendente antes de qualquer resposta BFF e depois de falha de rede; nenhum texto deve atribuir processamento à Spider sem confirmação. Teste na Spider o resultado READY e REJECTED para garantir explicação determinística e ausência de “compreendeu”. Reexecute contrato/HTTP real com três processos para verificar que a pré-proposta contém a redação nova **vinda da Spider**, não substituição local no frontend, e que a fatia deprecated não é chamada pelo SegSense. Sem novas etapas cronometradas, defaults de IDs, mock de produção ou mudanças no Satellite Contract V1. Preserve ACL restrita/preflight e não exponha segredos.

Se houver browser, confira o fluxo real e a peça impressa; registre viewports/teclado que tiverem sido de fato examinados. Não marque 768/390/320/zoom 200% como verificados sem executá-los. A auditoria independente já confirmou apenas a vista desktop e uma pré-proposta real no browser; isso não substitui toda a matriz visual.

Arquive cópia integral deste prompt em `segsense/documents/SEGSENSE_PRM_014_COR_001.md`, atualize índice, `SEGSENSE_REV_014` e `SEGSENSE_DEMO_RUN_001`. Todo documento **novo** desta conversa começa com `SEGSENSE_`; não renomeie `SPIDER-SAT-003`. Na devolutiva, liste frases antes/depois, fonte técnica de cada uma, testes, HTTP real, lacunas visuais e Git por aplicação. **Pare para auditoria; não autoaprove e não inicie PRM_015.** Se persistir ressalva, ela passa ao próximo prompt original; não haverá segundo corretivo do PRM_014.
