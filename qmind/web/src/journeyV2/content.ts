import type { HotpageIconName } from "./iconNames";
import {
  JOURNEY_CHAPTER_IDS,
  type GuidedTourContextRequirement,
  type GuidedTourSpeakBlocks,
  type JourneyChapter,
  type JourneyChapterId,
  type ProductCapability,
} from "./types";

export { JOURNEY_CHAPTER_IDS };
export type { JourneyChapterId, JourneyChapter };

/** Capítulos canônicos — mesma ordem na hotpage e no tour autenticado. */
export const JOURNEY_V2_CHAPTERS: JourneyChapter[] = [
  {
    id: "understand",
    label: "Compreender",
    title: "Compreender a organização",
    situation:
      "A equipe precisa alinhar contexto, escopo e processos antes de avaliar.",
    organizes:
      "O QMind organiza o perfil da organização e o mapa do que será avaliado.",
    evidence:
      "Perfil, escopo e avaliações existentes permanecem vinculados à organização dona dos dados.",
    humanAction:
      "Pessoas autorizadas confirmam o contexto e escolhem por onde começar.",
    observableResult:
      "Visão compartilhada do que existe — sem inventar maturidade nem conformidade.",
    icon: "building",
  },
  {
    id: "assess",
    label: "Avaliar",
    title: "Avaliar e reunir evidências",
    situation:
      "Perguntas, campo e documentos costumam ficar dispersos entre planilhas.",
    organizes:
      "Avaliações guiadas, plano, campo e evidências ficam no mesmo percurso.",
    evidence:
      "Respostas e arquivos ligados a perguntas, com verificação e origem.",
    humanAction:
      "A equipe responde, anexa evidências e revisa o que ainda falta.",
    observableResult:
      "Material preparado para análise — sem certificação automática.",
    icon: "clipboard",
  },
  {
    id: "recognize",
    label: "Reconhecer",
    title: "Reconhecer um problema relevante",
    situation:
      "Um impacto operacional aparece, mas some em e-mails e reuniões.",
    organizes:
      "O impacto vira um Improvement Case rastreável, com problema e processo.",
    evidence: "Problema, impacto e processo relacionados ficam registrados.",
    humanAction:
      "Alguém autorizado formula o caso e decide priorizar o acompanhamento.",
    observableResult:
      "Um caso identificável — não uma fila anônima de “pendências”.",
    icon: "target",
  },
  {
    id: "analyze",
    label: "Analisar",
    title: "Analisar com apoio do QMind OI",
    situation:
      "Há fatos no Core, mas falta uma leitura estruturada para discutir.",
    organizes:
      "O Core envia contexto factual ao OI por contrato HTTP; o OI interpreta sem ler o banco do Core.",
    evidence:
      "Achados, limitações e bases ficam persistidos no Core com histórico.",
    humanAction:
      "Pessoas autorizadas validam, rejeitam ou aprofundam a interpretação.",
    observableResult:
      "Leitura explicável — o QMind orienta; humanos decidem o próximo passo.",
    icon: "search",
  },
  {
    id: "execute",
    label: "Executar",
    title: "Executar com squads, sprints e check-ins",
    situation:
      "Ações acordadas se perdem fora do ciclo de acompanhamento.",
    organizes:
      "Board, sprints, squads, cerimônias e check-ins concentram o trabalho.",
    evidence:
      "Status, impedimentos e check-ins ficam como fatos de execução.",
    humanAction:
      "Donos das ações avançam o trabalho e tornam bloqueios visíveis.",
    observableResult:
      "Execução acompanhável — progresso ≠ eficácia automática.",
    icon: "activity",
  },
  {
    id: "evidence_measure",
    label: "Medir",
    title: "Evidenciar e medir resultados",
    situation:
      "Sem baseline e indicador, “melhorou” fica só como opinião.",
    organizes:
      "Evidência contextual, indicador, meta e observações ficam ligados ao caso/ação.",
    evidence:
      "Leituras e posturas de meta são fatos locais e auditáveis.",
    humanAction:
      "A equipe registra medições e interpreta se a meta ajuda a decisão.",
    observableResult:
      "Meta atingida é um fato — não substitui a decisão de eficácia.",
    icon: "chart",
  },
  {
    id: "interpret",
    label: "Interpretar",
    title: "Interpretar a execução no QMind OI",
    situation:
      "Há muitos fatos de execução; falta uma leitura consolidada e limitada.",
    organizes:
      "Snapshot factual do Core → OI → sinais explicáveis e histórico no Core.",
    evidence:
      "Sinais citam fatos de suporte; limitações ficam visíveis.",
    humanAction:
      "Revisores leem os sinais e decidem se há atenção, não o sistema sozinho.",
    observableResult:
      "Interpretação versionada — sem chatbot genérico e sem mutar a operação.",
    icon: "sparkles",
  },
  {
    id: "control",
    label: "Controlar",
    title: "Controlar prioridades no Cockpit",
    situation:
      "Gestores precisam ver o que merece atenção agora, sem score opaco.",
    organizes:
      "O Cockpit consolida fatos, freshness e uma fila transparente de revisão.",
    evidence:
      "Faixas e motivos derivados de dados já existentes — sem fan-out OI.",
    humanAction:
      "A pessoa escolhe o que revisar; prioridade não é decisão automática.",
    observableResult:
      "Fila legível para humanos — não um ranking percentual de risco.",
    icon: "compass",
  },
  {
    id: "decide",
    label: "Decidir",
    title: "Decidir e aprender com participação humana",
    situation:
      "Sem fechamento consciente, o ciclo não vira aprendizado.",
    organizes:
      "Outcome, revisão humana e rastreabilidade fecham o laço no caso/Evolution.",
    evidence:
      "Decisões e observações permanecem ligadas ao histórico do caso.",
    humanAction:
      "Pessoas autorizadas registram o desfecho e o que aprendemos.",
    observableResult:
      "Aprendizado organizacional com origem — sem prometer resultado garantido.",
    icon: "userCheck",
  },
];

