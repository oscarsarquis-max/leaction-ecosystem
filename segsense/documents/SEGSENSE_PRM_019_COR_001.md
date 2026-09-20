# SEGSENSE_PRM_019_COR_001 — Correção única da apresentação pública e fechamento dos gates

## Controle

- Projeto: SegSense. Versão 1.0. Data: 15/09/2026.
- Corretivo único de `SEGSENSE_PRM_019`. Não emitir segundo corretivo e não iniciar `SEGSENSE_PRM_020`.
- O PRM_019 comprovou na stack isolada a jornada real contexto → intenção livre → perguntas faltantes → Spider → Provider Mock → prêmio simulado. A auditoria humana em navegador confirmou o fluxo “incêndios próximos” + “Quero contratar um seguro residencial” + apartamento + R$ 300.000 + 12 meses → **R$ 540,00**.
- O corretivo não muda a arquitetura: SegSense, Spider e Insurance Provider Mock permanecem aplicações independentes; SegSense não chama o mock; Spider escolhe a capability; o mock calcula; não há produto/API/contrato Icatu.
- Alterações somente em `segsense/`, `spider/` e `segsense-provider-mock/` quando indispensáveis ao corretivo. Não tocar Experience Hub, Panne ou demais produtos. Não fazer commit, push ou deploy. Documentos novos originados daqui usam prefixo `SEGSENSE_`.

## Motivo do corretivo

A funcionalidade central está aprovada em conceito e foi observada no runtime. Há, porém, um desvio na linguagem pública: dentro de **Como este valor foi calculado**, a tela mostra `18 bps`, `APARTMENT`, `30000000 centavos` e `54000 centavos`. Esses são detalhes internos do motor demonstrativo. Eles contradizem a diretriz do PRM_019 de manter códigos e versões nos detalhes técnicos e dificultam a apresentação a pessoas de negócio.

Também faltou o fechamento formal dos gates completos: o encerramento do PRM_019 não reexecutou `mvnw verify` completo do SegSense nem a suíte ampla pertinente da Spider.

## Prompt para o Cursor

Faça apenas a correção abaixo, preservando integralmente o cálculo, os contratos versionados, a provenance, a idempotência, a separação das aplicações, V1–V16 e o resultado observado de R$ 540,00. Antes de editar, leia `SEGSENSE_PRM_019`, `SEGSENSE_FUN_004`, `SEGSENSE_ADR_007`, `SEGSENSE_REV_019` e a implementação efetiva da jornada.

### 1. Tornar a explicação pública compreensível

Na superfície pública, substitua a exposição direta de códigos e unidades internas por uma explicação humana derivada dos mesmos dados reais do provider. Para o caso auditado, a pessoa deve compreender algo equivalente a:

> O simulador considerou o valor de proteção de R$ 300.000,00, o tipo de imóvel apartamento e o período de 12 meses. Aplicou a regra demonstrativa vigente para esse cenário e calculou um prêmio anual simulado de R$ 540,00.

Não fixe essa frase ou esses números no frontend: derive tipo, capital, período e prêmio da resposta persistida da tentativa. Não invente cobertura, risco, taxa de mercado, franquia ou benefício. Mantenha claramente visível que a regra é fictícia, não calibrada ao mercado e que incêndios próximos não alteraram o prêmio.

Remova da camada pública os termos `bps`, `APARTMENT`, centavos brutos, nomes de enum, `scenarioKey`, `capability`, `Test Double`, versões de contrato e IDs. Quando úteis para auditoria, coloque-os somente em **Detalhes técnicos desta tentativa**, com rótulos adequados. O valor em reais, o capital, o período e o tipo de imóvel são informações de negócio e continuam visíveis.

Preserve o cabeçalho já correto: **SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO**. Preserve “Cotação simulada”, mas certifique-se de que o bloco deixe claro, sem repetição excessiva, que é resultado de um simulador independente e não cotação emitida por seguradora.

### 2. Ajustar a hierarquia dos estados

