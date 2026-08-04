# Arquitetura — inove4us School (B2B)

## O que é

**inove4us School** é uma aplicação **B2B independente**: interface própria, login próprio (Diretor / Coordenador), banco próprio e (em produção) subdomínio próprio (ex.: `school.inove4us.com.br`).

Não é um módulo dentro do app B2C dos professores (`inove4us/`). É uma **Torre de Controle** institucional.

```
┌─────────────────────────────────────────┐
│         inove4us School (B2B)           │
│  Gestores · Instituições · Diretrizes   │
│  DB: inove4us_school · tabelas school_* │
└──────────────────┬──────────────────────┘
                   │  contratos / API
                   │  (IDs + diretrizes)
                   ▼
┌─────────────────────────────────────────┐
│         inove4us (B2C professores)      │
│  Planejamento · Aulas · Kanban · PEI    │
│  DB: inove4us (inalterado por este app) │
└─────────────────────────────────────────┘
```

## Isolamento (regras duras)

1. **Código:** proibido importar pacotes, rotas ou componentes do `inove4us` B2C (e vice-versa).
2. **Dados:** banco `inove4us_school` separado. Prefixo `school_*` em todas as tabelas.
3. **Auth:** sessão/credencial de `school_gestores` não autentica o professor no B2C.
4. **FK cross-DB:** não existe. A ponte é lógica.

## Torre de Controle — responsabilidades

| Capacidade | Onde mora | O que faz |
|------------|-----------|-----------|
| Cadastro da escola | `school_instituicoes` | Razão social, CNPJ, domínio de e-mail, status |
| Login B2B | `school_gestores` | Diretor / Coordenador desta app |
| Quem é professor da escola | `school_professores_vinculo` | Liga `professor_b2c_id` ↔ instituição |
| Diretriz pedagógica | `school_editor_pedagogico` | Metodologia base + texto customizado |

A School **não** executa o ciclo de aula do professor. Ela **define e governa**; o B2C **opera**.

## Ponte com o B2C

- Coluna `school_professores_vinculo.professor_b2c_id` (UUID) é a **única ponte de identidade** no schema inicial.
- Sem FK para tabelas do banco `inove4us`. O mapeamento para `id_clie` / conta do professor acontece em **camada de integração** (API, webhook ou serviço de identidade do Hub), quando for implementada.
- Diretrizes ativas (`school_editor_pedagogico.is_active`) são **repassadas** ao B2C como payload de política — o B2C pode espelhar ou consultar; a fonte de verdade institucional é a School.

## Fronteiras com o ecossistema

- **Action Hub:** entitlements / billing institucional (futuro) — mesmo padrão das outras apps satélite.
- **inove4us B2C:** permanece produto do professor; mudanças só via liberação explícita e contrato de API.
- **CMS Nina / landing:** conteúdo público continua no Hub; School é área autenticada B2B.

## Evolução segura

1. Novas tabelas → sempre `school_*` neste banco.
2. Precisa de dado do professor → chamar API B2C ou Hub; não ler o DB B2C direto do processo School.
3. Precisa alterar o B2C → pedir liberação da app `inove4us` e manter o contrato versionado.

## Status do scaffold

- FE React (Vite `:5175`) + BE Flask (`:5012`)
- Migration `001_school_b2b_schema.sql`
- Health `/api/health` e meta `/api/meta`

Próximos passos naturais: auth de gestor, CRUD instituição, convite/vínculo de professor, publicação de diretriz para o B2C.
