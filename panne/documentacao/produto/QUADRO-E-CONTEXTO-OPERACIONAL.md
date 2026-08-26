# Quadro e contexto operacional

O quadro é a central gerencial do turno. Custos ficam fora.

## Contexto

Definido em abertura curta: data operacional, estabelecimento, turno e área/estação. Sem digitação de ID. Catálogo em `GET /production/board/context` (estabelecimentos existentes + turnos/áreas fechados).

Faixa compacta, exemplo: `24 ago 2026 · Padaria Central · Manhã · Fornos`.

Persistência: `sessionStorage` chave `panne.operationalContext.{org}.{usuario}`. Limpa ao trocar organização ou sair. Troca explícita; se houver ordem aberta na gaveta, pede confirmação.

## Filtros temporários

Produto, estado, prioridade, bloqueio/ocorrência e busca única. Chips e painel recolhível. Valores não sensíveis na URL.

## Visões

1. Fluxo por estado/etapa.
2. Lista gerencial densa (tabela sempre disponível).
3. Agrupamento por estação.

Cartões: aguardando liberação, em pesagem, prontas, em execução, bloqueadas, concluídas, encerradas parciais (`short_closed`).

## Vazios

Contexto ausente, nenhuma ordem planejada, filtros sem resultado, sem acesso ao estabelecimento, serviço indisponível e erro recuperável — cada um com ação coerente.
