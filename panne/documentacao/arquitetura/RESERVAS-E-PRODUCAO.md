# Reservas e produção

Reservas nascem do snapshot da ordem, por item e quantidade canônica. Alocação por lote/local é separada da necessidade.

Estados: `pending`, `partial`, `reserved`, `released`, `consumed`, `cancelled`, `expired`.

Ordens anteriores ao 0020 não recebem reserva silenciosa. Comando `adopt_historical` + motivo.

Fronteira transacional: o consumo operacional persiste primeiro. A postagem de estoque é posterior, idempotente, e pode ficar `pending`/`failed` sem apagar o fato de produção.
