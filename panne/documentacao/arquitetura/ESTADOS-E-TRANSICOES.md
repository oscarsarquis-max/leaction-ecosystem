# Estados e transições humanas

## Framework

`draft` → `active` (quando a primeira versão é ativada) → `archived`.

## Versão do framework

`draft` → `pending_review` (submissão humana) → `active` (ativação humana).  
A versão ativa anterior passa a `superseded`. `revoked` é ato humano explícito.

Só `draft` é editável. Ativação falha se requisito obrigatório não tiver fonte válida e vigente.

## Requisito

`pending` / `reviewed` / `rejected`. Conteúdo append-only depois de persistido.

## Avaliação

`draft` / `evaluated` / `reviewed` / `invalidated`.  
Completude: `complete`, `incomplete`, `insufficient_context`.

## Revisão da avaliação

Eventos append-only: `accepted`, `rejected`, `needs_changes`, `revoked`.  
Revogação cria **novo** evento e invalida a avaliação. O histórico permanece.

A IA não percorre nenhuma dessas transições.
