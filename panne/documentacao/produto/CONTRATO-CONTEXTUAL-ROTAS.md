# Contrato contextual das rotas

Tipo `RouteGuide` em `panne/frontend/src/guide/routes.ts`.

Campos: identificador, domínio, seção, título, objetivo, entidade, permissões, ações, pendências, bloqueios, próxima ação, conceitos relacionados, destinos, versão. Estado sujo/comando pendente vem do `AssistantContext`, não do registro estático.

Cobertura testada em `guide.test.tsx`. Nenhuma rota produtiva fica sem orientação mínima. Destinos respeitam permissão efetiva e nunca abrem rota não autorizada.
