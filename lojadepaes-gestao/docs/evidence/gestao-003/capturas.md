# Capturas de produção — GESTAO-003

Feitas em https://gestao.lojadepaes.com.br com `scripts/capture-evidence.mjs` (`GESTAO_MODO=porta`), só leitura:
nenhum dado foi gravado em produção. As senhas foram digitadas por Oscar numa janela do PowerShell e não foram gravadas.

| Captura | O que mostra | Resultado |
|---|---|---|
| login-320, 390, 768, 960, 1280, 1440 `.png` | Login com a logo (~72 px) | OK: sem rolagem horizontal, controles com 40/44 px, anel de foco de 2 px, alt "Loja de Pães" |
| login-1280@2x.png | Login a 2x, para conferir a nitidez da logo | OK |
| menu-1280, 960, 1440 `.png` | Menu lateral fixo, logo de ~40 px, etapas com ponto e frase | OK |
| menu-320, 390, 768 `.png` | Gaveta do menu no celular | OK |
| menu-1280@2x.png | Menu lateral a 2x | OK |
| portao-cliente-1280.png, portao-cliente-390.png | `admin@lojadepaes.com.br`: barra de cima com "Loja de Pães – Boulangerie" e CNPJ 69.423.547/0001-04 | OK |
| portao-admin-plataforma-1280.png, portao-admin-plataforma-390.png | `oscar`: "Sua conta não opera nenhuma organização" | OK |

As telas com dados (Hoje com alertas, Entradas, Entrada sem nota, Ingredientes) estão em `../gestao-003-local/`,
porque em produção não se grava dado de teste.
