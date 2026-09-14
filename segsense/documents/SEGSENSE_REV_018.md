# SEGSENSE_REV_018 — Revisão de aderência do PRM_018

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_REV_018 |
| Versão | 1.0 |
| Data | 14/09/2026 |
| Status | PRM_018 executado nesta etapa. **Não** autoaprovado. Não inicia PRM_019. Há no máximo um corretivo para este PRM. |

## Reprogramação

O identificador PRM_018 **não** entregou testes ponta a ponta nem piloto. Entregou **marca perceptível** em todas as superfícies reais e **aceite visual demonstrável** na stack isolada. E2E/piloto original permanece no plano (`SEGSENSE_PLN_001` v1.23) e **não** foi marcado como realizado.

## Inventário (URL ativa `:15178`, 1440×900, antes da edição)

O PNG oficial é 2000×2000. Conteúdo visível (alfa > 8): bbox `(208, 489, 1839, 1388)` — 81,6% da largura e **45% da altura**. Aumentar só o box do `<img>` ampliava margem vazia.

| Superfície | Posição (x,y) | Box CSS antes | Marca perceptível aprox. | Nome textual | Navegação |
|---|---|---|---|---|---|
| Home `/` | header `.home-top`, esquerda | 72×72 (`4.5rem` square) | ~32 px de altura | não | âncoras + Icatu + MVP |
| MVP `/demonstracao/mvp-integrado` | `.demo-top`, abaixo do watermark | `max-height: 2.4rem` → 38×38 | ~17 px | não (`alt=SegSense`) | logo → `/`; nav «Voltar à apresentação» |
| Icatu `/demonstracao/icatu` | `.demo-top` | token público 180×180 | ~81 px no centro do quadro vazio | não | logo → `/` |
| Fonte `/demonstracao/fontes/continuidade-familiar` | igual ao MVP | 38×38 | ~17 px | não | logo → `/`; «Voltar à jornada» |
| Admin `/admin` (HTML 200; corpo sem IdP) | `.admin-header` esquerda | 72×72 | ~32 px + texto «SegSense» | sim | Início / Catálogo / Oportunidades / Demonstrações |
| Público inválido `/c/prm018-no-token` | `.public-header` centrado | 180×180 | ~81 px | não | nenhum (não é convite vigente) |

Destinos de navegação **não** foram alterados. Paleta inalterada. Sem logo Icatu/Panne.

## Derivado de recorte (transparência periférica)

| Item | Valor |
|---|---|
| Original | `frontend/images/segsense logo.png` |
| SHA-256 original (antes e depois) | `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D` |
| Processo | `scripts/trim-segsense-logo-header.py`: alfa>8, pad 24 px, crop `(184, 465, 1863, 1412)` |
| Derivado | `frontend/images/segsense-logo-header.png` 1679×947 |
| O que não foi feito | redesenho, recoloração, distorção, recorte de símbolo/nome/tagline, `transform: scale()` |

A tagline *SMART CONTRACTS FOR ENSURE* permanece na arte. Em 320 px fica no limite da leitura; **não** foi redesenhada.

## Depois (mesma URL, 1440×900)

| Superfície | Posição | Box depois | Marca perceptível | Token / override | Evidência |
|---|---|---|---|---|---|
| Home | (160, 16) inalterada | 142×80 | preenche o box (~80 px) | `--segsense-home-logo: 5rem` | `after-home-header-1440x900.png` |
| MVP | (192, 59.6) inalterada | 177×100 | preenche (~100 px; era ~17) | `--segsense-demo-logo: 6.25rem`; removido `max-height: 2.4rem` | `after-mvp-header-1440x900.png` |
| Icatu | (192, 71.6) inalterada | 177×100 | ~100 px (era ~81 no quadro 180) | mesmo token demo | `after-icatu-header-1440x900.png` |
| Fonte governada | (192, 59.6) | 177×100 | ~100 px | mesmo token demo | `after-governed-header-1440x900.png` |
| Admin 401 honesto | (16, 12) | 106×60 + nome «SegSense» | ~60 px | `--segsense-admin-logo: 3.75rem` | `after-admin-1440x900.png` |
| Público inválido (rotulado; **não** convite vigente) | centrado; y=32 | 241×136 | ~136 px | `--segsense-public-logo` | `after-public-invalid-header-1440x900.png` |

Em 320×568 o logo permanece reconhecível (home 121×68; MVP/Icatu/fonte 135×76; admin 92×52 + nome; público 184×104). Overflow horizontal: **não** observado nos viewports medidos, inclusive zoom 200%.

Icatu: o **quadro** encolheu (180→100 de altura) porque a margem vazia saiu; a **marca** cresceu (~81→100). Não é regressão perceptível.

## Teclado, impressão, ditado

| Prova | Resultado |
|---|---|
| Teclado na jornada `:15178/demonstracao/mvp-integrado` | Tab: skip-link → logo «Voltar à apresentação» → nav → textarea → Ditar → URL → fontes → intenções → confirmações → CTA. Anel `rgb(96, 24, 232) solid 3px` em cada controle. `after-mvp-logo-link-focus.png` |
| Impressão do resultado corrente | `form` e `.demo-top` ocultos; watermark visível; «Possibilidades ilustrativas» da tentativa atual; sem resultado antigo. `after-mvp-print-current-result.png` |
| Ditado real | **NÃO VERIFICADO**. Chrome expõe `webkitSpeechRecognition`, mas esta prova **não** pediu nem aceitou microfone. Fallback de texto permanece. A UI afirma que o SegSense não recebe/grava áudio; **não** atribui processamento local ao navegador |

## Jornada real (versão nova)

Contexto governado «continuidade familiar» + intenção confirmada + «Ver possibilidades ilustrativas» em `http://127.0.0.1:15178/demonstracao/mvp-integrado`. Resultado do Test Double visível; explicação pública humana da Spider, sem enums. Captura: `after-mvp-family-result-1440.png`.

`/admin` na stack nova renderiza o shell com a mensagem «A autenticação administrativa ainda não está configurada». Não foi fabricada sessão autenticada. `/c/prm018-no-token` é estado de convite inexistente no `PublicShell`, **não** runtime de convite vigente.

## Gates

| Gate | Resultado |
|---|---|
| Frontend lint | ok |
| Frontend test | 16 arquivos / 77 testes, inclusive SHA do PNG original e regressão CSS por superfície |
| Frontend build | ok; empacota `segsense-logo-header.png` |
| `mvnw verify` | **não** executado: backend Java não foi tocado |
| Spider / mock | **não** alterados (sem razão para o logo) |
| Contrato 1.1, proveniência, timestamps, V1–V15, possibilidades | intocados |
| SHA original | preservado |
| Stack `:15178` | deixada no ar; `:5178` permanece código anterior, não morta |

## Ressalvas honestas

1. Ditado real com permissão de microfone: **NÃO VERIFICADO**.
2. Tagline institucional no PNG continua pequena em 320 px; arte não foi alterada.
3. `/c/{token}` vigente não foi aberto (não há token de uso único nesta auditoria). A prova pública é o `PublicShell` em estado inexistente, rotulado.
4. E2E/piloto do PRM_018 original **não** foi feito.
5. Esta revisão **não** aprova o PRM. Há no máximo um corretivo.

Evidências: `documents/evidencias/SEGSENSE_PRM_018/`.
