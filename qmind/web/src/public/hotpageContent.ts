export type Principle = { title: string; body: string };

export type JourneyStep = {
  id: string;
  label: string;
  definition: string;
  result: string;
  icon: HotpageIconName;
};

export type Differential = {
  id: string;
  name: string;
  definition: string;
  benefit: string;
  tourPoint: string;
  tourStepId: string;
  icon: HotpageIconName;
};

export type Outcome = {
  title: string;
  body: string;
  icon: HotpageIconName;
};

export type HotpageIconName =
  | "check"
  | "arrowDown"
  | "arrowRight"
  | "building"
  | "route"
  | "messages"
  | "files"
  | "search"
  | "trending"
  | "fileCheck"
  | "assistant"
  | "calendar"
  | "clipboard"
  | "map"
  | "folder"
  | "sparkles"
  | "shield"
  | "clock"
  | "hours"
  | "chart"
  | "stack"
  | "waypoints"
  | "userCheck";

export const PRINCIPLES: Principle[] = [
  {
    title: "AUTOAVALIAÇÃO PRIMEIRO",
    body: "A organização compreende sua realidade antes da auditoria formal.",
  },
  {
    title: "PREPARAÇÃO GUIADA",
    body: "O QMind traduz o processo em perguntas, exemplos, evidências e próximos passos acessíveis.",
  },
  {
    title: "MELHOR USO DO INVESTIMENTO",
    body: "Contexto e evidências organizados permitem concentrar o trabalho especializado em validação, análise e aprofundamento.",
  },
  {
    title: "ORGANIZAÇÃO DONA DOS DADOS",
    body: "A consultoria opera por acesso delegado. Os dados permanecem vinculados à organização.",
  },
  {
    title: "ORIENTAÇÃO COM DECISÃO HUMANA",
    body: "O sistema orienta e sugere; pessoas autorizadas revisam e decidem.",
  },
  {
    title: "SEM CONFORMIDADE AUTOMÁTICA",
    body: "O QMind não certifica, não substitui o auditor e não inventa evidências.",
  },
  {
    title: "RASTREABILIDADE",
    body: "Cada resposta, evidência, revisão, decisão e ação mantém sua origem.",
  },
];

export const JOURNEY_STEPS: JourneyStep[] = [
  {
    id: "understand",
    label: "Compreender",
    definition:
      "Conhecer contexto, escopo, processos, unidades e partes interessadas.",
    result: "Uma visão clara da organização e do que será avaliado.",
    icon: "building",
  },
  {
    id: "plan",
    label: "Planejar",
    definition:
      "Definir objetivos, critérios, equipe, entrevistas, reuniões e marcos.",
    result: "Um Plano da Auditoria único e executável.",
    icon: "route",
  },
  {
    id: "interview",
    label: "Entrevistar",
    definition: "Conduzir conversas orientadas por processos e temas relevantes.",
    result: "Informações estruturadas e rastreáveis.",
    icon: "messages",
  },
  {
    id: "evidence",
    label: "Evidenciar",
    definition:
      "Anexar, classificar, verificar e relacionar documentos e registros.",
    result: "Evidências organizadas para revisão e consumo pela auditoria.",
    icon: "files",
  },
  {
    id: "analyze",
    label: "Analisar",
    definition:
      "Confrontar respostas, evidências, constatações e maturidade.",
    result: "Pontos fortes, lacunas e assuntos para aprofundamento.",
    icon: "search",
  },
  {
    id: "evolve",
    label: "Evoluir",
    definition: "Transformar resultados em sugestões e ações priorizadas.",
    result: "Melhorias iniciadas antes da auditoria formal.",
    icon: "trending",
  },
  {
    id: "demonstrate",
    label: "Demonstrar",
    definition: "Consolidar relatório, histórico, ações e evidências.",
    result: "Uma preparação clara, verificável e apresentável.",
    icon: "fileCheck",
  },
];

