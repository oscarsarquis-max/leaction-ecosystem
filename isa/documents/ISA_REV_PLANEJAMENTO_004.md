# ISA — relato do planejamento local

Data: 16/10/2026. Protótipo **0.5.0**. Baseline proposta **1.2**. Não publicada, não aceita e sem commit.

Os documentos dos Prompts 001, 002, 002A e 003 permanecem. O leitor do Banco do Brasil, a separação entre movimento e saldo, a fila de correspondências e a contagem única de fatos vinculados continuam. O ActionFinance permanece na versão 0.2.10.

## Quatro respostas separadas

**Persistência local:** implementada. SQLite em `C:\Projetos\isa\data\lab\isa.sqlite`, arquivos sintéticos em `data\lab\files` e cópias em `data\backups`. Essas pastas estão no `.gitignore` da ISA. A migração é a versão 1 de `schema_migration`.

**Identidade real:** pendente. Não há diretório próprio da ISA. O laboratório reconhece só Marina e Paulo pelo cabeçalho `X-ISA-Lab-Person` quando `ISA_ENV=lab`. Com `ISA_ENV=production` a mesma chamada recebe 403. Isso não é cadastro nem autenticação produtiva. A aplicação não guarda senha e não usa o pool empresarial.

**Planejamento:** funcional no laboratório. A pessoa informa a disponibilidade com data, a próxima entrada e os compromissos, vê o dia da falta e compara uma data alternativa. O plano escolhido não altera o vencimento.

**Agentes:** simulados. Os textos saem de regras demonstrativas em `server/explain.py`. Nenhum provedor foi escolhido, contratado ou chamado. A sugestão gravada traz origem `regras-demonstrativas`, provedor vazio e a frase de que nenhum agente foi chamado.

## A decisão que a tela mostra

Com os valores fictícios e a data fixa 16/10/2026:

- disponível R$ 600,00, já contendo R$ 100,00 de reserva protegida;
- entrada confirmada de R$ 1.200,00 em 25/10/2026;
- compromissos de R$ 200,00 em 18/10, R$ 500,00 em 20/10 e R$ 300,00 em 28/10.

O disponível chega a **−R$ 100,00 em 20/10/2026**, no dia do compromisso de R$ 500,00. Outubro termina em **R$ 800,00**. O fim positivo não cobre o meio do caminho. Para manter também a reserva, faltam **R$ 200,00** no ponto mais baixo. A margem para um gasto adicional em 16/10 é **zero**.

Se somente esse compromisso de R$ 500,00 passar para 26/10, o ponto mais baixo fica em **R$ 400,00** e outubro continua em **R$ 800,00**. O custo do adiamento não foi informado e o credor não confirmou a data. A tela diz que não é renegociação concluída nem recomendação definitiva. Guardar como **Plano escolhido** deixa o vencimento original em 20/10/2026. Nada foi pago.

Um condomínio sintético de R$ 100,00 em 05/11 permanece no horizonte de novembro. Adiar para o mês seguinte não some com o compromisso.

Fontes do número: disponibilidade declarada, entrada com estado confirmada e os três compromissos de outubro, calculados por `isa-projecao-1`. A entrada incerta de exemplo fica de fora dessa trajetória.

## O que foi salvo e onde recuperar

A base ativa do laboratório é `C:\Projetos\isa\data\lab`. Ela guarda disponibilidade, entradas, compromissos, reserva, cenários, sugestões, eventos, rascunhos e arquivos ligados ao dono. Fechar o navegador não apaga o que o servidor confirmou. Trocar de aparelho só enxerga esses dados se alcançar esta mesma base local; não há serviço publicado.

Para subir de novo:

```powershell
cd C:\Projetos\isa
.\scripts\dev\start-isa.ps1
```

`http://127.0.0.1:8098` — entrar como Marina Alves é identidade de laboratório.

Cópia manual: `POST /api/backup` com um nome. O destino é `data\backups\<nome>`, separado da pasta ativa, com `isa.sqlite`, `files` e `manifest.json`. A restauração de prova usa `store.restore_dir` para um diretório vazio e aponta a leitura para essa cópia. Não substitui o arquivo ativo por cima.

Retenção marcada: `laboratorio-7-dias`. Uma cópia mais velha que sete dias é removida por `expire_backups`. Esquecer a pessoa apaga o ativo e conserva a cópia até esse prazo; restaurá-la devolveria os dados esquecidos. Não há promessa de guarda eterna. Cópia no mesmo disco não protege contra perda do equipamento. Antes de uso real, a cópia precisa de outro armazenamento. Nesta etapa a cópia é manual, então a perda máxima é o que mudou desde a última cópia.

