# Workflow Git — LeAction Ecosystem (Monorepo)

Este documento define como sincronizar o código entre **dois computadores** via GitHub (`oscarsarquiis`) e como manter um **log de auditoria** adequado ao Go-Live.

## Estrutura do monorepo

Raiz: `C:\Projetos`

| Pasta | Produto / papel |
|-------|-----------------|
| `PanelDX/` | PanelDX (Flask + Node BFF) |
| `leaction-platform/` | ActionHub (gateway-api, action-hub, backend) |
| `chamelleon/` | Chamelleon Hub (Flask + Vite) |
| `apps/` | Spokes (ex.: Diário de Obra) |
| `prodinx/` | Prodinx (legado — tinha `.git` próprio) |
| Outras (`MAtivas`, `LASim`, …) | Projetos no mesmo workspace |

**Remoto sugerido:** `https://github.com/oscarsarquiis/leaction-ecosystem.git`

---

## Pré-requisitos (uma vez por máquina)

1. [Git for Windows](https://git-scm.com/download/win) instalado.
2. Conta GitHub `oscarsarquiis` com repositório vazio criado (sem README, se for o primeiro push).
3. Autenticação: Personal Access Token (HTTPS) ou SSH configurado no GitHub.

### Atenção: repositório aninhado em `prodinx/`

`prodinx/` já possuía um `.git` interno. Antes do **primeiro commit** do monorepo, escolha uma opção:

- **Monorepo único (recomendado):** remover o Git interno e versionar tudo na raiz:
  ```powershell
  Remove-Item -Recurse -Force C:\Projetos\prodinx\.git
  ```
- **Submodule:** manter histórico separado (avançado; só se você souber gerenciar submodules).

---

## Workflow diário de sincronização

### Ao **iniciar** o dia (sempre antes de codar)

```powershell
cd C:\Projetos
git status
git pull origin main
```

Se houver conflitos, resolva localmente, depois `git add` + `git commit` + `git push`.

### Durante o trabalho

- Commits **pequenos e frequentes**, por área lógica (ex.: só PanelDX, só ActionHub).
- **Nunca** `git add .env` ou pastas `Chaves/` — o `.gitignore` da raiz bloqueia, mas confira com `git status` antes de commitar.

### Ao **terminar** o dia (ou ao trocar de máquina)

```powershell
cd C:\Projetos
git status
git add .
git status
# Confirme que NÃO há .env, node_modules, venv, Chaves/, etc.
git commit -m "feat(paneldx): descrição objetiva do que mudou"
git push origin main
```

Na outra máquina: apenas `git pull origin main`.

---

## Branches (Go-Live)

| Branch | Uso |
|--------|-----|
| `main` | Código estável / pré-produção e produção |
| `develop` | Integração contínua (opcional) |
| `feat/nome-curto` | Features isoladas; merge em `main` via PR |

Para lançamento, prefira **Pull Request** no GitHub com revisão, mesmo sendo equipe pequena — o histórico vira auditoria.

---

## Conventional Commits (auditoria Go-Live)

Formato:

```
<tipo>(<escopo opcional>): <descrição curta no imperativo>

[corpo opcional — o que e por quê]

[rodapé opcional — BREAKING CHANGE:, refs #issue]
```

### Tipos principais

| Tipo | Quando usar | Exemplo |
|------|-------------|---------|
| `feat` | Nova funcionalidade | `feat(actionhub): checkout sandbox Mercado Pago` |
| `fix` | Correção de bug | `fix(paneldx): webhook pagamento retorna 500` |
| `refactor` | Mudança interna sem alterar comportamento | `refactor(chamelleon): extrair TdPlanManager` |
| `chore` | Tarefas de manutenção, deps, CI, gitignore | `chore: atualizar .gitignore do monorepo` |
| `docs` | Só documentação | `docs: workflow git go-live` |
| `test` | Testes | `test(paneldx): e2e presurvey vitrine` |
| `perf` | Performance | `perf(chamelleon): cache journey flags` |

### Escopos sugeridos (monorepo)

`paneldx`, `actionhub`, `chamelleon`, `diario-obra`, `prodinx`, `deploy`, `infra`

### Boas práticas

- Imperativo: **"adicionar"**, não "adicionado".
- Uma intenção por commit quando possível.
- **PanelDX perto do Go-Live:** commits em `paneldx` só com sua autorização explícita; use mensagens claras para auditoria.

### Exemplos válidos

```
chore: initial commit do monorepo leaction-ecosystem
feat(paneldx): integração checkout ActionHub com handoff JWT
fix(actionhub): gateway 4001 — webhook PanelDX com URL Flask correta
refactor(chamelleon): área operacional na sidebar
docs: git workflow e conventional commits
```

---

## Checklist antes de cada push (Go-Live)

- [ ] `git status` — sem arquivos `.env`, `*.pem`, `Chaves/`
- [ ] Build/teste mínimo do módulo alterado
- [ ] Mensagem no padrão Conventional Commits
- [ ] `git pull` feito no início do dia (evitar push rejeitado)

---

## Comandos úteis

```powershell
# Ver o que será commitado
git diff --stat
git diff --cached --stat

# Desfazer stage de arquivo sensível (se adicionado por engano)
git reset HEAD -- caminho/do/arquivo.env

# Histórico de auditoria
git log --oneline -20
git log --oneline -- PanelDX/
```

---

## Suporte

Dúvidas sobre o remoto ou primeiro push: use o bloco de inicialização fornecido no chat após a criação deste repositório.
