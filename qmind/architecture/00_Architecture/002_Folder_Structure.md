# QMind — Estrutura de Pastas

## Estrutura documental atual

```text
qmind/
├── README.md
├── roadmap.md
├── 00_Architecture/
│   ├── 000_Project_Vision.md
│   ├── 001_System_Architecture.md
│   ├── 002_Folder_Structure.md
│   └── 003_Documentation_Standards.md
├── 01_Prompts/
│   └── README.md
├── 02_Models/
│   └── README.md
├── 03_Database/
│   └── README.md
├── 04_Docs/
│   └── 004_Initial_Backlog.md
├── 05_ADR/
│   ├── README.md
│   └── ADR-000-template.md
└── 99_Reference/
    └── README.md
```

## Convenções

- Documentos fundacionais usam prefixo numérico de três dígitos.
- ADRs usam `ADR-NNN-titulo-curto.md`.
- Nomes de arquivos permanecem estáveis após serem referenciados.
- Conteúdo em Markdown deve possuir título, finalidade e status quando aplicável.
- Materiais temporários não devem ser misturados à documentação aprovada.
- Textos normativos protegidos só podem ser armazenados quando houver licença.

## Evolução para código

Quando a implementação começar, a estrutura do código será definida por ADR. Uma opção inicial é adicionar diretórios independentes para aplicações, módulos compartilhados, infraestrutura e testes sem alterar a organização documental existente.

