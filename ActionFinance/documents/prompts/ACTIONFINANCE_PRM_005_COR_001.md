# ACTIONFINANCE_PRM_005_COR_001 — Ajuste pontual do cabeçalho compacto

Data: 29/09/2026. Prompt do analista para o Cursor. Mesmo recorte do PRM_005; sem PRM_006.

## Parecer e escopo

A direção visual está aprovada: azul navy, amarelo prioritário, área clara, controles e logos. Os hashes dos assets correspondem às cópias aprovadas. O analista examinou relatório, capturas desktop/tablet/mobile, AppShell e regras de layout. Não reexecutou a jornada ou os gates; estes permanecem evidências do executor. Não há pedido de alteração de domínio, persistência, contratos ou regras financeiras.

Resta um defeito visual concreto: em mobile-360-modal.png o texto “Operador empresa A” atravessa a logo amarela no cabeçalho. A grade compacta usa menu/brand/user na mesma linha; as larguras não cabem em 360 px. scrollWidth=clientWidth não detecta sobreposição interna.

Execute somente os ajustes abaixo em C:\Projetos\ActionFinance. Preserve dados, migrations, assets e versões. Sem commit/push/deploy ou mudanças em outros produtos.

## C1 — Reorganizar cabeçalho em 360 px

Para largura inferior a 768 px, usar distribuição explícita:

1. Primeira linha: Menu à esquerda e logo amarela à direita, com 144 px de largura e altura proporcional.
2. Segunda linha: empresa ativa, com label e nome/seletor; nome longo pode quebrar linha.
3. Terceira linha: badge Demonstração local e usuário/Sair. Se não couberem juntos, quebrar em linhas dentro da mesma região, sem sobreposição.

Não reduzir a logo, retirar CAPITAL, cortar imagem, comprimir letras ou usar overflow:hidden para esconder o problema. Não diminuir fonte até tornar o usuário ilegível. Sair permanece acessível; empresa ativa não desaparece. Tablet/desktop mantêm disposição atual se houver espaço.

Verificar com nomes longos de usuário e empresa. Usar min-width:0, quebra de texto e grid/flex coerentes, sem posicionamento absoluto sobre a marca. Preservar proteção de alterações pendentes ao trocar empresa/sair.

## C2 — Foco do drawer e mudança de largura

No AppShell, o efeito de contenção de foco está condicionado apenas a navOpen. Ajustar para funcionar somente quando compact && navOpen. Ao sair do breakpoint compacto, encerrar o estado de drawer e remover backdrop/contenção/inert temporários, sem devolver foco a botão Menu oculto no desktop.

Ao selecionar destino com navegação efetivada, fechar drawer e levar foco ao título/conteúdo principal; ao fechar sem navegar, retornar ao Menu visível. Se a navegação for recusada pela proteção de formulário, preservar contexto e foco úteis, sem enviar o usuário a título de página que não abriu.

Provar por teclado automatizado, sem exigir gravação humana: abrir com Menu, percorrer Tab/Shift+Tab, fechar com Escape, selecionar destino e redimensionar de compacto para desktop com menu aberto. A presença do handler no código não substitui observar o foco.

## Verificação e entrega

Capturar cabeçalho em 360 px com menu fechado, modal de estorno aberto e nomes longos; em 768/1280 conferir ausência de regressão. Verificar caixas delimitadoras de menu/logo/usuário: nenhum texto ou alvo interativo sobreposto. Inspecionar visualmente as capturas, além da métrica de largura.

Rodar lint, testes de frontend e build; acrescentar apenas os testes relevantes de layout/foco. Não repetir backend, migrations, restore ou toda a jornada financeira para este ajuste de apresentação. Nenhuma dependência nova é necessária.

Salvar cópia integral deste prompt em documents/prompts/ACTIONFINANCE_PRM_005_COR_001.md. Acrescentar adendo a ACTIONFINANCE_REV_005.md com mudanças, capturas e resultados. Registrar que paleta/assets estão aprovados e que este ajuste encerra o defeito do cabeçalho, sem alegar autoaprovação final.

Parar e devolver o resultado ao proprietário para aceite focado do analista. Não iniciar PRM_006.
