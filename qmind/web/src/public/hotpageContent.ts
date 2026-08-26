/**
 * Conteúdo público da hotpage — projeção da Jornada V2 canônica.
 * Textos comerciais/visuais vivem aqui; resolvers técnicos ficam em journeyV2/resolveContext.
 */

export type { HotpageIconName } from "@/journeyV2/iconNames";
export type { Principle, JourneyStep, Differential, Outcome } from "./hotpageContent.types";

import {
  HERO_V2,
  ILLUSTRATIVE_EXAMPLE,
  ILLUSTRATIVE_EXAMPLE_BADGE,
  JOURNEY_V2_CHAPTERS,
  PRINCIPLES_V2,
  PRODUCT_CAPABILITIES,
  guidedTourPathForChapter,
} from "@/journeyV2";
import type { Differential, JourneyStep, Outcome, Principle } from "./hotpageContent.types";

export const PRINCIPLES: Principle[] = PRINCIPLES_V2;

export const JOURNEY_STEPS: JourneyStep[] = JOURNEY_V2_CHAPTERS.map((c) => ({
  id: c.id,
  label: c.label,
  definition: c.organizes,
  result: c.observableResult,
  situation: c.situation,
  evidence: c.evidence,
  humanAction: c.humanAction,
  icon: c.icon,
}));

export const DIFFERENTIALS: Differential[] = PRODUCT_CAPABILITIES.map((cap) => ({
  id: cap.id,
  name: cap.name,
  definition: cap.problem,
  benefit: cap.productEvidence,
  limit: cap.humanLimit,
  tourPoint: JOURNEY_V2_CHAPTERS.find((c) => c.id === cap.chapterId)?.title ?? cap.chapterId,
  tourStepId: cap.chapterId,
  icon: cap.icon,
}));

export const OUTCOMES: Outcome[] = [
  {
    title: "Ciclo compreensível",
    body: "Da avaliação à execução e ao Cockpit, com o mesmo vocabulário.",
    icon: "map",
  },
  {
    title: "Problemas rastreáveis",
    body: "Impactos viram Improvement Cases acompanháveis.",
    icon: "target",
  },
  {
    title: "Execução visível",
    body: "Board, sprints e check-ins tornam bloqueios explícitos.",
    icon: "activity",
  },
  {
    title: "Medição com limites",
    body: "Indicadores e metas sustentam a conversa — sem eficácia automática.",
    icon: "chart",
  },
  {
    title: "Interpretação explicável",
    body: "OI lê snapshots factuais e devolve sinais com limitações.",
    icon: "sparkles",
  },
  {
    title: "Prioridade transparente",
    body: "Cockpit consolida fatos e freshness sem score opaco.",
    icon: "compass",
  },
  {
    title: "Decisão humana",
    body: "O QMind orienta; pessoas autorizadas decidem e aprendem.",
    icon: "userCheck",
  },
  {
    title: "Rastreabilidade",
    body: "Origem de respostas, evidências, análises e outcomes permanece.",
    icon: "waypoints",
  },
];

export const EVIDENCE_POINTS = [
  "Recebe evidências antes, durante e após o campo",
  "Vincula evidências a perguntas, respostas e entrevistas",
  "Classifica a origem de cada arquivo",
  "Registra a situação de verificação",
  "Preserva versões e hash no servidor",
  "Mantém aprovação humana",
  "Impede mistura entre organizações",
  "Liga evidência contextual a ações e medições",
  "Prepara consumo por análise e auditoria formal",
];

export const QUALITY_CONTROL_POINTS = [
  "Quem fez e quando",
  "Em qual organização e caso",
  "Qual versão da análise ou medição",
  "Quem revisou a interpretação OI",
  "Qual ação e check-in resultaram",
  "Se a meta foi medida (fato ≠ eficácia)",
  "O que entrou no histórico do caso",
];

export const HERO_PROMISE = HERO_V2.promise.map((p) => ({
  title: p.title,
  body: p.body,
}));

export const HERO_COPY = HERO_V2;

export {
  ILLUSTRATIVE_EXAMPLE,
  ILLUSTRATIVE_EXAMPLE_BADGE,
  PRODUCT_CAPABILITIES,
  guidedTourPathForChapter,
};
