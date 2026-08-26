# Política de estoque

Política versionada por organização e, opcionalmente, por estabelecimento.

Padrões da primeira versão publicada:

- saldo negativo: negar
- lote: opcional na política, exigível no item
- validade obrigatória por configuração
- consumo de lote: sugestão FEFO, confirmação humana
- tolerâncias de recebimento e inventário em percentual Decimal
- reserva não ocorre na liberação da ordem neste ciclo (`reserve_on_release=false`)
- ordem cancelada: libera reserva
- retorno restaura disponível; desperdício reduz físico
- ajuste exige aprovação
- alerta de validade: 7 dias
- algoritmo `inventory_procurement` v1

Política publicada é imutável. Mudança gera nova versão. Operações gravam o `inventory_policy_version_id` usado.
