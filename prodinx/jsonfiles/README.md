# Pasta de importação JSON — Prodinx

Deposite os ficheiros `.json` nesta pasta para importação automática pelo serviço Flask.

## Estrutura

```
jsonfiles/
├── *.json              # Novos ficheiros a importar
├── processados/        # Importados com sucesso (com timestamp no nome)
└── falhas/             # JSON inválido ou erro de gravação
```

## Caminho padrão

`C:\Projetos\prodinx\jsonfiles`

Configurável via variável de ambiente `JSON_IMPORT_DIR`.

## Como funciona

1. Coloque o ficheiro `.json` diretamente em `jsonfiles/`
2. O watcher deteta o ficheiro e valida a estrutura
3. Os dados são gravados na base PostgreSQL (`indicadores`)
4. O ficheiro é movido para `processados/` ou `falhas/`

## Exemplo

```powershell
copy C:\caminho\indicador.json C:\Projetos\prodinx\jsonfiles\
```
