# SEGSENSE_PRM_001_COR_001 — Correção documental da fundação

## Controle

- Projeto: SegSense
- Prompt original: SEGSENSE_PRM_001
- Tipo: único prompt corretivo permitido
- Versão: 1.1
- Data: 04/09/2026
- Situação anterior: CORREÇÃO ÚNICA NECESSÁRIA

## Divergência com o texto anterior deste identificador

Em 04/09/2026 este arquivo registrou o corretivo que apenas copiou `SEGSENSE_ARQ_001`, `SEGSENSE_PLN_001` e `SEGSENSE_PRM_001` e revisou a fundação só contra o ARQ. O prompt vigente abaixo **substitui** aquele texto como único corretivo autorizado: passa a exigir também `SPIDER-ARCH-017`, reconciliação das duas arquiteturas, avaliação `SAT-01` a `SAT-10` e ajuste dos READMEs de integração. O texto anterior permanece no apêndice, sem perda de conteúdo.

## Prompt para o Cursor

Execute o **único corretivo autorizado** para o `SEGSENSE_PRM_001` no workspace Git existente `leaction-ecosystem`.

O produto SegSense está em `C:\Projetos\segsense`. Não execute `git init`, não altere remotes, não faça commit ou push e não modifique outros produtos do monorepo.

### Motivo da correção

A fundação técnica foi validada, mas o documento arquitetural obrigatório `SEGSENSE_ARQ_001` não está em `C:\Projetos\segsense\documents`.

Além disso, o documento `SPIDER-ARCH-017 — Arquitetura de Aplicações Satélite e Satellite Contract` passou a ser referência normativa. O desenvolvimento não poderá seguir sem que ambas as arquiteturas estejam disponíveis e reconciliadas dentro do workspace.

### Escopo obrigatório

1. Inspecione o estado atual de `C:\Projetos\segsense` e preserve todo o código funcional já validado.

2. Copie, sem resumir nem reinterpretar, os documentos abaixo para `C:\Projetos\segsense\documents`:

   - `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_ARQ_001.md`;
   - `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_PLN_001.md`;
   - `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_PRM_001.md`.

3. Crie `documents\references` e copie integralmente:

   - origem: `C:\Users\Oscar Sarquis\.codex\attachments\2f7264eb-f9f6-473c-955d-4e9520c678db\pasted-text.txt`;
   - destino: `documents\references\SPIDER-ARCH-017.md`.

4. Registre este próprio prompt em:

   `documents\SEGSENSE_PRM_001_COR_001.md`

5. Atualize `documents\README.md` para funcionar como índice documental, contendo identificador, título, versão, situação e caminho de cada documento. Inclua `SPIDER-ARCH-017` como referência normativa externa.

6. Atualize o `README.md` raiz para:

   - remover a informação de que `SEGSENSE_ARQ_001` está ausente;
   - apontar para o índice documental;
   - identificar o SegSense como Insurance Reference Satellite;
   - identificar o backend Java como Satellite BFF;
   - informar que a Spider permanece `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`.

7. Leia integralmente:

   - `documents\SEGSENSE_ARQ_001.md`;
   - `documents\references\SPIDER-ARCH-017.md`.

8. Revise apenas os documentos:

   - `services\spider-integration\README.md`;
   - `services\icatu-integration\README.md`.

   Eles deverão esclarecer que:

   - o backend SegSense exercerá a função de Satellite BFF;
   - o frontend nunca chamará a Spider diretamente;
   - credenciais técnicas nunca ficarão no frontend;
   - o SegSense enviará objetivo e contexto pelo Satellite Contract;
   - o BFF não escolherá route, adapter, sistema executor ou Execution Plan;
   - a Icatu será um executor potencial de capabilities resolvidas pela Spider;
   - o SegSense não escolherá nem implementará integração operacional direta com a Icatu;
   - o boundary atual é `SIMULATED_INFRASTRUCTURE / MOCK_ONLY`;
   - nenhuma integração real está sendo declarada.

9. Produza `documents\SEGSENSE_REV_001.md` confrontando a fundação com `SEGSENSE_ARQ_001` e `SPIDER-ARCH-017`.

   Registre:

   - itens aderentes;
   - divergências encontradas;
   - riscos;
   - situação atual dos requisitos `SAT-01` a `SAT-10`;
   - conclusão objetiva.

10. Na avaliação `SAT-01` a `SAT-10`, não marque como implementado aquilo que ainda não existe. Use estados como:

    - `ATENDIDO`;
    - `PARCIAL`;
    - `NÃO IMPLEMENTADO`;
    - `NÃO APLICÁVEL NESTA ETAPA`.

11. Se a leitura revelar divergência técnica real, não altere código por iniciativa própria. Registre-a em `SEGSENSE_REV_001` para tratamento no próximo prompt.

### Restrições

