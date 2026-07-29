---
title: SDD Geracao de Relatorios
tipo: SDD
---

# Arquitetura de relatorios

Este SDD descreve a geracao assíncrona de relatorios analiticos (PDF/CSV/XLSX) a partir
de consultas agregadas no data warehouse operacional.

## Pipeline de geracao

O usuario solicita um relatorio; a API enfileira um job; workers leem o warehouse,
montam o arquivo e gravam em object storage. Notificacao de conclusao e enviada quando
o artefato esta pronto para download.

### Agendamento e templates

Relatorios recorrentes usam cron expressions. Templates parametrizam filtros (periodo,
tenant, escola). Cache de resultados intermediarios reduz custo de consultas pesadas.

## Componentes

Report API, fila Redis/SQS, workers Python, storage S3-compativel e catalogo de
templates versionados. Contratos: `/reports`, `/reports/{id}/download`, `/schedules`.
