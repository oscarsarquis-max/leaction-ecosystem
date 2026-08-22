# Segurança frontend

- sem `dangerouslySetInnerHTML`
- textos da API via React (escape)
- token em memória; preferência de organização no `localStorage` não é credencial
- cliente não registra headers
- esconder botão não autoriza — `RequirePermission` + API
- troca de organização e logout limpam cache e abortam pedidos
- fake auth nunca silencioso em produção
- CSP e headers de segurança ficam para o ciclo de publicação (documentado, não implementado neste host Vite)
