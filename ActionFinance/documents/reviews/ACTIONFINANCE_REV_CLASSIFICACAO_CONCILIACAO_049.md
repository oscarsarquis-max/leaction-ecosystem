# Classificação e conciliação — Prompt 049

Data: 16/10/2026. Publicado junto com o 050 na candidata 0.2.8. Aceite não atribuído. O fechamento conjunto está em [REV_051](ACTIONFINANCE_REV_FECHAMENTO_049_050_051.md).

A unidade classificada é o evento consolidado do extrato. A ocorrência documental repetida continua no lote e não vira outro evento. Categoria, iniciativa e situação de conferência são eixos separados. A referência comercial não baixa título e não entra na soma do livro. Conciliado exige que o líquido do evento e os movimentos usados fechem, nos dois lados. Rateio em centavos, com resíduo na maior participação.

A migration V24 foi aplicada no origin antes da imagem dependente, saindo de V23. O site não liga o Flyway. A imagem anterior 0.2.7 continuou respondendo versão, saúde e 401 depois do schema novo.

A prova financeira do 049 está em `ClassificationIT` e `AllocationMathTest`, no Postgres isolado. A jornada visual de classificar, ratear, conciliar e desfazer não foi percorrida no navegador nesta entrega.
