# Ficha imprimível

Renderiza o payload canônico da emissão mais o envelope (`issue_number`, finalidade, estado na emissão, emissão anterior, hash).

Não altera o payload nem inventa produto, empresa, responsável, data ou alertas ausentes — esses campos aparecem como “não informado nesta emissão”.

CSS de impressão: A4, preto e branco, `.no-print` esconde menus e o botão Imprimir, cabeçalho repetido com marca e código, aviso se a emissão substitui outra ou se a ordem estava cancelada. Sem PDF no backend.
