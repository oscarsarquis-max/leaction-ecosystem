---
title: PRD Sistema de Notificacoes
tipo: PRD
---

# Visao do produto

Este PRD cobre o sistema de notificacoes push, e-mail e in-app para engajar usuarios
com alertas de eventos relevantes (lembretes, atualizacoes de status e campanhas).

## Canais e preferencias

Cada usuario configura preferencias por canal. Push mobile usa FCM/APNs; e-mail usa
templates transacionais; in-app usa feed persistente com marcacao de lido.

### Segmentacao de audiencias

Campanhas podem mirar cohorts por papel, escola ou comportamento recente. Opt-out deve
ser respeitado imediatamente e auditado para LGPD.

## Regras de negocio

Fila de envio com retry exponencial, deduplicacao por `notification_key`, quiet hours
e limite de volume diario por usuario. Metricas: open rate, CTR e taxa de opt-out.
