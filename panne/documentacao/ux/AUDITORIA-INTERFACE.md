# Auditoria da interface atual

Inspeção em 2026-08-23 sobre a aplicação local (`:5180` + API `:5080`), código em `panne/frontend` e evidências 015/016. Base `7f5045772101217bc1ae1a92762e1797ebbd2c5f`.

## Navegação

Cabeçalho grafite horizontal: texto “Panne”, Produção, Planejamento, Ordens, Rastreabilidade, organização e conta. Sem submenus. Sem Receitas, Componentes, Conformidade ou Gestão. No modo operacional a navegação secundária some (`shell-ops`).

## Marca

Logo quadrado 2000×2000 só no login e na ficha. Depois do login a marca vira a palavra “Panne” em texto. A assinatura caligráfica some. Em cabeçalho baixo o lettering do PNG seria ilegível.

## Consistência

Bege `#E5E4D6` e grafite `#323334` estão corretos. Tipografia única (Segoe UI). Componentes simples: tabela, badge com ponto, cartão de filtro, diálogo de confirmação no operacional. Pouca variação de densidade.

## Área, densidade e hierarquia

O quadro aproveita bem a largura. Títulos pequenos (1,35rem). Login é um cartão estreito no centro. Rastreabilidade também cabe num cartão estreito. Hierarquia plana: tudo parece do mesmo peso.

## Responsividade

Abaixo de 900 px o menu vira botão “Menu”. Tablet funciona, mas não há experiência específica de toque além de alvos de 40 px. Sem adaptação de densidade por papel.

## Estados

Carregamento, vazio, erro, 401/403/409/503 e conflito existem e estão testados. Sem esqueleto visual. Sem indicadores de atualização contínua fora do operacional (polling 20 s).

## Acessibilidade

Landmarks, labels, foco, axe sem críticos, `prefers-reduced-motion`. Contraste AA do par bege/grafite. Submenus ainda não existem para validar.

## Pontos fortes

 paleta fiel; backend soberano; modo operacional denso e honesto; impressão A4 sem custos; estados de erro claros.

## Dívida visual

marca ausente após o login; IA incompleta (só produção); “Cadastros” ainda não existem, mas também não há Componentes; sem assistente; badges só de estado; sem gamificação responsável; área do login desperdiçada pelo PNG quadrado.