export const DIFFERENTIALS: Differential[] = [
  {
    id: "assistant",
    name: "Assistente QMind",
    definition:
      "Orientação contextual que explica a etapa, mostra pendências e conduz à próxima ação.",
    benefit:
      "Reduz dependência de treinamento e evita que o usuário fique perdido.",
    tourPoint: "Home, Wizard, Plano, Campo e Evolução",
    tourStepId: "home",
    icon: "assistant",
  },
  {
    id: "calendar",
    name: "Agenda unificada",
    definition:
      "Entrevistas, reuniões, prazos e marcos conectados às avaliações.",
    benefit:
      "Transforma planejamento em compromissos visíveis e reduz esquecimentos.",
    tourPoint: "Home da organização",
    tourStepId: "agenda",
    icon: "calendar",
  },
  {
    id: "plan",
    name: "Plano da Auditoria",
    definition:
      "Objetivo, escopo, processos, equipe e programação em um único caminho.",
    benefit: "Reduz improviso e elimina fluxos concorrentes.",
    tourPoint: "Plano da Auditoria",
    tourStepId: "audit_plan",
    icon: "clipboard",
  },
  {
    id: "journey",
    name: "Mapa do percurso",
    definition:
      "Visão do que foi concluído, do que está pendente e da próxima ação.",
    benefit: "Mantém gestores e consultores orientados.",
    tourPoint: "Home e visão da avaliação",
    tourStepId: "home",
    icon: "map",
  },
  {
    id: "evidence",
    name: "Evidências organizadas",
    definition:
      "Documentos e registros classificados, verificados e ligados às perguntas, entrevistas e constatações.",
    benefit:
      "Facilita o consumo racional das evidências durante a auditoria formal.",
    tourPoint: "Wizard e Central de Campo",
    tourStepId: "evidence",
    icon: "folder",
  },
  {
    id: "evolution",
    name: "Mapa de Evolução Empresarial",
    definition:
      "Sugestões práticas e rastreáveis, sempre revisadas por uma pessoa.",
    benefit: "Permite iniciar melhorias antes da auditoria formal.",
    tourPoint: "Mapa de Evolução Empresarial",
    tourStepId: "evolution",
    icon: "sparkles",
  },
  {
    id: "control",
    name: "Quality Control",
    definition:
      "Permissões, segregação, estados, versões, auditoria e correlação controlam todo o processo.",
    benefit: "Preserva confiança, responsabilidade e histórico das decisões.",
    tourPoint: "Análise, ações, relatório e trilha de auditoria",
    tourStepId: "quality_control",
    icon: "shield",
  },
];

export const OUTCOMES: Outcome[] = [
  {
    title: "Preparação mais rápida",
    body: "Ajuda a reduzir o tempo gasto reunindo entrevistas, evidências e pendências em um único percurso.",
    icon: "clock",
  },
  {
    title: "Melhor aproveitamento das horas do auditor",
    body: "Permite melhor aproveitamento do trabalho especializado em validação e análise — não em organizar arquivos dispersos.",
    icon: "hours",
  },
  {
    title: "Menor retrabalho",
    body: "Tende a reduzir retrabalho ao manter contexto, versões e decisões conectados.",
    icon: "chart",
  },
  {
    title: "Menos organização manual de arquivos",
    body: "Pode contribuir para reduzir a organização manual de evidências dispersas.",
    icon: "stack",
  },
  {
    title: "Evidências prontas para análise",
    body: "Melhora a preparação com arquivos classificados e ligados às perguntas.",
    icon: "folder",
  },
  {
    title: "Responsabilidades e prazos visíveis",
    body: "Agenda e ações deixam compromissos claros para a equipe.",
    icon: "calendar",
  },
  {
    title: "Identificação antecipada de lacunas",
    body: "Permite enxergar pontos fracos antes da auditoria formal.",
    icon: "search",
  },
  {
    title: "Início de melhorias antes da auditoria",
    body: "Sugestões revisadas podem virar ações ainda na preparação.",
    icon: "trending",
  },
  {
    title: "Rastreabilidade",
    body: "Resposta, evidência, revisão, decisão e ação mantêm origem.",
    icon: "waypoints",
  },
  {
    title: "Aprendizado organizacional",
    body: "Cada etapa vira aprendizado prático para a equipe — sem prometer certificação automática.",
    icon: "userCheck",
  },
];

export const EVIDENCE_POINTS = [
  "Recebe evidências antes, durante e após o campo",
  "Vincula evidências a perguntas, respostas e entrevistas",
  "Classifica a origem de cada arquivo",
  "Registra a situação de verificação",
  "Preserva versões",
  "Calcula hash no servidor",
  "Mantém aprovação humana",
  "Impede mistura entre organizações",
  "Permite reutilização sem duplicar arquivos",
  "Prepara o consumo pela auditoria formal",
];

export const QUALITY_CONTROL_POINTS = [
  "Quem fez",
  "Quando fez",
  "Em qual organização",
  "Em qual avaliação",
  "Qual versão",
  "Qual resposta",
  "Qual evidência",
  "Quem revisou",
  "Qual decisão foi tomada",
  "Qual ação resultou",
  "Se houve validação de eficácia",
  "O que entrou no relatório",
];

export const HERO_PROMISE = [
  {
    title: "Autoavaliação primeiro.",
    body: "Entenda a empresa antes da auditoria formal.",
  },
  {
    title: "Preparação guiada.",
    body: "Qualquer gestor consegue avançar com orientação.",
  },
  {
    title: "Melhor uso do investimento.",
    body: "O auditor recebe contexto e evidências já organizados.",
  },
  {
    title: "Decisão humana.",
    body: "O sistema orienta; a organização e o consultor validam.",
  },
];