Quando a Spider responder `MISSING_CONTEXT`, mostre prioritariamente as perguntas que faltam. Não renderize abaixo delas seções vazias ou deslocadas como “Possibilidades ilustrativas”, “Por que surgiram” ou “Nenhuma pendência humana veio nesta resposta”. Essas seções pertencem à jornada antiga de possibilidades ou a respostas que efetivamente tragam esse conteúdo.

Quando houver cotação concluída, apresente nesta ordem: resultado e período; dados usados; explicação humana do cálculo; limites da simulação; detalhes técnicos recolhidos. Nada deve aparecer como fato antes de existir na resposta/persistência desta tentativa. Alterar um campo deve invalidar visualmente o resultado anterior, como já ocorre.

Não redesenhe a página inteira. Preserve logo ampliado, posições, paleta roxo/lilás/branco, intenção livre, perguntas progressivas, responsividade, navegação e a jornada antiga compatível.

### 3. Provas funcionais e visuais

Na stack isolada vigente, repita por HTTP real e navegador:

1. fonte governada “incêndios próximos”;
2. intenção “Quero contratar um seguro residencial”;
3. primeiro envio → `MISSING_CONTEXT`, sem chamada ao provider e sem seções vazias;
4. apartamento, R$ 300.000, 12 meses;
5. segundo envio → R$ 540,00, exatamente o valor calculado pelo mock;
6. explicação pública sem os termos técnicos proibidos;
7. detalhes técnicos contendo, quando necessário, regra/taxa/unidades internas e IDs reais;
8. mudança material invalida resultado anterior; replay idêntico preserva resultado/referência;
9. provider indisponível não exibe prêmio anterior ou fallback;
10. jornada antiga de possibilidades permanece funcionando e SegSense continua sem chamar o mock.

Inspecione 1440×900, 768×1024, 390×844, 320×568, zoom 200%, teclado/foco e impressão. Não autorize microfone; ditado real continua `NÃO VERIFICADO` se não houver autorização expressa. Guarde evidências sob `documents/evidencias/SEGSENSE_PRM_019_COR_001/` sem segredos ou dados pessoais.

### 4. Gates completos obrigatórios

Execute e reporte, sem omitir falhas anteriores:

- frontend: instalação reproduzível, lint, todos os testes e build;
- SegSense backend: `mvnw verify` completo, com variáveis da stack isolada removidas quando contaminarem testes gerais;
- Spider: suíte ampla pertinente ao Satellite Contract, capability/provider dispatch e compatibilidade 1.0/1.1, não apenas um teste focado;
- mock: todos os testes, incluindo golden tests do prêmio;
- Flyway: validate e aplicação V1–V16 em banco vazio; no volume isolado existente, confirmar V16 sem reescrever migration;
- preflight, ACL/segredos e prova de que logs e respostas públicas não vazam segredo;
- `git diff`/status por aplicação, distinguindo rigorosamente este corretivo da sujeira alheia do Experience Hub.

Não modifique a fórmula para fazer o teste passar e não crie migration nova sem necessidade material. Se um gate amplo falhar por defeito real, corrija somente dentro do escopo e documente a causa. Se falhar por ambiente, prove e registre a condição de forma reproduzível.

### 5. Documentação e devolutiva

Crie `SEGSENSE_PRM_019_COR_001.md` como cópia integral deste prompt e atualize `SEGSENSE_REV_019` para v1.1, `SEGSENSE_DEMO_RUN_001`, `SEGSENSE_JRN_EVID_001`, `SEGSENSE_UI_001`, `SEGSENSE_PLN_001` e índices pertinentes. Registre explicitamente:

- funcionalidade central observada no navegador;
- diferença entre texto público e detalhes técnicos;
- origem de cada número mostrado;
- frase pública antes → depois;
- matriz de estados `MISSING_CONTEXT`, `COMPLETED`, provider indisponível e replay;
- resultados completos dos gates;
- URLs e processos da stack nova e preservação da antiga;
- arquivos alterados por aplicação e estado Git.

Na devolutiva, comece pelo que uma pessoa de seguros verá e entenderá na tela; depois apresente evidências técnicas. **Pare para auditoria. Não autoaprove e não inicie PRM_020.** Não faça commit ou push neste corretivo.
