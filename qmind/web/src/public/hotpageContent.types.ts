import type { HotpageIconName } from "@/journeyV2/iconNames";

export type Principle = { title: string; body: string };

export type JourneyStep = {
  id: string;
  label: string;
  definition: string;
  result: string;
  situation?: string;
  evidence?: string;
  humanAction?: string;
  icon: HotpageIconName;
};

export type Differential = {
  id: string;
  name: string;
  definition: string;
  benefit: string;
  limit?: string;
  tourPoint: string;
  tourStepId: string;
  icon: HotpageIconName;
};

export type Outcome = {
  title: string;
  body: string;
  icon: HotpageIconName;
};
