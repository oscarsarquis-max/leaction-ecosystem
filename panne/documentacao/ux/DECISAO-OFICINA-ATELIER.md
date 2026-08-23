# Decisão — Oficina + Atelier

O proprietário aprovou a **Oficina como estrutura completa** e a **área central do Atelier**.

Não é uma quarta direção inventada: cada peça foi lida nos protótipos do UX-001.

| Camada | Origem no protótipo | O que entra | O que não entra |
|---|---|---|---|
| Shell, cabeçalho grafite, nav caixa alta | `oficina.css` `.shell-header` / `.domains` | estrutura integral | header claro e Georgia do Atelier |
| Trilho de submenu sempre visível | `oficina.css` `.submenu` | menus e submenus | painel-submenu do Atelier; chips da Mesa |
| Densidade do chrome, badges, pin | Oficina | tratamento operacional | chrome arejado |
| Gaveta do assistente | `oficina.css` `.drawer-assist` | temporária à direita | `.sheet-assist`; overlay; barra permanente |
| Composição central | Atelier: `8vw`, H1 Georgia, `.cards` em grade | página no lugar das seções empilhadas | `.cards { display:block }` e H1 caixa-alta da Oficina |
| Ritmo editorial e auxiliar | Atelier (lede, cartão, espaço) + palco `.stage` | principal ao lado da nota auxiliar | inspetor `.workbench` da Mesa |
| Login e ficha | Atelier + mestres oficiais | logo completo | login estreito da Oficina |
| Mesa | — | nenhum | histórico apenas |

No laboratório a opção chama-se **Direção aprovada — Oficina + Atelier** e abre por padrão.
