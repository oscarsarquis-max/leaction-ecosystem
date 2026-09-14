# SEGSENSE_PRM_015_COR_001 — Encerramento seguro da stack de demonstração

## Controle

- Projeto: SegSense. Versão 1.0. Data: 14/09/2026.
- Este é o **único corretivo permitido** do `SEGSENSE_PRM_015`. Não o use para antecipar PRM_016.
- Execução pelo Cursor no monorepo `leaction-ecosystem`, restrita a `segsense/` e, apenas se comprovadamente indispensável, aos scripts de teste da fatia demo. Sem commit, push, deploy ou alteração em produtos alheios.

## Prompt para o Cursor

Na auditoria do PRM_015, a falha de provedor foi comprovada numa Spider isolada e `prove-mvp-http.ps1` deixou de matar o primeiro `mock=` de `pids.txt`. Porém, **`stop-mvp-demo.ps1` ainda pode encerrar um processo identificado apenas por PID do arquivo mais correspondência ampla na command line** (`*segsense-provider-mock*`, `*spring-boot.run.profiles=local-demo*` etc.). Um PID reciclado ou outro processo que use o mesmo projeto/profile pode coincidir. O teste `Assert-MvpRefusesStalePid` verifica `Test-MvpOwnedProcess`, mas o script de parada não usa essa função; portanto, o teste não prova o caminho que realmente mata. Corrija isso antes de recomendar o comando de parada ao usuário.

### Escopo obrigatório

1. Inspecione `start-mvp-demo.ps1`, `stop-mvp-demo.ps1`, `_mvp-process-safety.ps1`, `test-mvp-ops.ps1` e `prove-provider-unavailable-isolated.ps1`. Preserve a stack e os volumes existentes. Não execute o `stop-mvp-demo.ps1` atual como parte da auditoria.
2. Registre, na partida, identidade verificável de **cada processo efetivamente criado pelo script**: papel, PID, porta esperada, executável, command line/marker específico e instante de início. O registro deve ser escrito de modo robusto e permanecer gitignored. Processo que já ocupava uma porta e foi apenas aceito no preflight **não pertence** ao start e jamais pode constar como alvo de stop. Não invente propriedade de JVM filha do Maven ou processo Vite filho do npm: identifique o listener real e a relação demonstrável com a partida, ou falhe fechado.
3. Na parada, use a mesma verificação real para **cada** alvo: PID atual, listener da porta esperada, executável, marcador/command line e início compatível com o registro. Se qualquer evidência estiver ausente, ambígua ou divergente, **não envie `Stop-Process` para esse alvo**; mostre uma mensagem legível e deixe o processo intacto para inspeção manual. Nunca mate por substring ampla ou apenas por `pids.txt`. Não faça limpeza recursiva, não derrube Docker/volume e não use shells misturados para operações destrutivas. Para wrappers/filhos que não possam ser verificados com segurança, prefira não parar automaticamente a correr risco de atingir processo alheio.
4. Teste o **script de parada real**, não só o helper, com registro contendo PID obsoleto/reciclado, processo alheio na mesma porta ou processo semelhante fora desta execução. Comprove `still-running=true` para o alheio. Teste também que um processo de teste inequivocamente próprio pode ser parado, sem tocar a stack da reunião. Se esse cenário seguro não puder ser montado, registre a lacuna; não declare a parada validada.
5. Preserve a prova isolada `PROVIDER_UNAVAILABLE` do PRM_015. Revise seu `finally`: a JVM isolada só pode ser encerrada após validação de propriedade; se falhar, não force o encerramento pelo PID do launcher sem evidência equivalente. Nenhuma prova deve interromper Spider `:8080`, mock `:8095` ou BFF `:8088` da reunião.
6. Atualize `SEGSENSE_DEMO_RUN_001` com instrução honesta de parada. Enquanto o script não estiver comprovadamente seguro, indique que a parada automática está suspensa e requeira inspeção manual; não sugira execução do script antigo. Atualize `SEGSENSE_REV_015` preservando o histórico da ressalva, o índice e copie este prompt integralmente para `segsense/documents/SEGSENSE_PRM_015_COR_001.md`. Toda documentação nova mantém prefixo `SEGSENSE_`.

### Gates de devolutiva

Apresente comparação precisa do caminho antigo e novo de encerramento; prova de que o PID alheio permanece vivo após passar pelo **script real**; prova do caso próprio quando segura; resultado da prova isolada de provedor, identificando a porta fechada e a resposta canônica sem itens/reference; testes e builds pertinentes; estado da stack de reunião e Git. Não imprima segredos, não faça commit/push/deploy. Se algum gate não for cumprido, registre `NÃO COMPROVADO` e deixe a função de parada falhar fechado.

**Pare para auditoria. Não autoaprove e não inicie PRM_016.** As lacunas visual e de produto — entrada de contexto por URL/texto/ditado, intenção trabalhada pelo SegSense e possibilidades explicadas pela Spider — seguem para o próximo prompt original após o fechamento desta etapa. Não haverá segundo corretivo do PRM_015.
