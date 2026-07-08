# Repositório do logotipo — Metodologias Inov-ativas

Esta pasta guarda o **arquivo de imagem** exibido no topo das páginas (componente `Brand`).

## Como trocar o logotipo

### Opção A — Substituir o arquivo local (recomendado)

1. Prepare sua imagem:
   - **Formato:** PNG ou SVG (PNG com fundo transparente é o mais comum)
   - **Largura sugerida:** 240–400 px
   - **Proporção:** horizontal (paisagem), legível em telas mobile

2. Copie o arquivo para esta pasta com um destes nomes:
   - `logo.png` — padrão preferido
   - `logo.svg` — alternativa vetorial

3. Caminho no projeto:

   ```
   frontend/public/brand/logo.png
   ```

4. Recarregue o navegador (`http://localhost:5173`). Em desenvolvimento, não é preciso rebuild.

5. **Produção:** após trocar a imagem, gere o frontend novamente (`npm run build`) e faça deploy.

### Opção B — URL externa (painel admin)

1. Acesse **Painel Administrativo** → aba **Conteúdo da Interface**
2. Em **Imagens (URL)**, edite a chave `assets.logo`
3. Informe a URL pública da imagem (ex.: `https://seusite.com/imagens/logo.png`)
4. Salve — a interface atualiza em até 30 segundos

Se a URL do admin estiver preenchida, ela **tem prioridade** sobre o arquivo desta pasta.

## Arquivos nesta pasta

| Arquivo      | Função                                      |
|--------------|---------------------------------------------|
| `logo.svg`   | Placeholder padrão até você enviar o logo   |
| `logo.png`   | Coloque aqui o logotipo definitivo (você)   |
| `README.md`  | Este guia                                   |

## Onde o logotipo aparece

- Barra superior de todas as páginas (`TopBar`)
- Cabeçalho do painel administrativo

## Dica

Mantenha apenas **um** arquivo ativo (`logo.png` ou `logo.svg`). Se usar PNG, pode remover o `logo.svg` placeholder após a troca.
