# SEGSENSE_SEC_004 — Ameaças da âncora comercial e do backoffice editorial

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_SEC_004 |
| Versão | 1.0 |
| Data | 12/09/2026 |

| Ameaça | Tratamento |
|---|---|
| Alegação de parceria/oferta | Disclaimer permanente; título “não oficial”; sem logo Icatu |
| Conteúdo hostil no CMS | Rejeição de HTML/script; renderização como texto |
| Alegação sem fonte | FK + trigger de fonte verificada |
| Publicação sem aprovação | Trigger SQL + domínio |
| Acesso admin | 401/403; sem IdP, sem login fictício |
| Cache de versão retirada | `no-store` no GET público |
| Chamada externa | Página não faz fetch a Icatu/Spider; só BFF SegSense |

SAT-03 permanece não implementado.