O CSV real usado na validação privada do leitor não entrou nesta base, nem no Git, nem nas capturas. A carga de outubro do servidor é a fixture `cenario-sintetico-004` e não lê `sessionStorage`.

As telas de importação do protótipo 0.4.0 continuam gravando a demonstração no `sessionStorage` do navegador. Elas não foram copiadas automaticamente para o SQLite. A API `POST /api/imports` persiste lote, ocorrência e movimento quando é chamada, e o teste sintético cobre reenvio e sobreposição. Quem só usar aquelas telas antigas ainda depende da aba.

## Verificações

Motor, em `server`, 12 testes: trajetória canônica (−R$ 100,00 em 20/10 e R$ 800,00 no fim de outubro), adiamento para 26/10 (mínimo R$ 400,00), compromisso de novembro que permanece visível, entrada incerta fora da trajetória, base ausente sem virar zero, ordem no mesmo dia, reserva já contida na base, limite de crédito, saldo negativo, movimento já refletido no encerramento, gasto extra na data de referência e orçamento de categoria que não se soma ao teto global.

Servidor, 3 testes junto dos 12, todos ok em 16/10/2026 (`Ran 15 tests`):

- identidade desconhecida recebe 401; Paulo recebe 404 no identificador de Marina e uma projeção incompleta na própria casa;
- a fixture de outubro é idempotente; reenviar o mesmo lote não cria outro; a sobreposição importa só a linha nova e deixa uma pendência;
- duas confirmações concorrentes da mesma ocorrência deixam um estado e não duplicam o movimento;
- sugestão nasce `gerada`, passa a `apresentada` e pode ser `recusada`; outra, ainda apresentada, fica `desatualizada` quando uma entrada nova entra; a recusada permanece recusada; a correção cria revisão com `revision_of` e o conteúdo anterior fica; aceitar de novo devolve `repeated` e não muda a data do aluguel;
- rascunho de conferência aberta, compromissos, sugestões e anexo sobrevivem ao reinício do processo;
- a restauração num diretório vazio recupera compromissos, vínculos, sugestão recusada, revisão, SHA-256 do arquivo sintético e o rascunho;
- esquecer limpa o ativo e deixa a pasta da cópia; uma cópia de oito dias é expirada e a cópia recente permanece;
- `ISA_ENV=production` recusa a identidade de laboratório com 403.

Edição de uma parcela da série não muda a irmã. Vínculo confirmado reduz R$ 500,00 para R$ 300,00 uma vez. Repetir o vínculo não reduz de novo. Observação de saldo em 30/09 não completa a projeção.

No navegador, Edge headless, viewports 390×844 e 1280×800. Isso é emulação, não um aparelho físico. Não houve teclado virtual.

- Início sem base pergunta quanto há disponível e em qual data.
- Depois dos quatro compromissos, o dia 20 mostra **Falta**, −R$ 100,00 e a saída Aluguel R$ 500,00. Novembro continua no calendário. Sem rolagem horizontal da página.
- O Início mostra −R$ 100,00, a entrada de R$ 1.200,00 e os R$ 200,00 que faltam para a reserva.
- A comparação para 26/10 mostra mínimo R$ 400,00, fim de outubro R$ 800,00 e o custo ainda não informado. O plano escolhido mantém o aluguel em 20/10.
- **Posso gastar?** R$ 50,00 deixa a margem em zero e não inventa verba da categoria.
- Em 1280 px o calendário e a comparação ficam lado a lado. A legenda usa as palavras Falta, Entra e Sai além da cor.
- Recarregar a página recupera o plano escolhido e o aluguel.
- A jornada de importação do 0.4.0, em `http://127.0.0.1:8097`, foi repetida depois da navegação de quatro botões e terminou em `fechamento 003 ok`.

Capturas sintéticas: `documents/prototipo/390-planejar-pergunta.png`, `390-planejar-falta.png`, `390-inicio-decisao.png`, `1280-planejar-comparar.png`.

## Git

A raiz continua `C:\Projetos`. Não existe repositório dentro de `isa`. Não houve `git init` nem commit desta etapa. O diretório `isa/` segue não rastreado no monorepo. A candidata reproduzível é a lista de arquivos e hashes em `documents/ISA_CANDIDATA_004.txt`. Ela inclui só arquivos da ISA. Ficaram de fora `data/`, o SQLite, as cópias, `__pycache__` e qualquer extrato real.

Os arquivos sujos de outras frentes não foram alterados nesta entrega.

## Limitações que permanecem

A aprovação visual e a publicação continuam com o proprietário. Não há acesso real, câmera de aparelho, Open Finance, juros calculados, contratação de crédito nem agente de linguagem. A cópia local não substitui armazenamento fora desta máquina. As telas antigas de extrato ainda vivem na sessão do navegador até serem ligadas à API.
