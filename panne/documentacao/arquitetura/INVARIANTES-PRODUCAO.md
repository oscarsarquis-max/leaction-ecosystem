# Invariantes de produção

1. A ordem liberada usa versão **aprovada** da formulação.
2. A escala é determinística e reconstruível (motor existente + inputs no snapshot).
3. Quantidades liberadas formam snapshot imutável.
4. Mudanças posteriores na formulação viva não alteram ordens históricas.
5. Planejado e realizado são entidades distintas.
6. Consumo real não sobrescreve o planejado.
7. Eventos críticos são append-only.
8. Transições de estado são validadas (máquinas em `ESTADOS-PRODUCAO.md`).
9. Cancelamento e reabertura preservam motivo e histórico; reabrir não apaga.
10. Digital e impresso derivam da mesma ordem e do mesmo snapshot.
11. Códigos de ordem, versão (hash) e batelada são inequívocos na ficha e no quadro.
12. Relatórios são projeções, não cadastros.
13. Cálculo de escala não depende de IA.
14. IA não libera, conclui ou cancela ordens.
15. Dados organizacionais nascem com RLS (mesmo padrão 0009).
16. Custos e margens não aparecem ao padeiro por padrão.
