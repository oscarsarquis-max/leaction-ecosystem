# Serviços Prodinx — Importação JSON



Serviço Flask de receção de dados e importação automatizada por pasta quente.



## Estrutura de pastas



| Pasta | Função |

|-------|--------|

| `../jsonfiles/` | Deposite aqui os novos ficheiros `.json` para importação |

| `../jsonfiles/processados/` | Ficheiros importados com sucesso (renomeados com timestamp) |

| `../jsonfiles/falhas/` | Ficheiros com JSON inválido ou erro de gravação |

| `importacao.log` | Registo local de sucessos e falhas (em `servicos/`) |



Caminho padrão: `C:\Projetos\prodinx\jsonfiles`



## Instalação



```bash

cd servicos

pip install -r requirements.txt

```



## Arranque com watcher automático



Ao iniciar a aplicação Flask, o observador de ficheiros é lançado automaticamente numa thread em segundo plano:



```bash

python app.py

```



O watcher:

1. Monitoriza `jsonfiles/` em tempo real

2. Processa ficheiros `.json` já existentes no arranque

3. Valida a estrutura básica do JSON (objeto com chave de métrica)

4. Grava na tabela `indicadores` (coluna `payload_completo` JSONB)

5. Move o ficheiro para `jsonfiles/processados/` ou `jsonfiles/falhas/`



Para desativar o watcher automático:



```bash

set DISABLE_JSON_WATCHER=1

python app.py

```



## Arranque manual do watcher (terminal paralelo)



Se preferir correr o observador separadamente da API Flask:



```bash

# Terminal 1 — API

python app.py



# Terminal 2 — Watcher

python watcher.py

```



Neste modo, defina `DISABLE_JSON_WATCHER=1` ao subir o Flask para evitar dois observadores em simultâneo.



## Formato esperado do JSON



```json

{

  "nome_metrica": "producao_diaria",

  "periodo": {

    "inicio": "2025-01-01",

    "fim": "2025-12-31"

  },

  "resumo": {

    "total_registos": 150,

    "volume_total": 12500,

    "score_medio": 87.5

  },

  "itens": [

    { "nome": "Linha A", "volume": 4200, "score": 91 }

  ]

}

```



As datas `periodo.inicio` e `periodo.fim` são extraídas para colunas relacionais (`DATE`) com índice, otimizando consultas de histórico de até 1 ano. O campo `data_importacao` é preenchido automaticamente no momento da inserção.



Chaves aceites para identificar a métrica: `nome_metrica`, `metrica`, `nome`, `name`, `metric_name`, `tipo`.



## Teste rápido



```powershell

copy exemplo.json C:\Projetos\prodinx\jsonfiles\

```



O ficheiro será processado automaticamente e movido para `jsonfiles/processados/`.