- Não alterar backend, frontend, banco, Compose, dependências ou portas.
- Não criar regras de negócio de seguros.
- Não implementar Satellite Contract nesta correção.
- Não criar Satellite Manifest fictício.
- Não criar client, adapter, mock, endpoint, payload ou credencial de Spider ou Icatu.
- Não criar máquina de estados operacional paralela.
- Não alterar documentos ou código de outros produtos.
- Não apagar nem sobrescrever documento divergente sem comparar e relatar.
- Não antecipar o `SEGSENSE_PRM_002`.

### Validações obrigatórias

1. Confirmar que os documentos SegSense e `references\SPIDER-ARCH-017.md` existem em `C:\Projetos\segsense\documents`.
2. Confirmar que todos os caminhos do índice documental existem.
3. Confirmar que o README raiz não declara mais ausência do ARQ_001.
4. Confirmar que os READMEs de integração não sugerem integração direta SegSense–Icatu.
5. Confirmar que nenhum arquivo fora de `C:\Projetos\segsense` foi alterado.
6. Apresentar o estado Git limitado ao caminho `segsense/`.
7. Se o ambiente ainda estiver ligado, verificar `system/info` e readiness. Se estiver desligado, registrar isso sem reiniciá-lo apenas para a correção documental.

### Critérios de aceite

- `SEGSENSE_ARQ_001` está disponível e íntegro no workspace.
- `SPIDER-ARCH-017` está preservado como referência normativa.
- Plano, prompt original e corretivo estão na documentação oficial.
- Existe índice documental navegável e consistente.
- A fundação foi confrontada com as duas arquiteturas.
- Os requisitos `SAT-01` a `SAT-10` possuem avaliação honesta.
- Os READMEs não sugerem integração direta com a Icatu.
- Nenhum código funcional ou outro produto foi alterado indevidamente.

### Devolutiva obrigatória

Informe:

1. arquivos criados e alterados;
2. índice documental final;
3. resultado da comparação com as fontes;
4. conclusão da revisão arquitetural;
5. situação de `SAT-01` a `SAT-10`;
6. estado Git restrito a `segsense/`;
7. ressalvas remanescentes.

Não faça commit, push ou deploy.

## Apêndice — texto anterior deste identificador (v1.0)

O bloco abaixo é o corretivo documental executado antes da inclusão normativa de `SPIDER-ARCH-017`. Conservado para auditoria.

```markdown
# SEGSENSE_PRM_001_COR_001 — Correção documental da fundação

## Controle

- Projeto: SegSense
- Prompt original: SEGSENSE_PRM_001
- Tipo: único prompt corretivo permitido
- Versão: 1.0
- Data: 04/09/2026
- Situação anterior: CORREÇÃO ÚNICA NECESSÁRIA

## Prompt para o Cursor

Execute o **único corretivo autorizado** para o `SEGSENSE_PRM_001` no workspace Git existente `leaction-ecosystem`.

O produto SegSense está em `C:\Projetos\segsense`. Não execute `git init`, não altere remotes, não faça commit ou push e não modifique outros produtos do monorepo.

### Motivo da correção

A fundação técnica foi validada, mas o documento arquitetural obrigatório `SEGSENSE_ARQ_001` não está em `C:\Projetos\segsense\documents`. O desenvolvimento não pode seguir sem sua fonte arquitetural dentro do workspace.

### Escopo obrigatório

1. Inspecione o estado atual de `C:\Projetos\segsense` e preserve todo o código funcional já validado.
2. Copie, sem resumir nem reinterpretar, os documentos abaixo para `C:\Projetos\segsense\documents`:
   - origem `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_ARQ_001.md`;
   - origem `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_PLN_001.md`;
   - origem `C:\Users\Oscar Sarquis\Documents\Codex\2026-09-04\contextualize-se-sobre\outputs\SEGSENSE_PRM_001.md`.
3. Registre este próprio prompt em `documents\SEGSENSE_PRM_001_COR_001.md`.
4. Atualize `documents\README.md` para funcionar como índice documental, contendo identificador, título, versão, situação e caminho de cada documento.
5. Atualize o `README.md` raiz para remover a informação de que `SEGSENSE_ARQ_001` está ausente e apontar para o índice documental.
6. Leia integralmente `documents\SEGSENSE_ARQ_001.md` após a cópia e confronte a fundação já criada com seus princípios.
7. Produza `documents\SEGSENSE_REV_001.md` com a revisão de aderência da fundação ao `SEGSENSE_ARQ_001`, registrando:
   - itens aderentes;
   - divergências encontradas;
   - riscos;
   - conclusão objetiva.
8. Se a leitura revelar divergência técnica real, não amplie o escopo e não altere código por iniciativa própria. Registre a divergência em `SEGSENSE_REV_001` para decisão na próxima etapa.
```