export const ILLUSTRATIVE_EXAMPLE_BADGE = "Exemplo ilustrativo";

export const ILLUSTRATIVE_EXAMPLE = {
  title: "Atrasos recorrentes no atendimento",
  subtitle:
    "Jornada fictícia e estática — nenhum dado de organização real é usado.",
  steps: [
    {
      id: "ex-delay",
      label: "Atrasos recorrentes",
      detail:
        "O time nota filas longas no atendimento, mas o problema ainda não está formalizado.",
    },
    {
      id: "ex-impact",
      label: "Impacto reconhecido",
      detail:
        "O impacto vira um caso: clientes aguardam além do combinado no processo de atendimento.",
    },
    {
      id: "ex-finding",
      label: "Achado analisado",
      detail:
        "A análise OI destaca fatos do contexto; a equipe valida o que faz sentido operar.",
    },
    {
      id: "ex-action",
      label: "Ação atribuída",
      detail:
        "Uma ação ganha dono, prazo e aparece no board — sem mutar dados reais nesta página.",
    },
    {
      id: "ex-block",
      label: "Impedimento visível",
      detail:
        "Um bloqueio de capacidade fica explícito no check-in, em vez de desaparecer no chat.",
    },
    {
      id: "ex-metric",
      label: "Indicador medido",
      detail:
        "Uma leitura do tempo de espera é registrada. Meta atingida, se ocorrer, ainda exige julgamento humano.",
    },
    {
      id: "ex-oi",
      label: "OI aponta atenção",
      detail:
        "Sinais citam fatos de suporte (ex.: impedimento aberto) — sem decidir sozinho.",
    },
    {
      id: "ex-cockpit",
      label: "Cockpit pede revisão",
      detail:
        "A fila do Cockpit direciona revisão humana. Prioridade não é score nem automação.",
    },
  ],
} as const;

