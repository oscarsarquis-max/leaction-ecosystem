# SEGSENSE_UX_005 — Entrada pública de posicionamento `/`

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_UX_005 |
| Versão | 1.2 |
| Data | 14/09/2026 |
| Status | Implementado no PRM_012; composição COR_001; marca da home ampliada no PRM_018 |

## Antes / depois

| | Antes (PRM_011) | Depois (PRM_012) | COR_001 |
|---|---|---|---|
| `GET /` | React redirecionava para `/admin` | Página pública de posicionamento SegSense | Mesma rota; hero compacto, sem painel vazio |
| Identidade | Visitante via `/` via o backoffice | Roxo/lilás/branco, logo oficial, narrativa de produto | Logo da home menor; convite `/c/{token}` inalterado. **PRM_018:** home volta a marca perceptível (80 px de altura visível em 1440; posição inalterada), sem ser a escala do convite |
| Icatu | Só em `/demonstracao/icatu`, invisível na raiz | Link visível; **não** é a home | Link permanece; cenário não oficial |
| PWA / service worker | Ausente (`index.html` sem SW) | Ausente; causa do “não vi a âncora” = rota, não cache | Descoberta também a partir de `/admin/demonstracoes` 401 |

## Wireframe

1. Hero compacto (uma coluna): o que é o SegSense; ganho de hoje; CTA “Ver o que já opera”; link para demonstração Icatu não oficial; dois blocos úteis **Hoje** / **Depois de contratos**.
2. Três capacidades: hoje / hoje / depois de contratos.
3. Cooperação (papéis positivos), contratos pendentes, co-desenvolvimento de produto novo.
4. Seção técnica secundária: independência do SegSense, ausência de Satellite Contract e de integração.

Admin autenticado e `/c/{token}` inalterados. Sem dados editoriais administrativos na home. Sem ilustração de apólice, métrica fictícia ou integração fingida.

## Descoberta a partir do admin (COR_001)

Quando `/admin/demonstracoes` exibe o bloqueio de autenticação, há links públicos nomeados para `/` e `/demonstracao/icatu`. Não há tela de login nem liberação do backoffice.
