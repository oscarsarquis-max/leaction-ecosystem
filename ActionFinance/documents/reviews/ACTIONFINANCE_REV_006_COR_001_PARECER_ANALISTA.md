# PRM_006 — Parecer sobre os três pontos finais

Data: 29/09/2026. Analista.

**Aceitos os três pontos funcionais do complemento:** sessão após restart, upgrade/restore e cadastro rápido pela interface. A revisão examinou os quatro logs JSON apresentados, trechos dos scripts de prova de restart/upgrade, a separação de QuickCatalog do formulário pai, o portal de Modal e capturas novas desktop/mobile. Os ensaios não foram reexecutados pelo analista.

O restart mantém ator/empresa sem novo provisionamento; revogação retorna 403. O upgrade/restore preserva fatos e identidade; a invalidação posterior impede uso do cookie restaurado. O cadastro rápido registra contraparte e categoria pela interface sem submeter o título antecipadamente. Esses pontos estão encerrados e não devem ser repetidos sem alteração pertinente.

Imagem deste complemento: `sha256:329a018e649ebc00ce5a7722b95866d575467b0fcd6821df7e299757640a30cd`. JAR: `5dcde9c70436da79e1539a9f4801c03ed03fcc6afee07874d60d0baa8c280974`. Não atribuir o complemento à imagem anterior.

## Único residual de apresentação

A captura `mobile-360-quick-catalog-filled.png` apresenta conteúdo mais largo que o viewport declarado de 360 px: fieldsets/inputs avançam à direita do cartão e do cabeçalho. O script `capture-prm-006-quick-catalog.mjs` informa o viewport, mas não mede `scrollWidth/clientWidth`. Portanto, esse ensaio não prova preservação da responsividade.

As capturas fullPage também mostram o cabeçalho sticky no meio do formulário. Isso pode refletir o scroll no momento da captura; não se conclui por imagem isolada que o cabeçalho esteja defeituoso. Conferir o comportamento visível no viewport antes de modificar seu posicionamento.

Aceite integral pendente somente desse residual visual. Não há nova ressalva de sessão, autorização ou banco. Não iniciar PRM_007 ou produção.

## Prompt ao Cursor — fechar o residual visual no mesmo COR_001

1. Reproduzir Novo recebível com os nomes longos do ensaio, em 360 px, antes e depois de cadastrar contraparte/categoria. Medir `document.documentElement.clientWidth`, `scrollWidth` e limites dos fieldsets, inputs/selects e cartão; guardar resultados.
2. Corrigir apenas o transbordamento constatado. Verificar largura mínima intrínseca de fieldset/select/grid; aplicar restrições de largura adequadas sem esconder conteúdo com overflow-x hidden, cortar rótulos ou reduzir globalmente a tipografia. Preservar marca e logo, menu, foco e fluxo aprovado.
3. Capturar viewport real no topo e ao rolar até ações, além de fullPage após normalizar scroll. Comprovar que cabeçalho não impede acesso aos campos/botões. Se a posição intermediária for só efeito da captura, documentar isso e não alterar o shell desnecessariamente.
4. Acrescentar assertion de ausência de overflow ao script: scrollWidth igual a clientWidth em 360, 768 e 1280, incluindo formulário preenchido com nomes longos. Confirmar cadastro rápido e registro na largura afetada. Não repetir upgrade/restore/restart.
5. Executar lint/test/build pertinentes. Atualizar a imagem caso haja mudança frontend e registrar novo ID/hash, para não apresentar imagem antiga como versão corrigida. Se nenhum código mudar, justificar e mostrar a evidência que resolve a divergência da captura.
6. Acrescentar um adendo curto ao REV_006_COR_001, copiar este parecer para documents/reviews e indexar. Retornar medidas, capturas e resultado. Sem mudanças backend/migrations, DNS/AWS, commit/push ou novo ciclo.

Este é um ajuste limitado à evidência visual do formulário. IdP real e infraestrutura remota continuam etapas posteriores da publicação.
