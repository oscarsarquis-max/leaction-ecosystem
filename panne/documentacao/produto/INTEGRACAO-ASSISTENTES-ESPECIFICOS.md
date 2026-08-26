# Integração dos assistentes específicos

O assistente global é o mentor e o roteador. Ingrediente, receita, IA de receita, rotulagem, custos, relatórios, reposição e inventário registram o fluxo em `setFlow` e abrem a mesma gaveta.

O cartão inline preserva progresso e título. Não há overlay concorrente (`mentor-inline` no fluxo, `drawer-assist` só na gaveta global). Voltar à orientação limpa o fluxo sem executar comando.
