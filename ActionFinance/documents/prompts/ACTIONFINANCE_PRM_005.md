# ACTIONFINANCE_PRM_005 — Identidade visual e consistência da interface

Versão 0.1 — 29/09/2026. Desenho de UX do analista para implementação pelo Cursor.

## 1. Objetivo

Aplicar a identidade Action Finance às telas funcionais já entregues em C:\Projetos\ActionFinance. A interface deve ter **azul como base, prioridade à marca amarela, tonalidades coerentes e área de trabalho clara**. Entregar layout utilizável em desktop/mobile, componentes consistentes e hierarquia financeira legível. Não produzir apenas uma landing page, protótipo estático ou alteração de cores isolada.

PRM_003 e PRM_004 estão aprovados para demonstração local. Preservar regras, dados, contratos, permissões, idempotência, recuperação de falhas e saldo/baixa/estorno. Esta é uma entrega de apresentação, sem novas funcionalidades financeiras, integrações, IAM ou dashboard inventado. ActionFinance é produto autônomo/integrável; linguagem da interface deve servir também a empresas fora do grupo/padaria.

Sem mudanças em Spider/Hub/Panne, configurações globais, migrations aplicadas, volumes ou dados. Sem commit/push/deploy, produção/piloto. Não iniciar PRM_006. Ler instruções locais aplicáveis e documentos UX/DOM/DAT antes de implementar; preservar alterações existentes.

## 2. Fontes exatas e rastreabilidade

Pasta de entregáveis do analista:

`C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs`

Copiar, se ausentes no repositório, ACTIONFINANCE_REV_004_PARECER_ANALISTA.md e ACTIONFINANCE_REV_004_ENCERRAMENTO_ANALISTA.md dessa pasta para documents/reviews. Preservar conteúdo/autoria; não substituir relatório do executor por parecer. O parecer inicial não estava no repositório: não inventar sua presença anterior. Atualizar índice com o encerramento.

**Logos aprovadas são as versões compactas abaixo**, apesar do sufixo histórico “previa”. Não são os originais quadrados de frontend/images/action finance logos.

| Fonte dentro de outputs/logos-compactas | Dimensões intrínsecas | SHA256 |
| --- | --- | --- |
| logoamarelo-previa.png | 2098 × 749 | 332179CEB05EFB12B6DB5523D631D787319428FF511D5C97776C4A9F5E8BA1EB |
| logoazul-previa.png | 2127 × 739 | AE022ADB1D554D8188849EBA1D8674D57B3804E0F2C8A349823AD490D02AC0EC |
| logobranco-previa.png | 1254 × 1254 | A29779E088E171BCA42D80BE75199E55A1A2688DC53DE177320C1396EB2AF477 |

Copiar bytes intactos para frontend/src/assets/brand/ com nomes actionfinance-yellow.png, actionfinance-blue.png e actionfinance-white.png. Conferir hashes antes/depois. Não usar image generation, recortar, retirar fundo, recolorir, redesenhar, esticar ou recomprimir. Preservar originais de ambas as pastas. Importar como assets do build, sem dependência de caminho C:\ na aplicação.

Preservar dimensões do arquivo; a dimensão de exibição pode diminuir proporcionalmente com width e height:auto, sem object-fit:cover. Manter todo o conteúdo, incluindo CAPITAL. Não inventar monograma AF/favicon nem usar texto renderizado por fonte como substituição da logo. Se os arquivos exatos estiverem inacessíveis, informar esse bloqueio pontual; não regenerar marca aproximada.

## 3. Sistema de cores e tipografia

Tokens de interface propostos pelo analista (não alegar que são valores extraídos da imagem):

| Token | Valor | Uso |
| --- | --- | --- |
| brand-navy | #14143D | Sidebar e estrutura da marca |
| brand-blue | #24219B | Seleção, links e ações secundárias fortes |
| brand-blue-hover | #1C197E | Hover dessas ações |
| brand-gold | #FFE366 | Ação principal e destaque de marca |
| brand-gold-hover | #F4D34F | Hover da ação principal |
| canvas | #F3F5FB | Fundo da área de trabalho |
| surface | #FFFFFF | Tabelas, formulários, diálogos |
| text | #18243A | Texto principal |
| text-muted | #526078 | Texto secundário |
| border | #D7DEEA | Divisórias e controles |
| selection | #EAEAFE | Item/contexto selecionado em área clara |
| success | #166534 | Conclusão comprovada |
| warning | #854D0E | Atenção, com fundo claro e texto/ícone |
| danger | #B42318 | Erro/ação crítica |

Implementar como CSS custom properties centralizadas, sem valores de marca espalhados. Amarelo com texto navy; nunca texto branco em botão amarelo. Azul profundo com texto branco. Gold é marca/ação, não estado de vencimento. Vencido usa ícone/label e warning; recebido/pago comprovado pode usar success. Não depender só de cor.

Verificar contraste calculado nos estados reais: texto comum ≥4,5:1; texto grande ≥3:1; borda/foco de controle onde necessários ≥3:1 em relação ao entorno. Ajustar tokens de interface se necessário sem editar imagens aprovadas. Reportar combinações verificadas, não declarar certificação geral de acessibilidade.

Fonte de sistema: Segoe UI, system-ui, sans-serif. Marca conserva sua própria tipografia. Corpo 16 px; auxiliar 14 px; título de página 26 px desktop/22 px mobile; valores de resumo 24–28 px. Valores com tabular-nums. Sem fontes remotas. Espaçamento em escala 4/8/12/16/24/32 px. Bordas 1 px, raio 8 px em controles e 12 px em superfícies; sombras discretas apenas em elementos sobrepostos. Sem gradientes decorativos ou números animados.

## 4–8

Conforme o prompt integral recebido pelo Cursor nesta sessão: estrutura de navegação desktop/tablet/mobile, padrões das telas, logos alternativas, componentes, verificação e entrega. Parar após a entrega, sem PRM_006.
