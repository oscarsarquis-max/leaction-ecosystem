# REV 044 — Extrato no projeto Fluxo

Data: 15/10/2026. A base efetiva antes deste incremento era **0.2.3**, já publicada, e não a 0.2.2 citada no último relato anterior. A 0.2.3 já lia o relatório antes do vínculo e já tratava saldo desconhecido como «Não apurado». Este incremento recompõe a tela e publica **0.2.4**. A conta produtiva não foi recriada, o arquivo real não foi importado e nenhum dinheiro foi movimentado. Schema permanece V23. Aceite continua com o proprietário.

## Fontes inspecionadas

Raiz `C:\Projetos\claude\2026-10-15-interface-gestao-financeira`. Lidos `notas.md`, `log-conversa.md`, `design\canvas.json` e os nove `design\*.dc.html`. Os nove `referencia\html\*.html` foram abertos; usam Geist local com licença OFL. A pasta `referencia\png` descrita no log não está na árvore. A comparação usou os HTML independentes, sem `support.js`. Os originais não foram alterados.

## O que a tela passou a fazer

Título «Extrato da conta» e «Importar relatório» na mesma linha. A conta selecionada, a moeda e a data usada pelo relatório ficam na linha seguinte. Abas Todas, Identificadas e Em revisão, com contagem: linha é o evento gravado; ocorrência em revisão é outra unidade e usa o total autorizado, não o corte de 200. A tabela fica num cartão branco, com busca e período na faixa interna. O terço direito traz resumo, evolução, próxima ação e um único bloco de posição. No desktop, a linha abre o detalhe nesse terço. No celular, o detalhe é outra página e o retorno conserva conta, filtros e posição.

Geist e Geist Mono estão empacotados em `frontend/src/fonts`, com a licença OFL. Entradas usam `#1F5FA8`, saídas `#B4441C` e a ação principal o azul `#1603AD`. Fundo `#F3F5F4`, superfície branca, raio de 14 px. A faixa e as duas barras do ActionFinance permanecem. Não há sidebar, barra inferior, Exportar, Pagar, Aceitar sugestões, Conectar Open Finance nem Anexar.

## Importação e saldo

A jornada da 0.2.3 permanece: o arquivo é lido antes do vínculo, a confirmação da conta não importa o relatório, identificador divergente não substitui o vínculo e o mesmo arquivo segue para a prévia. Sem saldo inicial, saldo anterior, final, atual e após o movimento continuam «Não apurado». Um zero informado continua R$ 0,00. Nada grava saldo inicial zero para esconder a lacuna.

A lista passa a devolver `undatedCreditMinor` e `undatedDebitMinor`. Valor elegível sem data entra no resumo e fica fora do gráfico, com a parcela indicada. Os campos novos são ignoráveis pelos consumidores antigos. A contagem de revisão usa `reviewCount`; se a lista vier cortada em 200, a tela diz quantas ocorrências está mostrando e qual é o total autorizado.

## Prova isolada

Empresa de demonstração, conta nova sem saldo inicial e sem vínculo. Fixture sanitizada de uma linha, no formato do relatório, sem o arquivo real.

Percurso por clique: cadastrar conta → detalhe sem R$ 0,00 → importar → identificação → confirmar a conta → prévia → confirmar a fixture → lista e análise → detalhe no desktop → detalhe em página própria a 390 px, sem rolagem horizontal → arquivo de outra identificação, sem trocar o vínculo → conta com saldo inicial 0,00 permanecendo R$ 0,00. Em 1440×900, com o shell completo, quatro linhas ficaram visíveis. Testes de tela: 37, sem falha.

Capturas em `documents/reviews/evidence/extrato-044/`. A prancha de Lançamentos e a de Contas no celular foram fotografadas ao lado, na mesma ferramenta. Diferenças mantidas de propósito: shell e marca do ActionFinance, ausência dos botões sem função, ausência de calendário de títulos, de orçamento e de assistente.

## Publicação

| Peça | Valor |
|---|---|
| Código | `95545ab587756f78a04592d231a28c3093102237` |
| Task | `actionfinance-web:21` |
| linux/amd64 | `sha256:6e47b9eaa1658e78254cbc087e995a25a87a2e87575310b90138d544baa24f1d` |
| Bundle | `index-Dg2CBQGA.js` |
| Host | `version=0.2.4`, health 200, linhas sem sessão 401 |
| Rollback | `actionfinance-web:20`, produto 0.2.3, `index-Dlf7Kh7L.js` |

A sessão autenticada do host público não percorreu a tela. A prova isolada não é essa sessão e não é o aceite.
