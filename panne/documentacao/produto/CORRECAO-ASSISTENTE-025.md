# Correção do assistente (CURSOR-025)

O retorno do 024 afirmou cobertura integral. No produto real faltava o assistente em algumas páginas, o texto podia estar descontextualizado e o estado minimizado era um botão textual.

## O que mudou

- Avatar compacto no shell, sempre montado.
- Login com modo público e o mesmo componente.
- Lista de rotas extraída do router real.
- Contexto vivo por overlay + guia.
- Troca de rota, entidade e organização sem vazamento.
- Matriz gerada em `guide/matrix.ts`.
