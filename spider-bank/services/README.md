# services

O cliente SAT-003 desta fatia vive no BFF (`backend/`), não neste diretório e não no frontend.

- Endpoint: `POST /v1/satellites/interactions`
- Contrato: `1.0`
- Identidade: `spiderbank`
- Finalidade: `WORKING_CAPITAL_ASSESSMENT`

O frontend nunca recebe o segredo do satélite. Este diretório não contém conectores para `mock-sistemas-credito` nem para a porta `8096`. O BFF também não despacha o provider: a Spider resolve e chama o mock.