export const PRODUCT_CAPABILITIES: ProductCapability[] = [
  {
    id: "cap-assess",
    name: "Avaliação e evidências",
    problem: "Contexto e arquivos espalhados atrasam a preparação.",
    productEvidence:
      "Wizard, plano, campo e evidências ligados a perguntas na avaliação.",
    humanLimit:
      "Pessoas respondem, verificam evidências e decidem o que entra no relatório.",
    chapterId: "assess",
    icon: "folder",
  },
  {
    id: "cap-case",
    name: "Improvement Case",
    problem: "Problemas relevantes somem em listas genéricas.",
    productEvidence:
      "Caso com problema, impacto, processo e status rastreáveis.",
    humanLimit: "Alguém autorizado formula e prioriza o caso.",
    chapterId: "recognize",
    icon: "target",
  },
  {
    id: "cap-exec",
    name: "Execução ágil",
    problem: "Ações acordadas não têm ritmo nem visibilidade.",
    productEvidence: "Board, sprints, squads, cerimônias e check-ins.",
    humanLimit: "Donos avançam o trabalho e registram impedimentos.",
    chapterId: "execute",
    icon: "activity",
  },
  {
    id: "cap-measure",
    name: "Medição do resultado",
    problem: "Sem indicador, melhora vira opinião.",
    productEvidence: "Indicadores, leituras, metas e posturas no Core.",
    humanLimit:
      "Meta atingida não equivale automaticamente a eficácia — humanos concluem.",
    chapterId: "evidence_measure",
    icon: "chart",
  },
  {
    id: "cap-ei",
    name: "Execution Intelligence",
    problem: "Fatos de execução precisam de leitura explicável.",
    productEvidence:
      "Snapshot Core → OI → sinais e histórico no Evolution.",
    humanLimit: "Sinais orientam; não disparam mutação nem decisão final.",
    chapterId: "interpret",
    icon: "sparkles",
  },
  {
    id: "cap-cockpit",
    name: "Cockpit",
    problem: "Gestores precisam de fila transparente, sem score opaco.",
    productEvidence:
      "Síntese, freshness e motivos derivados de fatos existentes.",
    humanLimit: "Prioridade do Cockpit não é decisão automática.",
    chapterId: "control",
    icon: "compass",
  },
  {
    id: "cap-trace",
    name: "Rastreabilidade e decisão humana",
    problem: "Sem origem, confiança e aprendizado se perdem.",
    productEvidence:
      "Histórico de análises, ações, outcomes e revisões no caso.",
    humanLimit: "O QMind orienta e interpreta; pessoas autorizadas decidem.",
    chapterId: "decide",
    icon: "waypoints",
  },
];

export const HERO_V2 = {
  title: "Da compreensão à decisão — com qualidade, execução e aprendizado.",
  copy:
    "O QMind ajuda a organização a avaliar, reconhecer problemas, executar ações e interpretar resultados com fatos rastreáveis. O sistema orienta; pessoas autorizadas decidem.",
  humanDecision:
    "Decisões permanecem humanas. Meta atingida não equivale automaticamente a eficácia.",
  promise: [
    {
      title: "Ciclo completo.",
      body: "Avaliar, executar, medir e controlar prioridades no mesmo vocabulário.",
    },
    {
      title: "Fatos no Core.",
      body: "O Core conserva evidências e decisões; o OI interpreta por contrato.",
    },
    {
      title: "Sem conformidade automática.",
      body: "Não certificamos, não inventamos evidências e não prometemos percentuais.",
    },
    {
      title: "Decisão humana.",
      body: "Cockpit e OI orientam a revisão — não substituem o julgamento.",
    },
  ],
} as const;

export const PRINCIPLES_V2 = [
  {
    title: "ORGANIZAÇÃO DONA DOS DADOS",
    body: "Dados operacionais permanecem vinculados à organização autorizada.",
  },
  {
    title: "ORIENTAÇÃO COM DECISÃO HUMANA",
    body: "O QMind orienta e interpreta; pessoas autorizadas revisam e decidem.",
  },
  {
    title: "SEM CONFORMIDADE AUTOMÁTICA",
    body: "Não certificamos, não substituímos o auditor e não inventamos evidências.",
  },
  {
    title: "META ≠ EFICÁCIA",
    body: "Atingir uma meta é um fato mensurável — a eficácia continua decisão humana.",
  },
  {
    title: "OI NÃO É CHATBOT GENÉRICO",
    body: "O OI interpreta snapshots factuais via contrato HTTP, sem ler o banco do Core.",
  },
  {
    title: "COCKPIT SEM SCORE OPACO",
    body: "Prioridade é fila transparente com motivos — não risco percentual automático.",
  },
  {
    title: "RASTREABILIDADE",
    body: "Respostas, evidências, análises, ações e outcomes mantêm origem.",
  },
];

