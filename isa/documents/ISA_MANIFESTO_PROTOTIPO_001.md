# ISA — manifesto do protótipo 0.1.0

Baseline 1.0. Protótipo 0.2.0, em 16/10/2026. Proposta visual para aprovação. Não é produção e não está aprovada. Não altera a versão do ActionFinance, que permanece 0.2.10.

## Como abrir

Na pasta `isa/prototype`:

```powershell
python -m http.server 8097
```

Abrir `http://127.0.0.1:8097/`. Entrar como Marina Alves ou Paulo Nunes. Não há senha. Os dados ficam no navegador e somem ao fechar a aba.

Durante esta revisão o mesmo endereço estava no ar em 127.0.0.1:8097.

## Arquivos

| Arquivo | Função |
| --- | --- |
| `isa/VERSION` | `isa-prototipo 0.1.0`, baseline 1.0 |
| `isa/prototype/index.html` | Página única |
| `isa/prototype/styles.css` | Visual próprio, sem a faixa azul do Finance |
| `isa/prototype/app.js` | Jornada de demonstração |
| `isa/prototype/calc.js` | Resultado do mês |
| `isa/prototype/calc.test.mjs` | Casos sintéticos do cálculo |
| `isa/prototype/bb-statement.js` | Leitor do extrato do Banco do Brasil |
| `isa/prototype/bb-statement.test.mjs` | Testes sintéticos do perfil |
| `isa/prototype/validate-bb-local.mjs` | Contagens do CSV real, sem imprimir linhas |
| `isa/prototype/fixtures/bb-extrato-sintetico.csv` | Extrato inventado, mesma estrutura |
| `isa/prototype/fixtures/bb-extrato-sintetico-sobreposicao.csv` | Segundo exemplo, com linhas sobrepostas |
| `isa/documents/ISA_EXTRATO_BB_002.md` | Perfil conferido, sem valores pessoais |
| `isa/documents/ISA_PROJETO_MVP_001.md` | Limites, modelo, isolamento, leitura e preços |
| `isa/documents/ISA_PLANO_IMPLEMENTACAO_001.md` | Fatias, testes, publicação e recuperação |
| `isa/documents/prototipo/` | Capturas e `jornada.json` |

## O que a jornada fez

No Edge, em 390 px de largura:

- mês vazio, sem valor fictício;
- gasto digitado, conferido e gravado; a categoria foi de Transporte para Saúde no mesmo lançamento;
- salário recebido de R$ 2.500,00, aula a receber de R$ 400,00 e transferência de R$ 500,00;
- resultado de outubro: R$ 2.472,10 (2.500,00 − 27,90). A receber, a pagar e a transferência ficaram fora dessa conta;
- leitura simulada da padaria, campo corrigido, gravada uma vez como a pagar (R$ 42,80);
- segunda foto do mesmo documento abriu o lançamento existente;
- leitura parcial com campo vazio não gravou;
- a câmera do navegador de teste não autorizou a captura. Galeria e digitação continuaram na tela. Isso não prova a câmera de um celular;
- Paulo Nunes não viu os lançamentos de Marina.

Larguras medidas sem rolagem horizontal da página: 360, 390, 768 e 1280. Em 360 o texto foi ampliado. O último lançamento, rolado até o fim, ficou acima do menu. O foco no estabelecimento não ficou embaixo do menu.

Não houve teclado virtual nesta prova: o Edge usado é de mesa. O que se conferiu foi o foco e a área do menu.

## Capturas para a aprovação

- `390-inicio-vazio.png` — mês sem lançamento
- `390-inicio.png` — recebidos, pagos, resultado, a receber e a pagar
- `390-inicio-grafico.png` — categorias e últimos lançamentos
- `390-lista.png` — o que forma o resultado, com texto longo
- `390-duplicata.png` — possível duplicata
- `390-parcial.png` — leitura parcial e campo por conferir
- `390-camera-negada.png` — câmera não autorizada
- `360-inicio.png`, `768-inicio.png`, `1280-inicio.png`, `1280-conferir.png`
- `390-importar.png` e `390-importar-conta.png` — prévia sintética do extrato e a pergunta da conta

## A tesouraria empresarial

Esta frente só acrescentou a pasta `isa/`, ainda sem commit. Não houve edição de banco, migração, autenticação, deploy ou interface do ActionFinance. O working tree do Finance já tinha outras alterações de frentes anteriores; elas não foram incorporadas aqui e a versão publicada não foi incrementada.
