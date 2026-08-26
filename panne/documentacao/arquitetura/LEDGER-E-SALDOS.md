# Ledger e saldos

Tipos: recebimento, transferência saída/entrada, consumo, retorno, desperdício, devolução ao fornecedor, ajuste +/−, reversão, abertura.

Reserva e separação **não** geram movimento físico.

Cada movimento registra item, lote, locais, quantidade informada e canônica, sinal, origem, ator, datas, correlação, política, motivo e hash.

Erro se corrige por reversão ou lançamento compensatório. Concorrência: `SELECT FOR UPDATE` no saldo. Sem `float`.