export const GUIDED_SPEAK: Record<
  JourneyChapterId,
  GuidedTourSpeakBlocks & { title: string; contextRequirement: GuidedTourContextRequirement }
> = {
  understand: {
    title: "Compreender a organização",
    demonstrate: "Home de avaliações e o contexto da organização ativa.",
    message: "Comece pelo mapa: quem é a organização e o que já existe para demonstrar.",
    limitation: "Sem inventar maturidade. Contexto incompleto é estado honesto.",
    contextRequirement: "organization",
  },
  assess: {
    title: "Avaliar e reunir evidências",
    demonstrate: "Avaliação existente — perguntas, plano ou campo já preenchidos.",
    message: "Mostre evidências ligadas a perguntas, não pastas soltas.",
    limitation: "Não criar avaliação no tour. Se faltar dado, prepare fora da apresentação.",
    contextRequirement: "assessment",
  },
  recognize: {
    title: "Reconhecer o Improvement Case",
    demonstrate: "Detalhe de um caso existente: problema, impacto e status.",
    message: "O impacto virou um caso rastreável — não uma pendência anônima.",
    limitation: "Não criar caso no tour. Papéis sem leitura não recebem destino.",
    contextRequirement: "case",
  },
  analyze: {
    title: "Analisar com o QMind OI",
    demonstrate: "Seção de análise do caso: interpretação, achados e limitações.",
    message: "Core conserva fatos; OI interpreta; humano valida o próximo passo.",
    limitation: "Não disparar nova análise OI durante o tour.",
    contextRequirement: "case",
  },
  execute: {
    title: "Executar no board",
    demonstrate: "Board de execução ou card de ação existente.",
    message: "Squads, sprints e check-ins tornam o trabalho e os bloqueios visíveis.",
    limitation: "Não alterar status nem abrir impedimento no tour.",
    contextRequirement: "action",
  },
  evidence_measure: {
    title: "Evidenciar e medir",
    demonstrate: "Evolution ou card com medições/evidências já registradas.",
    message: "Baseline, indicador e leitura sustentam a conversa sobre resultado.",
    limitation: "Meta atingida não decide eficácia sozinha.",
    contextRequirement: "case",
  },
  interpret: {
    title: "Interpretar a execução",
    demonstrate: "Histórico de Execution Intelligence no Evolution, se existir.",
    message: "Sinais explicáveis citam fatos — sem chatbot genérico.",
    limitation: "Não disparar novo run de EI no tour.",
    contextRequirement: "case",
  },
  control: {
    title: "Controlar no Cockpit",
    demonstrate: "Cockpit da organização: síntese, freshness e fila.",
    message: "Prioridade é transparente e humana — não score automático.",
    limitation: "O Cockpit não chama o OI e não decide sozinho.",
    contextRequirement: "cockpit",
  },
  decide: {
    title: "Decidir e evoluir",
    demonstrate: "Caso/Evolution com outcome ou prontidão de revisão, se houver.",
    message: "Fechar o ciclo com revisão humana e aprendizado rastreável.",
    limitation: "Sem outcome, diga o que falta — não invente eficácia.",
    contextRequirement: "case",
  },
};

export function chapterById(id: JourneyChapterId): JourneyChapter {
  return JOURNEY_V2_CHAPTERS.find((c) => c.id === id) ?? JOURNEY_V2_CHAPTERS[0]!;
}

export function isJourneyChapterId(value: string | null | undefined): value is JourneyChapterId {
  return (
    typeof value === "string" &&
    (JOURNEY_CHAPTER_IDS as readonly string[]).includes(value)
  );
}

export function parseChapterParam(raw: string | null | undefined): JourneyChapterId | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!isJourneyChapterId(trimmed)) return null;
  return trimmed;
}

export function guidedTourPathForChapter(chapterId?: JourneyChapterId | null): string {
  if (!chapterId) return "/guided-tour";
  return `/guided-tour?chapter=${encodeURIComponent(chapterId)}`;
}

export type { HotpageIconName };
